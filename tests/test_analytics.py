from datetime import date

from sqlalchemy.orm import Session

from src.analytics import customer_abc, orders_detail, receivables, sales_detail
from src.generator import generate_day, seed_master_data


def test_analytics_frames_are_render_ready(test_engine):
    with Session(test_engine) as session, session.begin():
        seed_master_data(session, 777)
        generate_day(session, date(2026, 1, 15), 777, date(2026, 7, 1))
    assert not sales_detail(test_engine).empty
    assert not orders_detail(test_engine).empty
    assert "balance" in receivables(test_engine, date(2026, 7, 1))
    abc = customer_abc(test_engine, date(2026, 7, 1))
    assert set(abc.abc).issubset({"A", "B", "C"})
