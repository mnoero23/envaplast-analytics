from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

COLORS = ["#1B4965", "#2A9D8F", "#E9C46A", "#E76F51", "#6C757D"]

MONEY_COLUMNS = {
    "subtotal",
    "tax_amount",
    "total_amount",
    "allocated_total",
    "unit_price",
    "net_amount",
    "order_amount",
    "credit_limit",
    "collected_amount",
    "balance",
    "revenue",
}
INTEGER_COLUMNS = {
    "quantity",
    "billed_quantity",
    "units",
    "days_past_due",
}
PERCENT_COLUMNS = {
    "discount_percentage",
    "delivered_percentage",
}
RATIO_COLUMNS = {"share", "cumulative_share"}
DATE_COLUMNS = {
    "invoice_date",
    "due_date",
    "order_date",
    "promised_date",
    "delivery_date",
    "last_collection_date",
}

SPANISH_LABELS = {
    "invoice_id": "ID factura",
    "invoice_date": "Fecha de factura",
    "due_date": "Fecha de vencimiento",
    "invoice_number": "Número de factura",
    "invoice_status": "Estado de factura",
    "subtotal": "Subtotal",
    "tax_amount": "IVA",
    "total_amount": "Importe total",
    "allocated_total": "Facturación",
    "customer_id": "ID cliente",
    "customer_name": "Cliente",
    "segment": "Segmento",
    "province": "Provincia",
    "region": "Región",
    "order_id": "ID pedido",
    "order_date": "Fecha de pedido",
    "promised_date": "Fecha prometida",
    "status": "Estado",
    "sales_channel": "Canal de venta",
    "product_id": "ID producto",
    "sku": "SKU",
    "product_name": "Producto",
    "product_family": "Familia de producto",
    "quantity": "Unidades pedidas",
    "billed_quantity": "Unidades facturadas",
    "unit_price": "Precio unitario",
    "discount_percentage": "Descuento (%)",
    "net_amount": "Importe neto",
    "order_amount": "Importe del pedido",
    "units": "Unidades",
    "delivery_date": "Fecha de entrega",
    "delivery_status": "Estado de entrega",
    "delivered_percentage": "Entregado (%)",
    "credit_limit": "Límite de crédito",
    "collected_amount": "Importe cobrado",
    "last_collection_date": "Última cobranza",
    "balance": "Saldo pendiente",
    "days_past_due": "Días de mora",
    "aging_bucket": "Antigüedad",
    "derived_status": "Estado calculado",
    "revenue": "Facturación últimos 12 meses",
    "share": "Participación",
    "cumulative_share": "Participación acumulada",
    "abc": "Categoría ABC",
}

type MetricItem = tuple[str, str, str | None]
type AlertLevel = Literal["crítico", "atención", "información", "correcto"]


@dataclass(frozen=True)
class ManagementAlert:
    level: AlertLevel
    text: str


def setup_page() -> None:
    st.set_page_config(
        page_title="Envaplast Analytics",
        page_icon=":material/analytics:",
        layout="wide",
    )
    st.html(
        """
        <style>
        /* Streamlit no ofrece tokens para el ancho útil ni la tipografía interna
           de st.metric. Estos dos selectores se limitan a esos ajustes visuales. */
        .block-container {
            padding-top: 1.35rem;
            padding-bottom: 2.5rem;
            max-width: 1480px;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
            box-shadow: 0 3px 12px rgba(27, 73, 101, 0.07);
        }
        [data-testid="stMetricLabel"] {
            min-height: 2.15rem;
            align-items: flex-start;
            color: #526476;
        }
        [data-testid="stMetricValue"] {
            color: #173f58;
            font-weight: 650;
            letter-spacing: -0.025em;
        }
        .st-key-executive_header {
            background: linear-gradient(120deg, #f1f6f9 0%, #f8fbfc 70%, #edf7f5 100%);
            border: 1px solid #d5e1e8;
            border-left: 5px solid #1B4965;
            border-radius: 14px;
            padding: 1.15rem 1.35rem 0.9rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 5px 18px rgba(27, 73, 101, 0.07);
        }
        .st-key-executive_header h1 {
            color: #173f58;
            letter-spacing: -0.035em;
            padding-bottom: 0.15rem;
        }
        .st-key-alerts_panel {
            background: #fbfcfd;
            border-color: #d8e2e9;
            box-shadow: 0 3px 12px rgba(27, 73, 101, 0.05);
        }
        .st-key-sidebar_identity h2 {
            color: #173f58;
            padding-bottom: 0;
        }
        @media (max-width: 900px) {
            .block-container {padding-top: 1rem;}
            .st-key-executive_header {padding: 1rem 1rem 0.75rem;}
        }
        </style>
        """
    )


def money(value: float) -> str:
    return f"$ {value:,.0f}".replace(",", ".")


def number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def header(
    title: str,
    subtitle: str,
    period: str | None = None,
    badge: str | None = "Datos sintéticos",
) -> None:
    with st.container(key="executive_header"):
        main, metadata = st.columns([4, 1.25], vertical_alignment="center")
        with main:
            st.title(title, anchor=False)
            st.caption(subtitle)
        with metadata:
            if badge:
                st.badge(badge, icon=":material/database:", color="blue")
            if period:
                st.caption("Período analizado")
                st.markdown(f"**{period}**")


def section_heading(title: str, caption: str | None = None) -> None:
    st.subheader(title, anchor=False)
    if caption:
        st.caption(caption)


def metric_row(metrics: Sequence[MetricItem], *, key: str) -> None:
    with st.container(horizontal=True, gap="small", key=key):
        for label, value, delta in metrics:
            st.metric(
                label,
                value,
                delta,
                border=True,
                width="stretch",
                height=128,
            )


def alerts_panel(alerts: Sequence[ManagementAlert]) -> None:
    settings: dict[AlertLevel, tuple[str, str, str]] = {
        "crítico": (":material/error:", "red", "Crítico"),
        "atención": (":material/warning:", "orange", "Atención"),
        "información": (":material/info:", "blue", "Información"),
        "correcto": (":material/check_circle:", "green", "Correcto"),
    }
    visible_alerts = list(alerts) or [
        ManagementAlert(
            "correcto",
            "No se detectaron desvíos relevantes con las reglas actuales.",
        )
    ]
    with st.container(border=True, key="alerts_panel"):
        st.subheader("Alertas de gestión", anchor=False)
        st.caption("Señales generadas a partir de las reglas actuales del tablero.")
        for alert in visible_alerts:
            icon, color, label = settings[alert.level]
            with st.container(
                horizontal=True,
                vertical_alignment="center",
                gap="small",
            ):
                st.badge(label, icon=icon, color=color, width="content")
                st.write(alert.text)


def _format_hover_value(column: str, value: object) -> str:
    if pd.isna(value):
        return "—"
    if column in MONEY_COLUMNS:
        return money(float(value))
    if column in RATIO_COLUMNS:
        return f"{float(value) * 100:.1f}%".replace(".", ",")
    if column in PERCENT_COLUMNS:
        return f"{float(value):.1f}%".replace(".", ",")
    if column in INTEGER_COLUMNS or isinstance(value, int):
        return number(float(value))
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return pd.Timestamp(value).strftime("%d/%m/%Y")
    if isinstance(value, float):
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)


def chart(
    frame: pd.DataFrame,
    kind: Literal["line", "bar"],
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    *,
    orientation: Literal["h", "v"] | None = None,
    sort_values: bool = False,
) -> go.Figure:
    plot_frame = frame.copy()
    resolved_orientation = orientation or "v"
    value_column = x if resolved_orientation == "h" else y
    if sort_values and kind == "bar":
        plot_frame = plot_frame.sort_values(
            value_column,
            ascending=resolved_orientation == "h",
        )
    hover_column = "_formatted_value"
    plot_frame[hover_column] = plot_frame[value_column].map(
        lambda value: _format_hover_value(value_column, value)
    )
    common = {
        "data_frame": plot_frame,
        "x": x,
        "y": y,
        "color": color,
        "title": title,
        "labels": SPANISH_LABELS,
        "color_discrete_sequence": COLORS,
        "custom_data": [hover_column],
    }
    if kind == "line":
        fig = px.line(**common)
    else:
        fig = px.bar(**common, orientation=resolved_orientation)
    category_placeholder = "%{y}" if resolved_orientation == "h" else "%{x}"
    category_label = SPANISH_LABELS.get(y if resolved_orientation == "h" else x, "Categoría")
    value_label = SPANISH_LABELS.get(value_column, value_column.replace("_", " ").title())
    color_detail = f"<br>{SPANISH_LABELS.get(color, color)}: %{{fullData.name}}" if color else ""
    fig.update_traces(
        hovertemplate=(
            f"<b>{category_label}: {category_placeholder}</b>"
            f"<br>{value_label}: %{{customdata[0]}}{color_detail}<extra></extra>"
        )
    )
    value_format: Literal["money", "number", "percentage"] | None = None
    if value_column in MONEY_COLUMNS:
        value_format = "money"
    elif value_column in INTEGER_COLUMNS:
        value_format = "number"
    elif value_column in PERCENT_COLUMNS or value_column in RATIO_COLUMNS:
        value_format = "percentage"
    style_figure(
        fig,
        kind,
        value_axis="x" if resolved_orientation == "h" else "y",
        value_format=value_format,
    )
    return fig


def style_figure(
    fig: go.Figure,
    kind: Literal["line", "bar"] = "bar",
    *,
    value_axis: Literal["x", "y"] = "y",
    value_format: Literal["money", "number", "percentage"] | None = None,
) -> go.Figure:
    fig.update_layout(
        margin=dict(l=18, r=18, t=62, b=20),
        height=390,
        legend_title_text="",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified" if kind == "line" else "closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#334155", size=13, family="Arial, sans-serif"),
        title=dict(font=dict(color="#1B4965", size=17), x=0.01, xanchor="left"),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color="#1F2937", bordercolor="#CBD5E1"),
        bargap=0.28,
        separators=",.",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(
        showgrid=value_axis == "x",
        gridcolor="#E8EEF3",
        linecolor="#DCE5EC",
        tickfont=dict(color="#64748B"),
        automargin=True,
        separatethousands=True,
    )
    fig.update_yaxes(
        showgrid=value_axis == "y",
        gridcolor="#E8EEF3",
        gridwidth=1,
        zeroline=False,
        tickfont=dict(color="#64748B"),
        automargin=True,
        separatethousands=True,
    )
    axis = fig.update_xaxes if value_axis == "x" else fig.update_yaxes
    if value_format == "money":
        axis(tickprefix="$ ", tickformat=",.0f")
    elif value_format == "number":
        axis(tickformat=",.0f")
    elif value_format == "percentage":
        axis(ticksuffix=" %", tickformat=".1f")
    if kind == "line":
        fig.update_traces(line_width=3, marker=dict(size=6), mode="lines+markers")
    else:
        fig.update_traces(marker_line_width=0, opacity=0.92, cliponaxis=False)
    return fig


def render_chart(fig: go.Figure) -> None:
    with st.container(border=True):
        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )


def dataframe(frame: pd.DataFrame, *, key: str, height: int = 420) -> None:
    translated = translate_columns(frame)
    config: dict[str, object] = {}
    for original, label in zip(frame.columns, translated.columns, strict=True):
        if original in MONEY_COLUMNS:
            config[label] = st.column_config.NumberColumn(label, format="$ %.2f", width="small")
        elif original in RATIO_COLUMNS:
            config[label] = st.column_config.NumberColumn(label, format="percent", width="small")
        elif original in PERCENT_COLUMNS:
            config[label] = st.column_config.NumberColumn(label, format="%.1f%%", width="small")
        elif original in DATE_COLUMNS or pd.api.types.is_datetime64_any_dtype(frame[original]):
            config[label] = st.column_config.DatetimeColumn(
                label,
                format="DD/MM/YYYY",
                width="small",
            )
        elif original.endswith("_id") or original in INTEGER_COLUMNS:
            config[label] = st.column_config.NumberColumn(label, format="%d", width="small")
        elif original in {"customer_name", "product_name"}:
            config[label] = st.column_config.TextColumn(label, width="large", pinned=True)
        elif original in {"product_family", "province", "segment", "status"}:
            config[label] = st.column_config.TextColumn(label, width="medium")
    st.dataframe(
        translated,
        width="stretch",
        height=height,
        hide_index=True,
        column_config=config,
        key=key,
    )


def csv_download(frame: pd.DataFrame, filename: str) -> None:
    translated = translate_columns(frame)
    st.download_button(
        "Descargar detalle CSV",
        translated.to_csv(index=False).encode("utf-8-sig"),
        filename,
        "text/csv",
        icon=":material/download:",
    )


def translate_columns(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(columns=SPANISH_LABELS)


def date_filter(min_date: date, max_date: date) -> tuple[date, date]:
    selected = st.sidebar.date_input(
        "Rango de fechas",
        value=(max(min_date, date(max_date.year, max_date.month, 1)), max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
    )
    return selected if isinstance(selected, tuple) and len(selected) == 2 else (min_date, max_date)
