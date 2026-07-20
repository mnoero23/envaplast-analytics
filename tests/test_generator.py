from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.generator import generate_day, seed_master_data
from src.models import GenerationRun, Invoice, Order
from src.quality import run_quality_checks


def test_generator_is_idempotent(test_engine):
    target = date(2026, 1, 15)
    with Session(test_engine) as session, session.begin():
        seed_master_data(session, 42)
        first = generate_day(session, target, 42, date(2026, 7, 1))
    with Session(test_engine) as session, session.begin():
        second = generate_day(session, target, 42, date(2026, 7, 1))
    with Session(test_engine) as session:
        assert session.scalar(select(func.count()).select_from(GenerationRun)) == 1
        assert session.scalar(select(func.count()).select_from(Order)) == first["orders"]
    assert second == {"skipped": 1}


def test_invoice_components_and_integrity(test_engine):
    target = date(2026, 1, 15)
    with Session(test_engine) as session, session.begin():
        seed_master_data(session, 123)
        generate_day(session, target, 123, date(2026, 7, 1))
    with Session(test_engine) as session:
        invoices = list(session.scalars(select(Invoice)))
        assert invoices
        assert all(
            invoice.subtotal + invoice.tax_amount == invoice.total_amount for invoice in invoices
        )
    assert all(result.passed for result in run_quality_checks(test_engine))
