from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

COLORS = ["#1B4965", "#2A9D8F", "#D9A441", "#D86C4F", "#71808C"]

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
        /* Streamlit no ofrece tokens para el ancho útil, la grilla de métricas ni
           su tipografía interna. Los selectores data-testid quedan acotados a esos
           ajustes visuales y no alteran el comportamiento de los componentes. */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3.5rem;
            max-width: 1380px;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border-color: #dfe6eb;
            box-shadow: 0 1px 2px rgba(18, 38, 52, 0.035);
            padding: 1rem 1rem 0.9rem;
        }
        [data-testid="stMetricLabel"] {
            min-height: 1.8rem;
            align-items: flex-start;
            color: #61717f;
            font-size: 0.82rem;
            font-weight: 550;
        }
        [data-testid="stMetricValue"] {
            color: #183c53;
            font-size: clamp(1.2rem, 1.65vw, 1.55rem);
            font-weight: 640;
            letter-spacing: -0.035em;
            line-height: 1.15;
        }
        [class*="st-key-kpi_"] {
            flex-wrap: nowrap;
        }
        [class*="st-key-kpi_"] > [data-testid="stElementContainer"] {
            flex: 1 1 0 !important;
        }
        [class*="st-key-kpi_"] [data-testid="stMetric"] {
            min-width: 0;
        }
        .st-key-executive_header {
            background: #f8fafb;
            border: 1px solid #dfe7ec;
            border-left: 3px solid #1b4965;
            border-radius: 10px;
            padding: 1.3rem 1.4rem 1.05rem;
            margin-bottom: 1rem;
        }
        .st-key-executive_header h1 {
            color: #183c53;
            letter-spacing: -0.04em;
            line-height: 1.1;
            padding-bottom: 0.25rem;
        }
        .st-key-executive_header p {
            line-height: 1.45;
        }
        .st-key-alerts_panel {
            background: #fbfcfd;
            border-color: #dfe6eb;
            box-shadow: none;
        }
        .st-key-sidebar_identity h2 {
            color: #183c53;
            padding-bottom: 0;
            letter-spacing: -0.02em;
        }
        .st-key-sidebar_nav_label p,
        .st-key-sidebar_filter_label p,
        .st-key-sidebar_context_label p {
            color: #788792;
            font-size: 0.72rem;
            font-weight: 650;
            letter-spacing: 0.08em;
            margin-top: 0.55rem;
            text-transform: uppercase;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 1.35rem;
        }
        section[data-testid="stSidebar"] hr {
            margin: 0.75rem 0;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label {
            border-radius: 7px;
            padding: 0.35rem 0.5rem;
            transition: background-color 120ms ease;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: #e9f0f4;
            color: #183c53;
            font-weight: 600;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: #eef3f6;
        }
        @media (max-width: 900px) {
            .block-container {padding-top: 1rem; padding-bottom: 2.5rem;}
            .st-key-executive_header {padding: 1rem 1rem 0.8rem;}
            [class*="st-key-kpi_"] {
                flex-wrap: wrap;
            }
            [class*="st-key-kpi_"] > [data-testid="stElementContainer"] {
                flex-basis: 14rem !important;
            }
            [class*="st-key-kpi_"] [data-testid="stMetric"] {
                min-width: min(100%, 14rem);
            }
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
                height=118,
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
        margin=dict(l=14, r=14, t=58, b=16),
        height=370,
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
        font=dict(
            color="#41515D",
            size=12,
            family="Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        ),
        title=dict(font=dict(color="#183C53", size=16), x=0.01, xanchor="left"),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color="#202B33", bordercolor="#D6E0E6"),
        bargap=0.34,
        separators=",.",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(
        showgrid=value_axis == "x",
        gridcolor="#EEF2F4",
        linecolor="#E1E7EB",
        tickfont=dict(color="#6A7A86"),
        automargin=True,
        separatethousands=True,
    )
    fig.update_yaxes(
        showgrid=value_axis == "y",
        gridcolor="#EEF2F4",
        gridwidth=1,
        zeroline=False,
        tickfont=dict(color="#6A7A86"),
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
        fig.update_traces(line_width=2.5, marker=dict(size=5), mode="lines+markers")
    else:
        fig.update_traces(marker_line_width=0, opacity=0.96, cliponaxis=False)
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
