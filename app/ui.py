from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

COLORS = ["#1B4965", "#2A9D8F", "#E9C46A", "#E76F51", "#6C757D"]


def setup_page() -> None:
    st.set_page_config(page_title="Envaplast Analytics", page_icon="♻️", layout="wide")
    st.markdown(
        """
    <style>
    .block-container {padding-top: 1.6rem; max-width: 1500px;}
    [data-testid="stMetric"] {background:#f6f8fa;border:1px solid #e2e8f0;padding:14px;border-radius:12px;}
    [data-testid="stSidebar"] {border-right:1px solid #e5e7eb;}
    .synthetic {padding:.65rem .8rem;border-left:4px solid #2A9D8F;background:#edf7f5;border-radius:6px;}
    </style>
    """,
        unsafe_allow_html=True,
    )


def money(value: float) -> str:
    return f"$ {value:,.0f}".replace(",", ".")


def number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def chart(frame: pd.DataFrame, kind: str, x: str, y: str, title: str, color: str | None = None):
    factory = px.line if kind == "line" else px.bar
    fig = factory(frame, x=x, y=y, color=color, title=title, color_discrete_sequence=COLORS)
    fig.update_layout(
        margin=dict(l=10, r=10, t=55, b=10),
        legend_title_text="",
        hovermode="x unified" if kind == "line" else "closest",
    )
    if kind == "line":
        fig.update_traces(line_width=3)
    return fig


def csv_download(frame: pd.DataFrame, filename: str) -> None:
    st.download_button(
        "Descargar detalle CSV", frame.to_csv(index=False).encode("utf-8-sig"), filename, "text/csv"
    )


def date_filter(min_date: date, max_date: date) -> tuple[date, date]:
    selected = st.sidebar.date_input(
        "Rango de fechas",
        value=(max(min_date, date(max_date.year, max_date.month, 1)), max_date),
        min_value=min_date,
        max_value=max_date,
    )
    return selected if isinstance(selected, tuple) and len(selected) == 2 else (min_date, max_date)
