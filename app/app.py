from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui import COLORS, chart, csv_download, date_filter, header, money, number, setup_page

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


@st.cache_resource
def bootstrap() -> bool:
    create_schema(engine)
    minimum, maximum = available_date_range(engine)
    if minimum == maximum and minimum == date.today():
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
    header("Resumen ejecutivo", f"Tablero gerencial al {end:%d/%m/%Y}")
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
    cards = st.columns(4)
    cards[0].metric(
        "Facturación", money(revenue), f"{delta:+.1f}% vs. {p_start:%d/%m}-{p_end:%d/%m}"
    )
    cards[1].metric("Unidades vendidas", number(current.billed_quantity.sum()))
    cards[2].metric("Pedidos ingresados", number(current_orders.order_id.nunique()))
    cards[3].metric("Pedidos pendientes", number(open_orders.order_id.nunique()))
    cards = st.columns(4)
    cards[0].metric("Cuentas por cobrar", money(open_ar.balance.sum()))
    cards[1].metric("Deuda vencida", money(overdue))
    cards[2].metric(
        "Cartera vencida",
        f"{overdue / open_ar.balance.sum() * 100:.1f}%" if open_ar.balance.sum() else "0,0%",
    )
    paid = ar[(ar.derived_status == "pagada") & ar.last_collection_date.notna()].copy()
    paid["collection_days"] = (
        pd.to_datetime(paid.last_collection_date) - paid.invoice_date
    ).dt.days
    cards[3].metric(
        "Días promedio de cobro", f"{paid.collection_days.mean():.1f}" if not paid.empty else "—"
    )
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
    st.plotly_chart(
        chart(
            monthly.tail(18), "line", "invoice_date", "revenue", "Evolución mensual de facturación"
        ),
        width="stretch",
    )
    st.subheader("Alertas automáticas")
    alerts = []
    if delta < -10:
        alerts.append(f"⚠️ La facturación comparable cae {abs(delta):.1f}%.")
    if open_ar.balance.sum() and overdue / open_ar.balance.sum() > 0.25:
        alerts.append("⚠️ Más del 25% de la cartera está vencida.")
    if not open_orders.empty:
        alerts.append(f"📦 Hay {open_orders.order_id.nunique()} pedidos pendientes de entrega.")
    for alert in alerts or ["✅ No se detectaron desvíos relevantes con las reglas actuales."]:
        st.info(alert)


def sales_page(sales: pd.DataFrame, start: date, end: date) -> None:
    header("Facturación y ventas", "Evolución, mix comercial y detalle descargable")
    frame = sales[sales.invoice_date.dt.date.between(start, end)]
    frame = select_values(frame, "customer_name", "Cliente")
    frame = select_values(frame, "product_family", "Familia de producto")
    frame = select_values(frame, "province", "Provincia")
    if frame.empty:
        st.warning("No hay ventas para los filtros seleccionados.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Facturación", money(frame.allocated_total.sum()))
    c2.metric("Unidades", number(frame.billed_quantity.sum()))
    c3.metric("Precio promedio", money(frame.net_amount.sum() / frame.quantity.sum()))
    daily = frame.groupby(frame.invoice_date.dt.date).allocated_total.sum().reset_index()
    family = frame.groupby("product_family").allocated_total.sum().sort_values().reset_index()
    customer = (
        frame.groupby("customer_name")
        .allocated_total.sum()
        .nlargest(12)
        .sort_values()
        .reset_index()
    )
    left, right = st.columns(2)
    left.plotly_chart(
        chart(daily, "line", "invoice_date", "allocated_total", "Facturación diaria"),
        width="stretch",
    )
    right.plotly_chart(
        chart(family, "bar", "allocated_total", "product_family", "Ventas por familia"),
        width="stretch",
    )
    st.plotly_chart(
        chart(customer, "bar", "allocated_total", "customer_name", "Principales clientes"),
        width="stretch",
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    csv_download(frame, "ventas_envaplast.csv")


def orders_page(orders: pd.DataFrame, start: date, end: date) -> None:
    header("Pedidos", "Backlog, cumplimiento y desempeño de entregas")
    frame = orders[orders.order_date.dt.date.between(start, end)]
    frame = select_values(frame, "status", "Estado del pedido")
    open_frame = frame[~frame.status.isin(["entregado", "cancelado"])]
    delivered = frame[frame.delivery_date.notna()].copy()
    delivered["lead_days"] = (delivered.delivery_date - delivered.order_date).dt.days
    delivered["on_time"] = delivered.delivery_date <= delivered.promised_date
    cols = st.columns(4)
    cols[0].metric("Pedidos", number(frame.order_id.nunique()))
    cols[1].metric("Importe ingresado", money(frame.order_amount.sum()))
    cols[2].metric("Pendientes", number(open_frame.order_id.nunique()))
    cols[3].metric(
        "Cumplimiento prometido",
        f"{delivered.on_time.mean() * 100:.1f}%" if not delivered.empty else "—",
    )
    left, right = st.columns(2)
    status = frame.groupby("status").order_id.nunique().reset_index()
    left.plotly_chart(
        chart(status, "bar", "status", "order_id", "Pedidos por estado"), width="stretch"
    )
    trend = frame.groupby(frame.order_date.dt.date).order_id.nunique().reset_index()
    right.plotly_chart(
        chart(trend, "line", "order_date", "order_id", "Pedidos ingresados por día"),
        width="stretch",
    )
    delayed = frame[
        (frame.promised_date.dt.date < end) & ~frame.status.isin(["entregado", "cancelado"])
    ]
    st.subheader(f"Pedidos demorados ({len(delayed)})")
    st.dataframe(delayed, width="stretch", hide_index=True)
    csv_download(frame, "pedidos_envaplast.csv")


def ar_page(ar: pd.DataFrame, start: date, end: date) -> None:
    header("Cuentas corrientes", "Saldos, mora y concentración de riesgo")
    frame = ar[(ar.invoice_date.dt.date <= end) & (ar.balance > 0.01)]
    frame = select_values(frame, "derived_status", "Estado de factura")
    frame = select_values(frame, "customer_name", "Cliente")
    overdue = frame[frame.derived_status == "vencida"]
    customer = frame.groupby(
        ["customer_id", "customer_name", "credit_limit"], as_index=False
    ).balance.sum()
    cols = st.columns(4)
    cols[0].metric("Saldo pendiente", money(frame.balance.sum()))
    cols[1].metric("Saldo vencido", money(overdue.balance.sum()))
    cols[2].metric(
        "Mora promedio",
        f"{overdue.days_past_due.mean():.1f} días" if not overdue.empty else "0 días",
    )
    cols[3].metric("Sobre límite", number((customer.balance > customer.credit_limit).sum()))
    aging = (
        frame.groupby("aging_bucket")
        .balance.sum()
        .reindex(["No vencido", "1-30 días", "31-60 días", "61-90 días", ">90 días"], fill_value=0)
        .reset_index()
    )
    concentration = customer.nlargest(12, "balance").sort_values("balance")
    left, right = st.columns(2)
    left.plotly_chart(
        chart(aging, "bar", "aging_bucket", "balance", "Antigüedad de saldos"),
        width="stretch",
    )
    right.plotly_chart(
        chart(concentration, "bar", "balance", "customer_name", "Concentración por cliente"),
        width="stretch",
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    csv_download(frame, "cuentas_corrientes_envaplast.csv")


def abc_page(abc: pd.DataFrame, sales: pd.DataFrame, start: date, end: date) -> None:
    header("Clientes y análisis ABC", "Concentración de facturación móvil de 12 meses")
    category = st.sidebar.multiselect("Categoría ABC", ["A", "B", "C"])
    frame = abc[abc.abc.isin(category)] if category else abc
    cols = st.columns(4)
    for idx, cat in enumerate(["A", "B", "C"]):
        cols[idx].metric(f"Clientes {cat}", number((abc.abc == cat).sum()))
    cols[3].metric("Top 10 / ventas", f"{abc.head(10).share.sum() * 100:.1f}%")
    plot = frame.head(30).copy()
    fig = px.bar(
        plot,
        x="customer_name",
        y="revenue",
        color="abc",
        color_discrete_map={"A": COLORS[0], "B": COLORS[1], "C": COLORS[2]},
        title="Facturación y categoría por cliente",
    )
    st.plotly_chart(fig, width="stretch")
    selected = st.selectbox("Explorar cliente", abc.customer_name.tolist())
    history = (
        sales[sales.customer_name == selected]
        .groupby(sales.invoice_date.dt.to_period("M"))
        .net_amount.sum()
        .reset_index()
    )
    history["invoice_date"] = history.invoice_date.astype(str)
    st.plotly_chart(
        chart(history, "line", "invoice_date", "net_amount", f"Evolución de {selected}"),
        width="stretch",
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    csv_download(frame, "clientes_abc_envaplast.csv")


def main() -> None:
    setup_page()
    bootstrap()
    st.sidebar.title("Envaplast Analytics")
    st.sidebar.caption("Inteligencia comercial y financiera")
    page = st.sidebar.radio(
        "Navegación",
        [
            "Resumen ejecutivo",
            "Facturación y ventas",
            "Pedidos",
            "Cuentas corrientes",
            "Clientes y ABC",
        ],
    )
    minimum, maximum = available_date_range(engine)
    start, end = date_filter(minimum, maximum)
    st.sidebar.markdown("---")
    st.sidebar.info(
        "Todos los datos son sintéticos y no representan empresas ni operaciones reales."
    )
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
