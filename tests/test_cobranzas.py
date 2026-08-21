import pandas as pd

from src.cobranzas import collection_message, prioritize_receivables


def sample_receivables() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "invoice_id": 1,
                "customer_id": 10,
                "customer_name": "Cliente crítico",
                "balance": 800_000,
                "credit_limit": 500_000,
                "days_past_due": 120,
                "derived_status": "vencida",
            },
            {
                "invoice_id": 2,
                "customer_id": 20,
                "customer_name": "Cliente preventivo",
                "balance": 100_000,
                "credit_limit": 1_000_000,
                "days_past_due": 0,
                "derived_status": "pendiente",
            },
        ]
    )


def test_prioritize_receivables_puts_highest_risk_first():
    queue = prioritize_receivables(sample_receivables())

    assert queue.customer_name.tolist() == ["Cliente crítico", "Cliente preventivo"]
    assert queue.iloc[0].priority == "Crítica"
    assert queue.iloc[0].priority_score > queue.iloc[1].priority_score
    assert "120 días" in queue.iloc[0].explanation
    assert queue.priority_score.between(0, 100).all()


def test_prioritize_receivables_returns_defined_empty_shape():
    empty = sample_receivables().assign(balance=0)

    assert prioritize_receivables(empty).empty
    assert "priority_score" in prioritize_receivables(empty).columns


def test_collection_message_keeps_human_reviewable_context():
    message = collection_message("Cliente crítico", 800_000, 120)

    assert "Cliente crítico" in message
    assert "$800.000" in message
    assert "120 días" in message
    assert "fecha prevista de pago" in message
