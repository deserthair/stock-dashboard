"""Claude-generated earnings postmortem.

For each past earnings event (where eps_actual is recorded and no
postmortem exists yet, or ?force=True), assemble a snapshot containing:
  - the event (ticker, fiscal period, estimate/actual/surprise/reaction)
  - 1D and 5D post-earnings returns
  - engineered feature vector + Lasso-attributed top drivers
  - news / filings / events within ±7 days of the report
  - macro context at the time

…and hand it to Claude with a system prompt that asks for a 2-paragraph
narrative explaining *why the company beat / missed* and how the market
reacted, using only the data in the snapshot.

Skipped if ANTHROPIC_API_KEY isn't set. Stores results in `earnings_postmortems`."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Company,
    Earnings,
    EarningsPostmortem,
    Event,
    Filing,
    MacroSeries,
    NewsItem,
)
from analysis.attribution import build_attributions
from analysis.outcomes import compute as compute_outcome

from ingest.source_run import source_run

log = logging.getLogger("postmortem")

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You write a short, factual postmortem for a past restaurant-industry
earnings event. Return JSON:

{
  "headline": "<≤ 120 char summary e.g. 'CMG Q4 2025 beat on strong protein-bowl momentum'>",
  "narrative": "<2 paragraphs, 150-250 words total>",
  "tags": ["menu_innovation", "beef_costs", "traffic_soft", ...]
}

Inside `narrative` use:
  <tag>TICKER</tag> for every stock symbol
  <strong>...</strong> for the key numeric facts you want bolded

Paragraph 1: explain WHY the company beat or missed — connect the surprise
to the engineered features (which drivers were up/down) and any news or
filings in the ±7 day window. Paragraph 2: explain the MARKET REACTION
(1D / 5D return), tying it to sentiment + macro context.

Be concrete: cite actual percentages and counts from the snapshot. Never
invent data. If a signal is not in the snapshot, do not speculate. Do not
include any prose outside the JSON."""


def _snapshot(s, earnings_id: int) -> dict | None:
    earn = s.query(Earnings).filter_by(earnings_id=earnings_id).one_or_none()
    if earn is None or earn.eps_actual is None:
        return None
    company = s.get(Company, earn.company_id)
    if company is None:
        return None

    oc = compute_outcome(s, earn)
    report_dt = datetime.combine(earn.report_date, datetime.min.time())
    window_start = report_dt - timedelta(days=7)
    window_end = report_dt + timedelta(days=7)

    news = [
        {
            "headline": n.headline,
            "publisher": n.publisher,
            "published_at": (n.published_at or n.fetched_at).isoformat(),
            "sentiment": n.sentiment_score,
        }
        for n in (
            s.query(NewsItem)
            .filter(
                NewsItem.company_id == company.company_id,
                NewsItem.fetched_at >= window_start,
                NewsItem.fetched_at <= window_end,
            )
            .order_by(NewsItem.fetched_at.desc())
            .limit(15)
            .all()
        )
    ]
    filings = [
        {
            "filing_type": f.filing_type,
            "filed_at": f.filed_at.isoformat(),
            "items": list(f.item_numbers or []),
            "title": f.title,
        }
        for f in (
            s.query(Filing)
            .filter(
                Filing.company_id == company.company_id,
                Filing.filed_at >= window_start,
                Filing.filed_at <= window_end,
            )
            .all()
        )
    ]
    events = [
        {
            "ticker": e.ticker_label,
            "type": e.event_type,
            "severity": e.severity,
            "source": e.source,
            "description": e.description,
            "at": e.event_at.isoformat(),
        }
        for e in (
            s.query(Event)
            .filter(
                Event.event_at >= window_start,
                Event.event_at <= window_end,
                (Event.company_id == company.company_id) | (Event.company_id.is_(None)),
            )
            .limit(20)
            .all()
        )
    ]
    macro = [
        {
            "series": m.series_id,
            "label": m.label,
            "change_90d_pct": m.change_90d_pct,
            "direction": m.direction,
        }
        for m in s.query(MacroSeries).all()
    ]

    attrs = build_attributions(s)
    contribution = attrs.get(earnings_id)
    drivers = (
        [
            {
                "feature": c.feature,
                "value": round(c.value, 3),
                "coefficient": round(c.coefficient, 3),
                "contribution": round(c.contribution, 3),
            }
            for c in contribution.contributions[:5]
        ]
        if contribution
        else []
    )

    return {
        "event": {
            "ticker": company.ticker,
            "name": company.name,
            "segment": company.segment,
            "fiscal_period": earn.fiscal_period,
            "report_date": earn.report_date.isoformat(),
            "time_of_day": earn.time_of_day,
            "eps_estimate": earn.eps_estimate,
            "eps_actual": earn.eps_actual,
            "eps_surprise_pct": oc.eps_surprise_pct,
            "revenue_estimate": earn.revenue_estimate,
            "revenue_actual": earn.revenue_actual,
            "eps_beat": oc.eps_beat,
            "reaction": oc.reaction,
            "post_earnings_1d_return": oc.post_earnings_1d_return,
            "post_earnings_5d_return": oc.post_earnings_5d_return,
        },
        "top_drivers": drivers,
        "news_pm7": news,
        "filings_pm7": filings,
        "events_pm7": events,
        "macro_context": macro,
    }


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"response missing JSON: {text[:200]}")
    return json.loads(text[start : end + 1])


def run_once(force: bool = False, limit: int = 20) -> int:
    """Generate postmortems for past earnings that don't yet have one.

    With force=True, regenerates even if a postmortem already exists.
    Caps at `limit` calls per run to keep API cost bounded."""
    with source_run("postmortem") as run:
        settings = get_settings()
        if not settings.anthropic_api_key:
            run.skip = True
            return 0
        try:
            import anthropic
        except ImportError:
            run.skip = True
            return 0

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        written = 0
        with SessionLocal() as s:
            candidates = [
                e.earnings_id
                for e in s.query(Earnings)
                .filter(Earnings.eps_actual.isnot(None))
                .order_by(Earnings.report_date.desc())
                .all()
            ]
            for earnings_id in candidates[:limit]:
                existing = s.get(EarningsPostmortem, earnings_id)
                if existing is not None and not force:
                    continue
                snap = _snapshot(s, earnings_id)
                if snap is None:
                    continue
                try:
                    resp = client.messages.create(
                        model=MODEL,
                        max_tokens=900,
                        system=SYSTEM_PROMPT,
                        messages=[
                            {
                                "role": "user",
                                "content": "Snapshot:\n" + json.dumps(snap, indent=2, default=str),
                            }
                        ],
                    )
                    text = "".join(
                        b.text for b in resp.content if getattr(b, "type", None) == "text"
                    )
                    body = _extract_json(text)
                except Exception as exc:  # noqa: BLE001
                    log.warning("earnings_id=%s postmortem failed: %s", earnings_id, exc)
                    continue

                rec = existing or EarningsPostmortem(earnings_id=earnings_id)
                rec.generated_at = datetime.utcnow()
                rec.model = MODEL
                rec.token_count = int(
                    getattr(resp.usage, "output_tokens", 0) or 0
                )
                rec.headline = (body.get("headline") or "")[:256]
                rec.narrative = body.get("narrative") or ""
                rec.tags = [t for t in (body.get("tags") or []) if isinstance(t, str)][:10]
                if existing is None:
                    s.add(rec)
                written += 1
            s.commit()
        run.rows_fetched = written
        return written


if __name__ == "__main__":
    run_once()
