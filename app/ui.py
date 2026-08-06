from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from typing import Literal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

COLORS = ["#2A9D8F", "#1B4965", "#69C5B8", "#E9C46A", "#E76F51", "#6C757D"]

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

KPI_ICONS = {
    "Facturación": "payments",
    "Cuentas por cobrar": "account_balance_wallet",
    "Deuda vencida": "event_busy",
    "Pedidos pendientes": "pending_actions",
    "Unidades vendidas": "inventory_2",
    "Pedidos ingresados": "receipt_long",
    "Cartera vencida": "percent",
    "Días promedio de cobro": "schedule",
    "Unidades": "inventory_2",
    "Precio promedio": "sell",
    "Pedidos": "shopping_cart",
    "Importe ingresado": "paid",
    "Pendientes": "pending_actions",
    "Cumplimiento prometido": "verified",
    "Saldo pendiente": "account_balance_wallet",
    "Saldo vencido": "event_busy",
    "Mora promedio": "schedule",
    "Sobre límite": "credit_card_off",
    "Clientes A": "looks_one",
    "Clientes B": "looks_two",
    "Clientes C": "looks_3",
    "Top 10 / ventas": "leaderboard",
}


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
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1480px;
        }
        h1, h2, h3 {
            letter-spacing: -0.025em;
        }
        .section-heading {
            border-left: 3px solid #2a9d8f;
            margin: 1.65rem 0 0.8rem;
            padding: 0.08rem 0 0.08rem 0.8rem;
        }
        .section-heading h2 {
            color: #173f58;
            font-size: 1.22rem;
            font-weight: 700;
            line-height: 1.3;
            margin: 0;
        }
        .section-heading p {
            color: #667b89;
            font-size: 0.86rem;
            line-height: 1.45;
            margin: 0.18rem 0 0;
        }
        .st-key-company_profile {
            background: linear-gradient(100deg, #f2f8f8 0%, #ffffff 100%);
            border-color: #d5e6e4;
            box-shadow: 0 5px 16px rgba(18, 55, 72, 0.06);
            margin-top: 1.2rem;
        }
        .company-profile-icon {
            align-items: center;
            background: #dff2ef;
            border-radius: 12px;
            color: #147d71;
            display: flex;
            font-size: 1.7rem;
            height: 3.25rem;
            justify-content: center;
            width: 3.25rem;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #102f3d 0%, #0b2632 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 1.15rem;
        }
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #d8e5e9;
        }
        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin: 0 auto 0.25rem;
            max-width: 270px;
        }
        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 0.35rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 0.56rem 0.68rem;
            transition: background 150ms ease, border-color 150ms ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(255, 255, 255, 0.07);
            border-color: rgba(255, 255, 255, 0.10);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: rgba(42, 157, 143, 0.22);
            border-color: rgba(89, 201, 188, 0.55);
            box-shadow: inset 3px 0 0 #4fc3b3;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
            color: #ffffff;
            font-weight: 650;
        }
        [data-testid="stSidebar"] [data-testid="stDateInput"] input {
            color: #f8fbfc;
        }
        [data-testid="stSidebar"] [data-testid="stDateInput"] > div > div {
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.18);
        }
        .sidebar-section-label {
            color: #83d5ca;
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.13em;
            margin: 1.05rem 0 0.45rem;
        }
        .sidebar-subtitle {
            color: #a9c3cc;
            font-size: 0.82rem;
            line-height: 1.35;
            margin-top: -0.25rem;
        }
        .sidebar-synthetic {
            background: rgba(42, 157, 143, 0.14);
            border: 1px solid rgba(89, 201, 188, 0.32);
            border-radius: 11px;
            color: #dff8f4;
            font-size: 0.79rem;
            line-height: 1.45;
            margin-top: 1.15rem;
            padding: 0.75rem 0.8rem;
        }
        .sidebar-footer {
            border-top: 1px solid rgba(255, 255, 255, 0.10);
            color: #8faab4;
            font-size: 0.72rem;
            line-height: 1.55;
            margin-top: 1.3rem;
            padding-top: 0.9rem;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, #ffffff 0%, #f8fbfc 100%);
            border: 1px solid #dbe6eb;
            border-top: 3px solid #2a9d8f;
            box-shadow: 0 6px 18px rgba(18, 55, 72, 0.08);
            transition: transform 160ms ease, box-shadow 160ms ease;
        }
        [data-testid="stMetric"]:hover {
            box-shadow: 0 9px 24px rgba(18, 55, 72, 0.12);
            transform: translateY(-2px);
        }
        [data-testid="stMetricLabel"] {
            min-height: 2.15rem;
            align-items: flex-start;
            color: #506675;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: #173f58;
            font-weight: 700;
            letter-spacing: -0.025em;
        }
        [data-testid="stMetricDelta"] {
            background: #edf5f3;
            border-radius: 999px;
            padding: 0.18rem 0.48rem;
            width: fit-content;
        }
        [class*="st-key-kpi_"] [data-testid="stHorizontalBlock"] {
            align-items: stretch;
            flex-wrap: wrap;
        }
        [class*="st-key-kpi_"] [data-testid="stHorizontalBlock"] > div {
            flex: 1 1 215px;
            min-width: 0;
        }
        .st-key-executive_header {
            background: linear-gradient(120deg, #f4f8fa 0%, #ffffff 66%, #edf8f6 100%);
            border: 1px solid #d5e1e8;
            border-left: 6px solid #2A9D8F;
            border-radius: 14px;
            padding: 1.35rem 1.5rem 1.05rem;
            margin-bottom: 1rem;
            box-shadow: 0 5px 18px rgba(27, 73, 101, 0.07);
        }
        .st-key-executive_header h1 {
            color: #173f58;
            letter-spacing: -0.035em;
            padding: 0.05rem 0 0.15rem;
        }
        .st-key-alerts_panel {
            background: #fbfcfd;
            border-color: #d8e2e9;
            box-shadow: 0 3px 12px rgba(27, 73, 101, 0.05);
        }
        [class*="st-key-chart_card_"] {
            background: #ffffff;
            border-color: #dbe6eb;
            box-shadow: 0 7px 22px rgba(18, 55, 72, 0.08);
            padding: 0.35rem 0.55rem 0.15rem;
        }
        [class*="st-key-chart_card_"] [data-testid="stPlotlyChart"] {
            border: 0;
            box-shadow: none;
        }
        .st-key-sidebar_identity h2 {
            color: #ffffff;
            padding-bottom: 0;
            letter-spacing: -0.025em;
        }
        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1rem;
            }
            .st-key-executive_header {
                padding: 1rem 1rem 0.75rem;
            }
            [class*="st-key-kpi_"] [data-testid="stHorizontalBlock"] > div {
                flex-basis: calc(50% - 0.5rem);
            }
        }
        @media (max-width: 620px) {
            [class*="st-key-kpi_"] [data-testid="stHorizontalBlock"] > div {
                flex-basis: 100%;
            }
            [data-testid="stMetric"] {
                min-height: 132px;
            }
            .section-heading {
                margin-top: 1.3rem;
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
            st.caption("ENVAPLAST ANALYTICS · BUSINESS INTELLIGENCE PLATFORM")
            st.title(title, anchor=False)
            st.caption(subtitle)
        with metadata:
            if badge:
                st.badge(badge, icon=":material/database:", color="blue")
            if period:
                st.caption("Período analizado")
                st.markdown(f"**{period}**")


def sidebar_section(label: str) -> None:
    st.html(f'<div class="sidebar-section-label">{label}</div>')


def sidebar_notice() -> None:
    st.html(
        """
        <div class="sidebar-synthetic">
            <strong>◉ Datos sintéticos</strong><br>
            No representan empresas ni operaciones reales.
        </div>
        """
    )


def sidebar_footer() -> None:
    st.html(
        """
        <div class="sidebar-footer">
            © 2026 Envaplast Analytics<br>
            Todos los derechos reservados.
        </div>
        """
    )


def section_heading(title: str, caption: str | None = None) -> None:
    caption_html = f"<p>{escape(caption)}</p>" if caption else ""
    st.html(f'<div class="section-heading"><h2>{escape(title)}</h2>{caption_html}</div>')


def company_profile(description: str) -> None:
    with st.container(border=True, key="company_profile"):
        icon, content = st.columns([0.45, 7], vertical_alignment="center")
        with icon:
            st.html('<div class="company-profile-icon">▦</div>')
        with content:
            st.markdown("**Sobre Envaplast**")
            st.caption(
                "Pyme industrial argentina ficticia especializada en soluciones "
                "de envases plásticos para el canal mayorista."
            )
        with st.expander("Conocer el contexto de la empresa", icon=":material/factory:"):
            st.write(description)


def metric_row(metrics: Sequence[MetricItem], *, key: str) -> None:
    with st.container(horizontal=True, gap="small", key=key):
        for label, value, delta in metrics:
            icon = KPI_ICONS.get(label, "analytics")
            st.metric(
                f":material/{icon}: {label}",
                value,
                delta,
                border=True,
                width="stretch",
                height=140,
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
        margin=dict(l=22, r=22, t=68, b=24),
        height=410,
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
        plot_bgcolor="#FCFEFE",
        font=dict(color="#334155", size=13, family="Arial, sans-serif"),
        title=dict(font=dict(color="#173F58", size=18), x=0.01, xanchor="left"),
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
        fig.update_traces(
            line_width=3,
            marker=dict(size=6, line=dict(color="#FFFFFF", width=1.5)),
            mode="lines+markers",
        )
    else:
        fig.update_traces(marker_line_width=0, opacity=0.92, cliponaxis=False)
    return fig


def render_chart(fig: go.Figure) -> None:
    title = str(fig.layout.title.text or "grafico")
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    with st.container(border=True, key=f"chart_card_{slug}"):
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
