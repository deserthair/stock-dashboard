"""Claude-generated Overnight Synthesis.

Every call:
  1. snapshots the current universe signals, top hypothesis leaders,
     recent high-severity events, macro movers, and upcoming earnings
  2. hands the snapshot to Claude with a system prompt that specifies
     four exact sections ("Top Story", "Macro Context", "Hypothesis Watch",
     "Flags") and the <tag>TICKER</tag> + <strong>…</strong> microformat
     the frontend renders
  3. writes the new briefing to `briefings` and keeps the most recent row
     served by /api/briefing

Skipped if ANTHROPIC_API_KEY isn't set (the seeded briefing remains visible)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Briefing,
    Company,
    CompanySignal,
    Earnings,
    Event,
    MacroSeries,
)

from ingest.source_run import source_run

MODEL = "claude-sonnet-4-6"  # Synthesis quality matters more than raw cost here.

SYSTEM_PROMPT = """You write an 800-token pre-market briefing for a restaurant-industry
stock-tracking dashboard. Return JSON:

{
  "token_count": <integer estimate>,
  "sections": [
    {"heading": "Top Story",        "body": "..."},
    {"heading": "Macro Context",    "body": "..."},
    {"heading": "Hypothesis Watch", "body": "..."},
    {"heading": "Flags",            "body": "..."}
  ]
}

Exactly 4 sections with those headings, in that order. Each body is 1-2 paragraphs of
serif prose. Inside bodies use <tag>TICKER</tag> for every stock symbol and
<strong>...</strong> for key numeric facts you want bolded. Be concrete: cite the actual
percentages and counts from the snapshot. Do not invent data not in the snapshot. Do not
include any prose outside the JSON."""


def _snapshot(s) -> dict:
    companies = {c.company_id: c for c in s.query(Company).all()}
    signals = s.query(CompanySignal).all()
    universe = []
    for sig in signals:
        c = companies.get(sig.company_id)
        if c is None:
            continue
        universe.append({
            "ticker": c.ticker,
            "name": c.name,
            "price": sig.last_price,
            "change_1d_pct": sig.change_1d_pct,
            "change_30d_pct": sig.change_30d_pct,
            "rs_vs_xly": sig.rs_vs_xly,
            "news_7d": sig.news_7d_count,
            "news_pct_baseline": sig.news_volume_pct_baseline,
            "sentiment_7d": sig.sentiment_7d,
            "social_vol_z": sig.social_vol_z,
            "jobs_30d_pct": sig.jobs_change_30d_pct,
            "hypothesis_score": sig.hypothesis_score,
            "hypothesis_label": sig.hypothesis_label,
            "next_er": sig.next_er_date.isoformat() if sig.next_er_date else None,
        })
    universe.sort(
        key=lambda u: abs(u.get("hypothesis_score") or 0), reverse=True
    )

    since = datetime.utcnow() - timedelta(days=2)
    events = [
        {
            "ticker": e.ticker_label,
            "type": e.event_type,
            "severity": e.severity,
            "source": e.source,
            "description": e.description,
            "at": e.event_at.isoformat(),
        }
        for e in s.query(Event).filter(Event.event_at >= since).order_by(Event.event_at.desc()).limit(20).all()
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

    upcoming = [
        {
            "ticker": companies[e.company_id].ticker if e.company_id in companies else "?",
            "report_date": e.report_date.isoformat(),
            "time_of_day": e.time_of_day,
            "eps_estimate": e.eps_estimate,
        }
        for e in s.query(Earnings)
        .filter(Earnings.report_date >= datetime.utcnow().date())
        .order_by(Earnings.report_date)
        .limit(5)
        .all()
    ]

    return {
        "universe_top_hypotheses": universe[:6],
        "recent_events": events,
        "macro": macro,
        "upcoming_earnings": upcoming,
    }


def run_once() -> int:
    with source_run("briefing") as run:
        settings = get_settings()
        if not settings.anthropic_api_key:
            run.skip = True
            return 0

        try:
            import anthropic
        except ImportError:
            run.skip = True
            return 0

        with SessionLocal() as s:
            snapshot = _snapshot(s)
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": "Snapshot:\n" + json.dumps(snapshot, indent=2),
                    }
                ],
            )
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                raise ValueError(f"briefing response missing JSON object: {text[:200]}")
            body = json.loads(text[start : end + 1])

            sections = body.get("sections") or []
            if len(sections) != 4:
                raise ValueError(f"expected 4 sections, got {len(sections)}")

            s.add(
                Briefing(
                    generated_at=datetime.utcnow(),
                    token_count=int(body.get("token_count") or resp.usage.output_tokens),
                    sections=sections,
                )
            )
            # Keep only the 20 most recent briefings
            old = (
                s.query(Briefing)
                .order_by(Briefing.generated_at.desc())
                .offset(20)
                .all()
            )
            for b in old:
                s.delete(b)
            s.commit()

        run.rows_fetched = 1
        return 1


if __name__ == "__main__":
    run_once()
