"""Overleaf integration — bidirectional git sync for a Federal Proposal.

Overleaf's `/devs` surface exposes exactly two things a server can use:
  * HTTPS git remote per project: https://git.overleaf.com/{project_id}
  * A personal auth token per user, sent as HTTP Basic password with
    username `git`. Users create tokens at overleaf.com → Account Settings →
    Git Integration → New authentication token.

There is NO public REST API for creating projects or embedding the editor —
we verified this against Overleaf's docs. So the flow is:
  1. User creates the Overleaf project (any way) and pastes its project id
     (or full URL) into CaptureAgent, along with a personal auth token
     (once, in Settings — stored envelope-encrypted like the API keys).
  2. `push_proposal` writes one file per proposal volume into a clone of
     the Overleaf repo, commits, and pushes.
  3. `pull_proposal` fetches the latest, reads each volume back, and
     updates the corresponding `proposal_documents.content_md`.

We push/pull each volume as a `.md` file (Overleaf accepts any file type in
the project and previews it, and it round-trips losslessly). A companion
`main.tex` is also written on first push so that if the user hits
"Compile" they get a real PDF via the LaTeX `markdown` package.

Everything happens inside `tempfile.TemporaryDirectory` — no persistent
state on disk. Git operations use the `git` CLI via `asyncio.subprocess`
to keep the event loop free."""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse

import database as db
from utils import as_uuid, now_utc


OVERLEAF_GIT_HOST = "git.overleaf.com"


class OverleafError(RuntimeError):
    """Any failure syncing with Overleaf — the endpoint turns this into a 502."""


# ------- URL / project-id parsing -------

_PROJECT_ID_RE = re.compile(r"^[a-f0-9]{16,32}$", re.IGNORECASE)


def normalize_project_id(user_input: str) -> str:
    """Accept either a bare project id, a git URL, or a web URL and return the
    canonical project id string. Raises OverleafError on anything unusable."""
    s = (user_input or "").strip()
    if not s:
        raise OverleafError("Overleaf project id or URL is required.")
    # Bare id
    if _PROJECT_ID_RE.match(s):
        return s
    # URL — take the last path segment
    try:
        parts = urlparse(s if "://" in s else f"https://{s}").path.strip("/").split("/")
    except Exception as e:
        raise OverleafError(f"Could not parse Overleaf URL: {e}") from e
    for seg in reversed(parts):
        if _PROJECT_ID_RE.match(seg):
            return seg
    raise OverleafError(
        f"Could not find a project id in {s!r}. Expected a Overleaf project id "
        "or a URL like https://www.overleaf.com/project/<project_id>.")


def _authenticated_remote(project_id: str, token: str) -> str:
    """Overleaf accepts HTTP Basic auth with username `git` and the personal
    auth token as the password. URL-encode the token to survive special chars."""
    safe = quote(token, safe="")
    return f"https://git:{safe}@{OVERLEAF_GIT_HOST}/{project_id}"


# ------- git subprocess helpers -------

async def _git(cwd: str, *args: str, timeout: int = 60) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ,
             # Keep credentials off the machine — always ask the URL and never
             # trigger a system-wide credential helper.
             "GIT_TERMINAL_PROMPT": "0",
             "GIT_CONFIG_NOSYSTEM": "1",
             "HOME": cwd,
             "GIT_AUTHOR_NAME":  "CaptureAgent",
             "GIT_AUTHOR_EMAIL": "sync@captureagent.us",
             "GIT_COMMITTER_NAME":  "CaptureAgent",
             "GIT_COMMITTER_EMAIL": "sync@captureagent.us"},
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError as e:
        proc.kill()
        raise OverleafError(f"git {args[0]} timed out after {timeout}s") from e
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


def _redact(text: str, token: str) -> str:
    """Strip the auth token out of any surfaced git output so we don't leak it
    back to the API caller / browser console."""
    if not token:
        return text
    return text.replace(token, "«redacted»").replace(quote(token, safe=""), "«redacted»")


async def _clone(project_id: str, token: str, dest: str) -> None:
    remote = _authenticated_remote(project_id, token)
    code, out, err = await _git(dest, "clone", "--depth", "1", remote, ".", timeout=120)
    if code != 0:
        # Cloudflare / Overleaf return 401 as a text body when the token is bad
        message = _redact(err or out, token).strip()
        if "Authentication failed" in message or "401" in message:
            raise OverleafError(
                "Overleaf rejected the auth token. Regenerate it at "
                "overleaf.com → Account → Git Integration and re-save it in Settings.")
        if "not found" in message.lower() or "404" in message:
            raise OverleafError(
                f"Overleaf project {project_id!r} not found. Double-check the URL "
                "or project id — and that your Overleaf account has access to it.")
        raise OverleafError(f"git clone failed: {message[:400]}")


# ------- file-shape helpers -------

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


def _volume_filename(doc_type: str) -> str:
    """Slug for the file that represents a single proposal volume in Overleaf."""
    slug = _SAFE_NAME.sub("-", (doc_type or "volume").strip().lower()).strip("-")
    return f"{slug or 'volume'}.md"


MAIN_TEX_TEMPLATE = r"""% Auto-generated by CaptureAgent on {generated_at} — safe to edit.
% This wrapper lets Overleaf compile the markdown volumes to a single PDF.
\documentclass[11pt]{article}
\usepackage[hybrid,smartEllipses,pipeTables,tightLists]{markdown}
\usepackage[margin=1in]{geometry}
\usepackage{hyperref}
\begin{document}
\markdownInput{{{main_include}}}
\end{document}
"""


def _combined_markdown(volumes: list[dict]) -> str:
    """Concatenate every volume's markdown into a single top-level file that
    `\\markdownInput` can compile in Overleaf."""
    parts = []
    for v in volumes:
        title = (v.get("title") or v.get("doc_type") or "Volume").strip()
        body  = (v.get("content_md") or "").strip()
        parts.append(f"\n\n\\clearpage\n# {title}\n\n{body}\n")
    return "".join(parts).lstrip() + "\n"


# ------- Public API used by the router -------

async def push_proposal(*, org_id, proposal_id, token, project_id):
    """Push every proposal volume as a `.md` file to the Overleaf project.
    Returns { filesWritten, commitSha }."""
    volumes = await db.fetch(
        """select id, doc_type, title, content_md
             from proposal_documents
             where proposal_id = $1
             order by sort_order, doc_type""",
        as_uuid(proposal_id))
    if not volumes:
        raise OverleafError("Proposal has no volumes to push yet.")

    with tempfile.TemporaryDirectory(prefix="overleaf-push-") as tmp:
        await _clone(project_id, token, tmp)

        # 1. One .md per volume — round-trippable.
        for v in volumes:
            fname = _volume_filename(v["doc_type"])
            (Path(tmp) / fname).write_text(v["content_md"] or "", encoding="utf-8")

        # 2. A combined `_captureagent.md` so `main.tex` has a single entry point.
        (Path(tmp) / "_captureagent.md").write_text(
            _combined_markdown([dict(v) for v in volumes]), encoding="utf-8")

        # 3. Main.tex — never overwrite if the user has customized it; only write
        #    when absent so their LaTeX edits survive future pushes.
        main_tex = Path(tmp) / "main.tex"
        if not main_tex.exists():
            main_tex.write_text(
                MAIN_TEX_TEMPLATE.format(
                    generated_at=now_utc().isoformat(timespec="seconds"),
                    main_include="_captureagent.md"),
                encoding="utf-8")

        # 4. Commit + push.
        await _git(tmp, "add", "-A")
        code, out, err = await _git(tmp, "diff", "--cached", "--quiet")
        if code == 0:
            return {"filesWritten": 0, "commitSha": "", "noChanges": True}
        code, out, err = await _git(tmp, "commit", "-m",
                                    f"CaptureAgent push · {now_utc().isoformat(timespec='seconds')}")
        if code != 0:
            raise OverleafError(f"git commit failed: {_redact(err or out, token)[:300]}")
        code, out, err = await _git(tmp, "push", "origin", "HEAD:master", timeout=120)
        if code != 0:
            # Overleaf's default branch is `master` — but retry against `main`
            # in case the project was recreated on a different default branch.
            code2, out2, err2 = await _git(tmp, "push", "origin", "HEAD:main", timeout=120)
            if code2 != 0:
                raise OverleafError(f"git push failed: {_redact(err or out, token)[:300]}")
        _code, sha, _err = await _git(tmp, "rev-parse", "HEAD")
        return {"filesWritten": len(volumes) + 1, "commitSha": sha.strip(),
                "noChanges": False}


async def pull_proposal(*, org_id, proposal_id, token, project_id):
    """Pull the latest .md files from Overleaf into each proposal volume.
    Only files whose slug matches an existing volume are applied; new files
    the user created in Overleaf are ignored (we don't invent volumes)."""
    volumes = await db.fetch(
        """select id, doc_type, content_md
             from proposal_documents
             where proposal_id = $1""",
        as_uuid(proposal_id))
    slug_to_row = {_volume_filename(v["doc_type"]): v for v in volumes}
    if not slug_to_row:
        raise OverleafError("Proposal has no volumes to pull into.")

    with tempfile.TemporaryDirectory(prefix="overleaf-pull-") as tmp:
        await _clone(project_id, token, tmp)
        updated, unchanged, missing = [], [], []
        for fname, row in slug_to_row.items():
            path = Path(tmp) / fname
            if not path.exists():
                missing.append(fname)
                continue
            new_md = path.read_text(encoding="utf-8", errors="replace")
            if new_md == (row["content_md"] or ""):
                unchanged.append(fname)
                continue
            await db.execute(
                """update proposal_documents
                     set content_md = $2, status = 'edited', updated_at = $3
                     where id = $1""",
                row["id"], new_md, now_utc())
            updated.append(fname)
        return {"updated": updated, "unchanged": unchanged, "missing": missing}


# ------- Persistence helpers -------

async def link_proposal(*, proposal_id, project_id_or_url):
    project_id = normalize_project_id(project_id_or_url)
    await db.execute(
        "update proposals set overleaf_project_id = $2, updated_at = $3 where id = $1",
        as_uuid(proposal_id), project_id, now_utc())
    return project_id


async def unlink_proposal(*, proposal_id):
    await db.execute(
        """update proposals set overleaf_project_id = '', overleaf_last_sync = null,
             updated_at = $2 where id = $1""",
        as_uuid(proposal_id), now_utc())


async def mark_synced(*, proposal_id):
    """Record the time of a successful push/pull so the UI can show 'Last synced …'."""
    await db.execute(
        "update proposals set overleaf_last_sync = $2, updated_at = $2 where id = $1",
        as_uuid(proposal_id), now_utc())


# Guarantee git is installed on import — fail loudly at startup instead of at
# the first user click. Keeps deployment failures visible to the platform.
if shutil.which("git") is None:
    raise RuntimeError(
        "The `git` CLI is required for the Overleaf integration but is not installed "
        "in this container. Add it to your Docker image (apt install git).")
