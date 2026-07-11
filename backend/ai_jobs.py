"""AI job lifecycle: live stage/progress, token+cost metering, cancellation.

Runners call `stage()` between phases; `stage()` raises JobCancelled when the
user pressed Stop, which the runner surfaces as a cancelled job. Cancellation
is cooperative — an in-flight provider call finishes, then the result is
discarded before any write."""
import database as db
from utils import as_uuid, now_utc

import genai


class JobCancelled(Exception):
    pass


async def create(org_id, user, kind, ref_id="", engine="claude", model="", effort="standard"):
    row = await db.fetchrow(
        """insert into ai_jobs (organization_id, user_id, kind, ref_id, status,
                                stage, engine, model, effort)
           values ($1, $2, $3, $4, 'running', 'Starting…', $5, $6, $7)
           returning id""",
        as_uuid(org_id), as_uuid((user or {}).get("id")), kind, str(ref_id),
        engine, model, effort or "standard")
    return row["id"]


async def stage(job_id, text, progress):
    """Update the live stage; raises JobCancelled if the user pressed Stop."""
    row = await db.fetchrow(
        """update ai_jobs set stage = $2, progress = $3
           where id = $1 returning cancel_requested""",
        job_id, text, max(0, min(99, int(progress))))
    if row and row["cancel_requested"]:
        await db.execute(
            """update ai_jobs set status = 'cancelled', stage = 'Cancelled by user',
               finished_at = $2 where id = $1""", job_id, now_utc())
        raise JobCancelled()


async def add_usage(job_id, model, usage):
    """Accumulate tokens + metered cost after a provider call."""
    inp = int((usage or {}).get("inputTokens") or 0)
    out = int((usage or {}).get("outputTokens") or 0)
    cost = genai.cost_usd(model, inp, out)
    await db.execute(
        """update ai_jobs set model = $2, input_tokens = input_tokens + $3,
               output_tokens = output_tokens + $4, cost_usd = cost_usd + $5
           where id = $1""",
        job_id, model, inp, out, cost)


async def finish(job_id, stage_text="Done"):
    await db.execute(
        """update ai_jobs set status = 'done', stage = $2, progress = 100,
           finished_at = $3 where id = $1""", job_id, stage_text, now_utc())


async def fail(job_id, error):
    await db.execute(
        """update ai_jobs set status = 'error', stage = 'Failed', error = $2,
           finished_at = $3 where id = $1""", job_id, str(error)[:900], now_utc())


async def cancelled(job_id):
    await db.execute(
        """update ai_jobs set status = 'cancelled', stage = 'Cancelled by user',
           finished_at = $2 where id = $1""", job_id, now_utc())


async def month_spend(org_id) -> float:
    row = await db.fetchrow(
        """select coalesce(sum(cost_usd), 0) as spend from ai_jobs
           where organization_id = $1
             and created_at >= date_trunc('month', now())""",
        as_uuid(org_id))
    return float(row["spend"] or 0)
