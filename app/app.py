from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui import (
    COLORS,
    ManagementAlert,
    alerts_panel,
    chart,
    company_profile,
    csv_download,
    dataframe,
    date_filter,
    header,
    metric_row,
    money,
    number,
    render_chart,
    section_heading,
    setup_page,
    sidebar_footer,
    sidebar_notice,
    sidebar_section,
)

from src.analytics import (
    available_date_range,
    customer_abc,
    orders_detail,
    receivables,
    sales_detail,
)
from src.database import engine
from src.generator import create_schema, initialize_history
from src.metrics import comparable_previous_period
from src.models import Order

NAVIGATION_ICONS = {
    "Resumen ejecutivo": "home",
    "Facturación y ventas": "query_stats",
    "Pedidos": "inventory_2",
    "Cuentas corrientes": "account_balance_wallet",
    "Clientes y ABC": "groups",
}

COMPANY_DESCRIPTION = (
    "Envaplast S.A. es una pyme industrial ficticia radicada en Argentina que fabrica "
    "botellas, frascos, bidones, baldes y sistemas de cierre plásticos. Abastece a "
    "distribuidores, comercios e industrias de distintas provincias mediante venta "
    "mayorista y condiciones de crédito adaptadas a cada segmento."
)


@st.cache_resource
def bootstrap() -> bool:
    create_schema(engine)
    with engine.connect() as connection:
        order_count = connection.scalar(select(func.count()).select_from(Order)) or 0
    if order_count == 0:
        initialize_history(engine)
    return True


@st.cache_data(ttl=900)
def load_data():
    return sales_detail(engine), orders_detail(engine), receivables(engine), customer_abc(engine)


def select_values(frame: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    values = sorted(frame[column].dropna().unique().tolist())
    selected = st.sidebar.multiselect(label, values)
    return frame[frame[column].isin(selected)] if selected else frame


def summary(
    sales: pd.DataFrame, orders: pd.DataFrame, ar: pd.DataFrame, start: date, end: date
) -> None:
    header(
        "Resumen ejecutivo",
        "Transformando datos comerciales en decisiones de negocio.",
        f"{start:%d/%m/%Y} — {end:%d/%m/%Y}",
    )
    current = sales[sales.invoice_date.dt.date.between(start, end)]
    p_start, p_end = comparable_previous_period(start.replace(day=1), end)
    previous = sales[sales.invoice_date.dt.date.between(p_start, p_end)]
    revenue = current.groupby("invoice_id").total_amount.first().sum()
    prior = previous.groupby("invoice_id").total_amount.first().sum()
    delta = (revenue / prior - 1) * 100 if prior else 0
    current_orders = orders[orders.order_date.dt.date.between(start, end)]
    open_orders = orders[~orders.status.isin(["entregado", "cancelado"])]
    open_ar = ar[ar.balance > 0.01]
    overdue = open_ar[open_ar.derived_status == "vencida"].balance.sum()
    paid = ar[(ar.derived_status == "pagada") & ar.last_collection_date.notna()].copy()
    paid["collection_days"] = (
        pd.to_datetime(paid.last_collection_date) - paid.invoice_date
    ).dt.days

    section_heading(
        "Indicadores principales",
        "Los valores con mayor impacto en la gestión del período.",
    )
    metric_row(
        [
            (
                "Facturación",
                money(revenue),
                f"{delta:+.1f}% vs. {p_start:%d/%m}-{p_end:%d/%m}",
            ),
            ("Cuentas por cobrar", money(open_ar.balance.sum()), None),
            ("Deuda vencida", money(overdue), None),
            ("Pedidos pendientes", number(open_orders.order_id.nunique()), None),
        ],
        key="kpi_primary",
    )
    section_heading(
        "Indicadores operativos",
        "Volumen, actividad comercial y eficiencia de cobranza.",
    )
    metric_row(
        [
            ("Unidades vendidas", number(current.billed_quantity.sum()), None),
            ("Pedidos ingresados", number(current_orders.order_id.nunique()), None),
            (
                "Cartera vencida",
                f"{overdue / open_ar.balance.sum() * 100:.1f}%"
                if open_ar.balance.sum()
                else "0,0%",
                None,
            ),
            (
                "Días promedio de cobro",
                f"{paid.collection_days.mean():.1f}" if not paid.empty else "—",
                None,
            ),
        ],
        key="kpi_operational",
    )
    company_profile(COMPANY_DESCRIPTION)

    monthly = (
        sales.groupby(sales.invoice_date.dt.to_period("M"))
        .agg(
            revenue=(
                "total_amount",
                lambda s: s.groupby(sales.loc[s.index, "invoice_id"]).first().sum(),
            )
        )
        .reset_index()
    )
    monthly["invoice_date"] = monthly.invoice_date.astype(str)
    section_heading(
        "Evolución mensual de facturación",
        "Tendencia de los últimos 18 meses disponibles para contextualizar el período.",
    )
    render_chart(
        chart(
            monthly.tail(18),
            "line",
            "invoice_date",
            "revenue",
            "Evolución mensual de facturación",
        )
    )

    alerts: list[ManagementAlert] = []
    if delta < -10:
        alerts.append(
            ManagementAlert("crítico", f"La facturación comparable cae {abs(delta):.1f}%.")
        )
    if open_ar.balance.sum() and overdue / open_ar.balance.sum() > 0.25:
        alerts.append(ManagementAlert("crítico", "Más del 25% de la cartera está vencida."))
    if not open_orders.empty:
        alerts.append(
            ManagementAlert(
                "atención",
                f"Hay {open_orders.order_id.nunique()} pedidos pendientes de entrega.",
            )
        )
    alerts_panel(alerts)


def sales_page(sales: pd.DataFrame, start: date, end: date) -> None:
    header(
        "Facturación y ventas",
        "Evolución, mix comercial y detalle descargable.",
        f"{start:%d/%m/%Y} — {end:%d/%m/%Y}",
    )
    frame = sales[sales.invoice_date.dt.date.between(start, end)]
    frame = select_values(frame, "customer_name", "Cliente")
    frame = select_values(frame, "product_family", "Familia de producto")
    frame = select_values(frame, "province", "Provincia")
    if frame.empty:
        st.warning("No hay ventas para los filtros seleccionados.")
        return
    metric_row(
        [
            ("Facturación", money(frame.allocated_total.sum()), None),
            ("Unidades", number(frame.billed_quantity.sum()), None),
            ("Precio promedio", money(frame.net_amount.sum() / frame.quantity.sum()), None),
        ],
        key="kpi_sales",
    )
    daily = frame.groupby(frame.invoice_date.dt.date).allocated_total.sum().reset_index()
    family = frame.groupby("product_family").allocated_total.sum().reset_index()
    customer = frame.groupby("customer_name").allocated_total.sum().nlargest(12).reset_index()
    left, right = st.columns(2)
    with left:
        render_chart(chart(daily, "line", "invoice_date", "allocated_total", "Facturación diaria"))
    with right:
        render_chart(
            chart(
                family,
                "bar",
                "allocated_total",
                "product_family",
                "Ventas por familia",
                orientation="h",
                sort_values=True,
            )
        )
    render_chart(
        chart(
            customer,
            "bar",
            "allocated_total",
            "customer_name",
            "Principales clientes",
            orientation="h",
            sort_values=True,
        )
    )
    section_heading("Detalle de ventas", "Registros incluidos en los filtros seleccionados.")
    dataframe(frame, key="sales_table")
    csv_download(frame, "ventas_envaplast.csv")


def orders_page(orders: pd.DataFrame, start: date, end: date) -> None:
    header(
        "Pedidos",
        "Backlog, cumplimiento y desempeño de entregas.",
        f"{start:%d/%m/%Y} — {end:%d/%m/%Y}",
    )
    frame = orders[orders.order_date.dt.date.between(start, end)]
    frame = select_values(frame, "status", "Estado del pedido")
    open_frame = frame[~frame.status.isin(["entregado", "cancelado"])]
    delivered = frame[frame.delivery_date.notna()].copy()
    delivered["lead_days"] = (delivered.delivery_date - delivered.order_date).dt.days
    delivered["on_time"] = delivered.delivery_date <= delivered.promised_date
    metric_row(
        [
            ("Pedidos", number(frame.order_id.nunique()), None),
            ("Importe ingresado", money(frame.order_amount.sum()), None),
            ("Pendientes", number(open_frame.order_id.nunique()), None),
            (
                "Cumplimiento prometido",
                f"{delivered.on_time.mean() * 100:.1f}%" if not delivered.empty else "—",
                None,
            ),
        ],
        key="kpi_orders",
    )
    left, right = st.columns(2)
    status = frame.groupby("status").order_id.nunique().reset_index()
    with left:
        render_chart(chart(status, "bar", "status", "order_id", "Pedidos por estado"))
    trend = frame.groupby(frame.order_date.dt.date).order_id.nunique().reset_index()
    with right:
        render_chart(chart(trend, "line", "order_date", "order_id", "Pedidos ingresados por día"))
    delayed = frame[
        (frame.promised_date.dt.date < end) & ~frame.status.isin(["entregado", "cancelado"])
    ]
    section_heading(
        f"Pedidos demorados ({len(delayed)})",
        "Pedidos cuya fecha prometida ya transcurrió y todavía no fueron entregados.",
    )
    dataframe(delayed, key="orders_table")
    csv_download(frame, "pedidos_envaplast.csv")


def ar_page(ar: pd.DataFrame, start: date, end: date) -> None:
    header(
        "Cuentas corrientes",
        "Saldos, mora y concentración de riesgo.",
        f"{start:%d/%m/%Y} — {end:%d/%m/%Y}",
    )
    frame = ar[(ar.invoice_date.dt.date <= end) & (ar.balance > 0.01)]
    frame = select_values(frame, "derived_status", "Estado de factura")
    frame = select_values(frame, "customer_name", "Cliente")
    overdue = frame[frame.derived_status == "vencida"]
    customer = frame.groupby(
        ["customer_id", "customer_name", "credit_limit"], as_index=False
    ).balance.sum()
    metric_row(
        [
            ("Saldo pendiente", money(frame.balance.sum()), None),
            ("Saldo vencido", money(overdue.balance.sum()), None),
            (
                "Mora promedio",
                f"{overdue.days_past_due.mean():.1f} días" if not overdue.empty else "0 días",
                None,
            ),
            ("Sobre límite", number((customer.balance > customer.credit_limit).sum()), None),
        ],
        key="kpi_receivables",
    )
    aging = (
        frame.groupby("aging_bucket")
        .balance.sum()
        .reindex(
            ["No vencido", "1-30 días", "31-60 días", "61-90 días", ">90 días"],
            fill_value=0,
        )
        .reset_index()
    )
    concentration = customer.nlargest(12, "balance")
    left, right = st.columns(2)
    with left:
        render_chart(chart(aging, "bar", "aging_bucket", "balance", "Antigüedad de saldos"))
    with right:
        render_chart(
            chart(
                concentration,
                "bar",
                "balance",
                "customer_name",
                "Concentración por cliente",
                orientation="h",
                sort_values=True,
            )
        )
    section_heading("Detalle de cuentas corrientes", "Composición de los saldos pendientes.")
    dataframe(frame, key="receivables_table")
    csv_download(frame, "cuentas_corrientes_envaplast.csv")


def abc_page(abc: pd.DataFrame, sales: pd.DataFrame, start: date, end: date) -> None:
    header(
        "Clientes y análisis ABC",
        "Concentración de facturación móvil de 12 meses.",
        f"{start:%d/%m/%Y} — {end:%d/%m/%Y}",
    )
    category = st.sidebar.multiselect("Categoría ABC", ["A", "B", "C"])
    frame = abc[abc.abc.isin(category)] if category else abc
    metric_row(
        [
            ("Clientes A", number((abc.abc == "A").sum()), None),
            ("Clientes B", number((abc.abc == "B").sum()), None),
            ("Clientes C", number((abc.abc == "C").sum()), None),
            ("Top 10 / ventas", f"{abc.head(10).share.sum() * 100:.1f}%", None),
        ],
        key="kpi_abc",
    )
    plot = frame.head(30).copy()
    fig = chart(
        plot,
        "bar",
        "revenue",
        "customer_name",
        "Facturación y categoría por cliente",
        color="abc",
        orientation="h",
        sort_values=True,
    )
    for trace in fig.data:
        trace.marker.color = {"A": COLORS[0], "B": COLORS[1], "C": COLORS[2]}.get(
            trace.name,
            COLORS[4],
        )
    render_chart(fig)
    customers = sorted(abc.customer_name.dropna().unique().tolist(), key=str.casefold)
    selected = st.selectbox("Explorar cliente", customers)
    history = (
        sales[sales.customer_name == selected]
        .groupby(sales.invoice_date.dt.to_period("M"))
        .net_amount.sum()
        .reset_index()
    )
    history["invoice_date"] = history.invoice_date.astype(str)
    render_chart(chart(history, "line", "invoice_date", "net_amount", f"Evolución de {selected}"))
    section_heading("Cartera de clientes", "Clasificación y participación sobre ventas.")
    dataframe(frame, key="abc_table")
    csv_download(frame, "clientes_abc_envaplast.csv")


def main() -> None:
    setup_page()
    bootstrap()
    with st.sidebar:
        st.image(str(APP_DIR / "assets" / "envaplast-logo.svg"), width="stretch")
        with st.container(key="sidebar_identity"):
            st.subheader("Envaplast Analytics", anchor=False)
            st.html('<div class="sidebar-subtitle">Business Intelligence Platform</div>')
        sidebar_section("PLATAFORMA")
        with st.expander("Sobre la empresa", icon=":material/factory:"):
            st.write(COMPANY_DESCRIPTION)
        sidebar_section("NAVEGACIÓN")
        page = st.radio(
            "Seleccioná un tablero",
            list(NAVIGATION_ICONS),
            format_func=lambda option: f":material/{NAVIGATION_ICONS[option]}: {option}",
            key="navigation",
            width="stretch",
            label_visibility="collapsed",
        )
    minimum, maximum = available_date_range(engine)
    with st.sidebar:
        sidebar_section("RANGO DE FECHAS")
    start, end = date_filter(minimum, maximum)
    with st.sidebar:
        sidebar_notice()
        sidebar_footer()
    try:
        sales, orders, ar, abc = load_data()
        {
            "Resumen ejecutivo": summary,
            "Facturación y ventas": sales_page,
            "Pedidos": orders_page,
            "Cuentas corrientes": ar_page,
        }.get(page, abc_page)(
            *(
                (sales, orders, ar, start, end)
                if page == "Resumen ejecutivo"
                else (sales, start, end)
                if page == "Facturación y ventas"
                else (orders, start, end)
                if page == "Pedidos"
                else (ar, start, end)
                if page == "Cuentas corrientes"
                else (abc, sales, start, end)
            )
        )
    except Exception as exc:
        st.error("No fue posible cargar el tablero. Revisá la conexión y la carga inicial.")
        st.exception(exc)


if __name__ == "__main__":
    main()
