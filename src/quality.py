from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.database import engine as default_engine
from src.models import Collection, Delivery, GenerationRun, Invoice, Order, OrderItem


@dataclass
class CheckResult:
    name: str
    passed: bool
    failures: int
    detail: str


def run_quality_checks(target_engine: Engine = default_engine) -> list[CheckResult]:
    checks: list[CheckResult] = []
    with Session(target_engine) as session:
        orphan_items = (
            session.scalar(
                select(func.count())
                .select_from(OrderItem)
                .outerjoin(Order)
                .where(Order.order_id.is_(None))
            )
            or 0
        )
        checks.append(
            CheckResult("FK ítems-pedidos", orphan_items == 0, orphan_items, "Ítems sin pedido")
        )
        bad_dates = (
            session.scalar(
                select(func.count())
                .select_from(Delivery)
                .join(Order)
                .where(Delivery.delivery_date < Order.order_date)
            )
            or 0
        )
        checks.append(
            CheckResult(
                "Secuencia de entregas", bad_dates == 0, bad_dates, "Entregas anteriores al pedido"
            )
        )
        bad_invoice = (
            session.scalar(
                select(func.count())
                .select_from(Invoice)
                .where(
                    func.abs(Invoice.total_amount - Invoice.subtotal - Invoice.tax_amount) > 0.01
                )
            )
            or 0
        )
        checks.append(
            CheckResult(
                "Reconciliación de facturas",
                bad_invoice == 0,
                bad_invoice,
                "Subtotal + IVA != total",
            )
        )
        overpaid_invoices = (
            select(Invoice.invoice_id)
            .outerjoin(Collection)
            .group_by(Invoice.invoice_id)
            .having(func.coalesce(func.sum(Collection.amount), 0) > Invoice.total_amount + 0.01)
            .subquery()
        )
        overpaid = session.scalar(select(func.count()).select_from(overpaid_invoices)) or 0
        checks.append(
            CheckResult(
                "Cobranzas dentro del saldo", overpaid == 0, overpaid, "Facturas sobrecobradas"
            )
        )
        negatives = (
            session.scalar(
                select(func.count()).select_from(OrderItem).where(OrderItem.net_amount < 0)
            )
            or 0
        )
        checks.append(
            CheckResult("Importes no negativos", negatives == 0, negatives, "Ítems negativos")
        )
        incomplete = (
            session.scalar(
                select(func.count()).select_from(Invoice).where(Invoice.invoice_number.is_(None))
            )
            or 0
        )
        checks.append(
            CheckResult("Completitud crítica", incomplete == 0, incomplete, "Facturas sin número")
        )
        duplicate_days = (
            session.scalar(
                select(func.count()).select_from(
                    select(GenerationRun.business_date)
                    .group_by(GenerationRun.business_date)
                    .having(func.count() > 1)
                    .subquery()
                )
            )
            or 0
        )
        checks.append(
            CheckResult(
                "Idempotencia por fecha", duplicate_days == 0, duplicate_days, "Fechas duplicadas"
            )
        )
        future_orders = (
            session.scalar(
                select(func.count()).select_from(Order).where(Order.order_date > date.today())
            )
            or 0
        )
        checks.append(
            CheckResult("Fechas no futuras", future_orders == 0, future_orders, "Pedidos futuros")
        )
    return checks


def quality_report(target_engine: Engine = default_engine) -> dict:
    results = run_quality_checks(target_engine)
    return {
        "passed": all(item.passed for item in results),
        "checks": [asdict(item) for item in results],
    }
