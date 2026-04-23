"""Shared query filters used across list endpoints."""

from __future__ import annotations

from datetime import date, datetime, time

from fastapi import HTTPException, Query


def _parse(name: str, value: str | None) -> date | None:
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {name}: expected YYYY-MM-DD")


def parse_range(
    start_date: str | None, end_date: str | None
) -> tuple[date | None, date | None]:
    s = _parse("start_date", start_date)
    e = _parse("end_date", end_date)
    if s is not None and e is not None and s > e:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    return s, e


def apply_date_range(query, column, start_date: str | None, end_date: str | None, *,
                     is_datetime: bool):
    """Narrow `query` to rows whose `column` falls within [start, end].

    Both bounds are inclusive. Set is_datetime=True when `column` is a
    DateTime so we cap at end-of-day on the `end_date` side."""
    s, e = parse_range(start_date, end_date)
    if s is not None:
        if is_datetime:
            query = query.filter(column >= datetime.combine(s, time.min))
        else:
            query = query.filter(column >= s)
    if e is not None:
        if is_datetime:
            query = query.filter(column <= datetime.combine(e, time.max))
        else:
            query = query.filter(column <= e)
    return query


def date_range_query():
    """Reusable Query-annotated params for endpoints that accept a range."""
    return (
        Query(default=None, description="Inclusive start date (YYYY-MM-DD)"),
        Query(default=None, description="Inclusive end date (YYYY-MM-DD)"),
    )
