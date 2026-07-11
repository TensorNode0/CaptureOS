"""Public marketing endpoints: reviews wall + contact form. No auth required.
Anti-abuse: honeypot field, strict size limits, AI headshot moderation."""
import os
import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import database as db
import email_service
from utils import iso

router = APIRouter(prefix="/api/public", tags=["public"])

CONTACT_FORWARD_TO = "info@orbitalservicescorporation.com"
MAX_HEADSHOT_CHARS = 2_800_000  # ~2 MB of base64
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HEADSHOT_PREFIX = re.compile(r"^data:image/(png|jpeg|jpg|webp);base64,", re.I)


class ReviewIn(BaseModel):
    firstName: str = Field(min_length=1, max_length=60)
    lastName: str = Field(min_length=1, max_length=60)
    showFullName: bool = True
    company: str = Field(min_length=1, max_length=120)
    companyAnonymous: bool = False
    email: str = Field(min_length=3, max_length=254)
    sector: str = Field(min_length=1, max_length=40)
    industry: str = Field(min_length=1, max_length=80)
    inquiryType: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=4000)
    headshot: str = Field(default="", max_length=MAX_HEADSHOT_CHARS + 60)
    website: str = ""  # honeypot — real users never fill this


class ContactIn(BaseModel):
    firstName: str = Field(min_length=1, max_length=60)
    lastName: str = Field(min_length=1, max_length=60)
    company: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    sector: str = Field(min_length=1, max_length=40)
    industry: str = Field(min_length=1, max_length=80)
    inquiryType: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=4000)
    website: str = ""  # honeypot


def _check_email(email: str):
    if not EMAIL_RE.match(email.strip()):
        raise HTTPException(status_code=400, detail="Enter a valid company email address.")


async def _moderate_headshot(data_url: str):
    """AI check: appropriate headshot of a person, nothing offensive. (ok, reason)."""
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return False, "Headshot uploads are temporarily unavailable — submit without a photo."
    b64 = data_url.split(",", 1)[1] if "," in data_url else ""
    if not b64:
        return False, "Invalid image data."
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        chat = LlmChat(
            api_key=key, session_id=f"headshot-{uuid4()}",
            system_message="You are a strict image moderator for a business reviews page.",
        ).with_model("openai", "gpt-4o-mini")
        resp = await chat.send_message(UserMessage(
            text=("Answer with exactly APPROVE or REJECT. APPROVE only if this image is an "
                  "appropriate headshot-style photo of one real person suitable for a business "
                  "reviews page: no nudity or sexual content, no violence or gore, no hate "
                  "symbols, no slurs or offensive text or gestures, and not a meme, logo, "
                  "cartoon, screenshot, or object."),
            file_contents=[ImageContent(image_base64=b64)]))
        if (str(resp) or "").strip().upper().startswith("APPROVE"):
            return True, ""
        return False, ("The photo was rejected: it must be an appropriate headshot of a "
                       "person with no inappropriate content. Try another photo or submit without one.")
    except Exception:
        return False, "Headshot moderation is temporarily unavailable — submit without a photo."


def _shape_review(r):
    name = (f"{r['first_name']} {r['last_name']}" if r["show_full_name"]
            else f"{r['first_name'][:1]}. {r['last_name'][:1]}.")
    return {
        "id": str(r["id"]), "name": name,
        "company": "" if r["company_anonymous"] else r["company"],
        "sector": r["sector"], "industry": r["industry"],
        "inquiryType": r["inquiry_type"], "message": r["message"],
        "headshot": r["headshot"], "createdAt": iso(r["created_at"]),
    }


@router.get("/reviews")
async def list_reviews():
    rows = await db.fetch(
        "select * from marketing_reviews order by created_at desc limit 100")
    return [_shape_review(r) for r in rows]


@router.post("/reviews")
async def create_review(body: ReviewIn):
    if body.website.strip():
        return {"ok": True}  # honeypot hit — accept silently, store nothing
    _check_email(body.email)
    headshot = body.headshot.strip()
    if headshot:
        if not HEADSHOT_PREFIX.match(headshot):
            raise HTTPException(status_code=400,
                detail="Headshot must be a JPEG, PNG, or WEBP image.")
        if len(headshot) > MAX_HEADSHOT_CHARS:
            raise HTTPException(status_code=400, detail="Headshot must be under 2 MB.")
        ok, reason = await _moderate_headshot(headshot)
        if not ok:
            raise HTTPException(status_code=400, detail=reason)
    row = await db.fetchrow(
        """insert into marketing_reviews
               (first_name, last_name, show_full_name, company, company_anonymous,
                email, sector, industry, inquiry_type, message, headshot)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
           returning *""",
        body.firstName.strip(), body.lastName.strip(), body.showFullName,
        body.company.strip(), body.companyAnonymous, body.email.strip().lower(),
        body.sector, body.industry, body.inquiryType, body.message.strip(), headshot)
    return {"ok": True, "review": _shape_review(row)}


@router.post("/contact")
async def create_contact(body: ContactIn):
    if body.website.strip():
        return {"ok": True}
    _check_email(body.email)
    row = await db.fetchrow(
        """insert into marketing_contacts
               (first_name, last_name, company, email, sector, industry,
                inquiry_type, message)
           values ($1, $2, $3, $4, $5, $6, $7, $8)
           returning id""",
        body.firstName.strip(), body.lastName.strip(), body.company.strip(),
        body.email.strip().lower(), body.sector, body.industry,
        body.inquiryType, body.message.strip())
    html = (
        f"<h2>CaptureAgent contact form</h2>"
        f"<p><b>Name:</b> {body.firstName} {body.lastName}<br/>"
        f"<b>Company:</b> {body.company}<br/>"
        f"<b>Email:</b> {body.email}<br/>"
        f"<b>Sector:</b> {body.sector} · <b>Industry:</b> {body.industry}<br/>"
        f"<b>Inquiry type:</b> {body.inquiryType}</p>"
        f"<p style='white-space:pre-wrap'>{body.message}</p>"
        f"<p style='color:#888;font-size:12px'>Submission id: {row['id']}</p>"
    )
    forwarded = False
    try:
        await email_service.send(
            CONTACT_FORWARD_TO,
            f"[CaptureAgent] {body.inquiryType} inquiry — {body.firstName} {body.lastName} ({body.company})",
            html)
        forwarded = True
    except Exception:
        forwarded = False
    await db.execute("update marketing_contacts set forwarded = $2 where id = $1",
                     row["id"], forwarded)
    return {"ok": True}
