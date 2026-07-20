from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def invoice_status(total: float, collected: float, due_date: date, as_of: date) -> str:
    if collected >= total - 0.01:
        return "pagada"
    if collected > 0:
        return "parcialmente pagada"
    return "vencida" if due_date < as_of else "pendiente"


def days_past_due(due_date: date, as_of: date, paid_date: date | None = None) -> int:
    reference = paid_date or as_of
    return max(0, (reference - due_date).days)


def aging_bucket(due_date: date, as_of: date) -> str:
    days = (as_of - due_date).days
    if days <= 0:
        return "No vencido"
    if days <= 30:
        return "1-30 días"
    if days <= 60:
        return "31-60 días"
    if days <= 90:
        return "61-90 días"
    return ">90 días"


def comparable_previous_period(start: date, end: date) -> tuple[date, date]:
    previous_month_end = start - timedelta(days=1)
    previous_start = previous_month_end.replace(day=1)
    days_elapsed = (end - start).days
    return previous_start, min(previous_start + timedelta(days=days_elapsed), previous_month_end)


def abc_classification(frame: pd.DataFrame, value_col: str = "revenue") -> pd.DataFrame:
    result = frame.copy().sort_values(value_col, ascending=False).reset_index(drop=True)
    total = result[value_col].sum()
    result["share"] = result[value_col] / total if total else 0
    result["cumulative_share"] = result["share"].cumsum()
    prior = result["cumulative_share"] - result["share"]
    result["abc"] = prior.map(lambda value: "A" if value < 0.80 else "B" if value <= 0.95 else "C")
    return result
