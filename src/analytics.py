from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database import engine as default_engine
from src.metrics import abc_classification, aging_bucket


def read_frame(
    query: str, target_engine: Engine = default_engine, params: dict | None = None
) -> pd.DataFrame:
    with target_engine.connect() as connection:
        return pd.read_sql(text(query), connection, params=params or {})


def sales_detail(target_engine: Engine = default_engine) -> pd.DataFrame:
    frame = read_frame(
        """
        SELECT i.invoice_id, i.invoice_date, i.due_date, i.invoice_number, i.invoice_status,
               i.subtotal, i.tax_amount, i.total_amount, c.customer_id, c.customer_name,
               c.segment, c.province, c.region, o.order_id, o.sales_channel,
               p.product_id, p.sku, p.product_name, p.product_family,
               oi.quantity, oi.unit_price, oi.discount_percentage, oi.net_amount,
               i.total_amount * oi.net_amount /
                 SUM(oi.net_amount) OVER (PARTITION BY i.invoice_id) AS allocated_total,
               oi.quantity * i.subtotal /
                 SUM(oi.net_amount) OVER (PARTITION BY i.invoice_id) AS billed_quantity
        FROM invoices i JOIN customers c ON c.customer_id=i.customer_id
        JOIN orders o ON o.order_id=i.order_id JOIN order_items oi ON oi.order_id=o.order_id
        JOIN products p ON p.product_id=oi.product_id
    """,
        target_engine,
    )
    for column in ["invoice_date", "due_date"]:
        frame[column] = pd.to_datetime(frame[column])
    return frame


def orders_detail(target_engine: Engine = default_engine) -> pd.DataFrame:
    frame = read_frame(
        """
        SELECT o.order_id, o.order_date, o.promised_date, o.status, o.sales_channel,
               c.customer_id, c.customer_name, c.province, c.region,
               COALESCE(SUM(oi.net_amount),0) order_amount, COALESCE(SUM(oi.quantity),0) units,
               d.delivery_date, d.delivery_status, d.delivered_percentage
        FROM orders o JOIN customers c ON c.customer_id=o.customer_id
        JOIN order_items oi ON oi.order_id=o.order_id
        LEFT JOIN deliveries d ON d.order_id=o.order_id
        GROUP BY o.order_id, o.order_date, o.promised_date, o.status, o.sales_channel,
                 c.customer_id, c.customer_name, c.province, c.region,
                 d.delivery_date, d.delivery_status, d.delivered_percentage
    """,
        target_engine,
    )
    for column in ["order_date", "promised_date", "delivery_date"]:
        frame[column] = pd.to_datetime(frame[column])
    return frame


def receivables(target_engine: Engine = default_engine, as_of: date | None = None) -> pd.DataFrame:
    as_of = as_of or date.today()
    frame = read_frame(
        """
        SELECT i.invoice_id, i.invoice_number, i.invoice_date, i.due_date, i.total_amount,
               c.customer_id, c.customer_name, c.segment, c.credit_limit, c.province, c.region,
               COALESCE(SUM(col.amount),0) collected_amount,
               MAX(col.collection_date) last_collection_date
        FROM invoices i JOIN customers c ON c.customer_id=i.customer_id
        LEFT JOIN collections col ON col.invoice_id=i.invoice_id
        GROUP BY i.invoice_id, i.invoice_number, i.invoice_date, i.due_date, i.total_amount,
                 c.customer_id, c.customer_name, c.segment, c.credit_limit, c.province, c.region
    """,
        target_engine,
    )
    if frame.empty:
        for column in [
            "balance",
            "days_past_due",
            "aging_bucket",
            "derived_status",
        ]:
            frame[column] = pd.Series(dtype="object")
        return frame
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"])
    frame["due_date"] = pd.to_datetime(frame["due_date"])
    frame["balance"] = frame["total_amount"] - frame["collected_amount"]
    frame["days_past_due"] = frame["due_date"].dt.date.map(lambda due: max(0, (as_of - due).days))
    frame["aging_bucket"] = frame["due_date"].dt.date.map(lambda due: aging_bucket(due, as_of))
    frame["derived_status"] = frame.apply(
        lambda row: (
            "pagada"
            if row.balance <= 0.01
            else "parcialmente pagada"
            if row.collected_amount > 0
            else "vencida"
            if row.due_date.date() < as_of
            else "pendiente"
        ),
        axis=1,
    )
    return frame


def customer_abc(target_engine: Engine = default_engine, as_of: date | None = None) -> pd.DataFrame:
    as_of = as_of or date.today()
    start = as_of - timedelta(days=365)
    frame = read_frame(
        """
        SELECT c.customer_id, c.customer_name, c.segment, c.province, c.region,
               COALESCE(SUM(i.total_amount),0) revenue
        FROM customers c LEFT JOIN invoices i ON i.customer_id=c.customer_id
          AND i.invoice_date BETWEEN :start AND :end
        GROUP BY c.customer_id, c.customer_name, c.segment, c.province, c.region
    """,
        target_engine,
        {"start": start, "end": as_of},
    )
    return abc_classification(frame)


def available_date_range(target_engine: Engine = default_engine) -> tuple[date, date]:
    frame = read_frame(
        "SELECT MIN(order_date) min_date, MAX(order_date) max_date FROM orders", target_engine
    )
    if frame.empty or frame.iloc[0]["min_date"] is None:
        today = date.today()
        return today - timedelta(days=365), today
    return pd.to_datetime(frame.iloc[0]["min_date"]).date(), pd.to_datetime(
        frame.iloc[0]["max_date"]
    ).date()
