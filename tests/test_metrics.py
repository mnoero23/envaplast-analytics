from datetime import date

import pandas as pd

from src.metrics import (
    abc_classification,
    aging_bucket,
    comparable_previous_period,
    days_past_due,
    invoice_status,
)


def test_invoice_states_and_mora():
    assert invoice_status(121, 0, date(2026, 1, 10), date(2026, 1, 11)) == "vencida"
    assert invoice_status(121, 50, date(2026, 1, 10), date(2026, 1, 11)) == "parcialmente pagada"
    assert invoice_status(121, 121, date(2026, 1, 10), date(2026, 1, 11)) == "pagada"
    assert days_past_due(date(2026, 1, 10), date(2026, 2, 1)) == 22
    assert aging_bucket(date(2025, 10, 1), date(2026, 2, 1)) == ">90 días"


def test_comparable_period_clamps_short_month():
    assert comparable_previous_period(date(2026, 3, 1), date(2026, 3, 31)) == (
        date(2026, 2, 1),
        date(2026, 2, 28),
    )


def test_abc_keeps_threshold_crossing_customer_in_previous_class():
    result = abc_classification(pd.DataFrame({"customer": ["a", "b", "c"], "revenue": [79, 16, 5]}))
    assert result.abc.tolist() == ["A", "A", "B"]
    assert round(result.share.sum(), 8) == 1
