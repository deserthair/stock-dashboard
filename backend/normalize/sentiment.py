"""Claude-backed sentiment + topic classifier for news and social posts.

Batches 20 items per API call for cost efficiency. Returns a list of
{sentiment, confidence, topics, relevance} dicts aligned with inputs.

Skipped if ANTHROPIC_API_KEY is unset."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.config import get_settings
from app.db import SessionLocal
from app.models import Company, NewsItem, RedditPost, SocialPost

from ingest.source_run import source_run

log = logging.getLogger("sentiment")

BATCH = 20
MODEL = "claude-haiku-4-5-20251001"  # Haiku: bulk tagging. Promote to Sonnet for ambiguous cases.

SYSTEM_PROMPT = (
    "You are a financial-news classifier. For each item, return a JSON object "
    "with keys:\n"
    "  sentiment: float in [-1, 1] (negative / neutral / positive toward the company),\n"
    "  confidence: float in [0, 1],\n"
    "  relevance: float in [0, 1] (how materially it affects the stock),\n"
    "  topics: array of short lowercase tags drawn from "
    "['earnings','guidance','menu','mgmt_change','labor','supply','promo',"
    "'regulatory','legal','expansion','closure','macro','analyst','tech','other'].\n"
    "Return ONLY a JSON array of objects, same length as input, no prose."
)


@dataclass
class ScoreResult:
    sentiment: float | None
    confidence: float | None
    relevance: float | None
    topics: list[str]


def _score_batch(client, ticker: str, company: str, items: list[str]) -> list[ScoreResult]:
    prompt = (
        f"Company: {ticker} ({company}). Score these {len(items)} items toward the company:\n\n"
        + "\n".join(f"[{i}] {t}" for i, t in enumerate(items))
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"sentiment response missing JSON array: {text[:200]}")
    data = json.loads(text[start : end + 1])
    out: list[ScoreResult] = []
    for row in data:
        out.append(
            ScoreResult(
                sentiment=_coerce_float(row.get("sentiment")),
                confidence=_coerce_float(row.get("confidence")),
                relevance=_coerce_float(row.get("relevance")),
                topics=[t for t in (row.get("topics") or []) if isinstance(t, str)][:6],
            )
        )
    # Pad/truncate to the expected length so callers can zip safely.
    while len(out) < len(items):
        out.append(ScoreResult(None, None, None, []))
    return out[: len(items)]


def _coerce_float(x) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def run_once(limit: int = 200) -> int:
    with source_run("sentiment") as run:
        settings = get_settings()
        if not settings.anthropic_api_key:
            log.info("ANTHROPIC_API_KEY not set; skipping sentiment pass")
            run.skip = True
            return 0

        try:
            import anthropic
        except ImportError:
            run.skip = True
            return 0

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        scored = 0
        with SessionLocal() as s:
            by_id = {c.company_id: c for c in s.query(Company).all()}

            targets: list[tuple[object, str, int | None]] = []
            for n in (
                s.query(NewsItem)
                .filter(NewsItem.sentiment_score.is_(None))
                .order_by(NewsItem.news_id.desc())
                .limit(limit)
                .all()
            ):
                targets.append((n, n.headline, n.company_id))
            for p in (
                s.query(RedditPost)
                .filter(RedditPost.sentiment_score.is_(None))
                .order_by(RedditPost.fetched_at.desc())
                .limit(limit // 2)
                .all()
            ):
                targets.append((p, p.title, p.company_id))
            for sp in (
                s.query(SocialPost)
                .filter(SocialPost.sentiment_score.is_(None))
                .order_by(SocialPost.post_id.desc())
                .limit(limit // 2)
                .all()
            ):
                targets.append((sp, sp.content, sp.company_id))

            # Group by company so the prompt has a single ticker context.
            by_company: dict[int | None, list[tuple[object, str]]] = {}
            for obj, text, cid in targets:
                by_company.setdefault(cid, []).append((obj, text))

            for cid, rows in by_company.items():
                company = by_id.get(cid)
                ticker = company.ticker if company else "?"
                cname = company.name if company else "(unknown)"

                for i in range(0, len(rows), BATCH):
                    chunk = rows[i : i + BATCH]
                    try:
                        scores = _score_batch(client, ticker, cname, [t for _, t in chunk])
                    except Exception as exc:  # noqa: BLE001
                        log.warning("batch failed: %s", exc)
                        continue
                    for (obj, _), sr in zip(chunk, scores):
                        if sr.sentiment is not None:
                            obj.sentiment_score = sr.sentiment
                        if hasattr(obj, "sentiment_confidence") and sr.confidence is not None:
                            obj.sentiment_confidence = sr.confidence
                        if hasattr(obj, "relevance_score") and sr.relevance is not None:
                            obj.relevance_score = sr.relevance
                        if hasattr(obj, "topics"):
                            obj.topics = sr.topics
                        scored += 1
            s.commit()

        run.rows_fetched = scored
        return scored


if __name__ == "__main__":
    run_once()
