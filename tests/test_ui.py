from __future__ import annotations

import pandas as pd

from app.ui import chart, money, number, translate_columns


def test_spanish_number_formats_and_column_labels():
    assert money(1234567) == "$ 1.234.567"
    assert number(1234567) == "1.234.567"
    translated = translate_columns(pd.DataFrame({"invoice_date": [], "balance": []}))
    assert translated.columns.tolist() == ["Fecha de factura", "Saldo pendiente"]


def test_horizontal_ranking_is_sorted_with_largest_bar_on_top():
    frame = pd.DataFrame(
        {
            "customer_name": ["Cliente A", "Cliente B", "Cliente C"],
            "revenue": [200, 500, 100],
        }
    )
    figure = chart(
        frame,
        "bar",
        "revenue",
        "customer_name",
        "Ranking",
        orientation="h",
        sort_values=True,
    )
    assert list(figure.data[0].y) == ["Cliente C", "Cliente A", "Cliente B"]
    assert figure.layout.xaxis.tickprefix == "$ "
