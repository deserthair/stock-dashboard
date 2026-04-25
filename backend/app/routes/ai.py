"""Ask-AI endpoint for in-app info modals.

The frontend's `<InfoIcon>` opens a modal that explains a section in plain
English. The user can type a follow-up question; we forward it to Claude
along with the section's title, the explanation already on screen, and any
page-level context, then return the answer.

If `ANTHROPIC_API_KEY` is not configured the endpoint returns a 503 so the
modal can show a friendly error instead of silently failing.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import get_settings

router = APIRouter(prefix="/api/ai", tags=["ai"])

MODEL = "claude-haiku-4-5-20251001"  # Snappy + cheap for short Q&A.

SYSTEM_PROMPT = """You are an explainer baked into a stock-analysis dashboard
called RESTIN (Restaurant Intelligence Terminal). The user is a complete
beginner — assume zero finance background. Answer their follow-up question
about the section they're looking at.

Rules:
- Plain English. Define jargon the first time you use it.
- 2-4 short paragraphs max. No bullet lists unless explicitly asked.
- Ground your answer in the section context provided. Do not invent
  numbers that aren't in the context.
- If the question is off-topic for the section, briefly answer it and
  then point back to what the section actually shows.
"""


class AskRequest(BaseModel):
    section_title: str = Field(..., max_length=200)
    section_explanation: str = Field("", max_length=4000)
    page_context: str = Field("", max_length=2000)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI is not configured on this server (ANTHROPIC_API_KEY missing).",
        )

    try:
        import anthropic
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail="anthropic SDK not installed on this server.",
        ) from e

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    user_message = (
        f"Section: {req.section_title}\n"
        f"\nWhat the section shows (already visible to the user):\n"
        f"{req.section_explanation}\n"
    )
    if req.page_context:
        user_message += f"\nExtra page context:\n{req.page_context}\n"
    user_message += f"\nUser question:\n{req.question}\n"

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:  # noqa: BLE001 — surface upstream errors to UI
        raise HTTPException(status_code=502, detail=f"Claude error: {e}") from e

    text = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    ).strip()
    if not text:
        raise HTTPException(status_code=502, detail="Empty response from Claude.")

    return AskResponse(answer=text)
