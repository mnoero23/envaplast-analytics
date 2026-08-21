from __future__ import annotations

import pandas as pd


SCORE_WEIGHTS = {
    "saldo_vencido": 35,
    "mora": 25,
    "uso_credito": 20,
    "concentracion": 20,
}


def _pesos(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.div(denominator.replace(0, pd.NA))
    return result.fillna(0).clip(lower=0)


def _priority_label(score: float) -> str:
    if score >= 70:
        return "Crítica"
    if score >= 45:
        return "Alta"
    return "Seguimiento"


def _recommended_action(score: float, days_past_due: int) -> str:
    if score >= 70 or days_past_due > 90:
        return "Contactar hoy y acordar una fecha concreta de pago."
    if score >= 45 or days_past_due > 30:
        return "Contactar dentro de 48 horas y solicitar confirmación de pago."
    return "Enviar recordatorio preventivo y revisar nuevamente en 7 días."


def _explanation(row: pd.Series) -> str:
    factors: list[str] = []
    if row.overdue_balance > 0:
        factors.append(f"{_pesos(row.overdue_balance)} vencidos")
    if row.max_days_past_due > 0:
        factors.append(f"mora máxima de {int(row.max_days_past_due)} días")
    if row.credit_utilization >= 1:
        factors.append(f"uso del {row.credit_utilization:.0%} del límite de crédito")
    if row.portfolio_share >= 0.1:
        factors.append(f"{row.portfolio_share:.1%} de la cartera total")
    return "; ".join(factors[:3]) or "Saldo abierto sin factores críticos adicionales"


def prioritize_receivables(receivables: pd.DataFrame) -> pd.DataFrame:
    """Create an explainable customer-level collections queue from invoice balances."""
    open_items = receivables[receivables.balance > 0.01].copy()
    if open_items.empty:
        return pd.DataFrame(
            columns=[
                "customer_id",
                "customer_name",
                "balance",
                "overdue_balance",
                "max_days_past_due",
                "credit_limit",
                "credit_utilization",
                "portfolio_share",
                "priority_score",
                "priority",
                "explanation",
                "recommended_action",
            ]
        )

    open_items["overdue_component"] = open_items.balance.where(
        open_items.derived_status == "vencida", 0
    )
    queue = (
        open_items.groupby(["customer_id", "customer_name"], as_index=False)
        .agg(
            balance=("balance", "sum"),
            overdue_balance=("overdue_component", "sum"),
            max_days_past_due=("days_past_due", "max"),
            credit_limit=("credit_limit", "max"),
            open_invoices=("invoice_id", "nunique"),
        )
        .sort_values("balance", ascending=False)
    )

    total_balance = queue.balance.sum()
    max_overdue = max(queue.overdue_balance.max(), 1)
    queue["credit_utilization"] = _safe_ratio(queue.balance, queue.credit_limit)
    queue["portfolio_share"] = queue.balance / total_balance if total_balance else 0
    queue["priority_score"] = (
        (queue.overdue_balance / max_overdue).clip(upper=1) * SCORE_WEIGHTS["saldo_vencido"]
        + (queue.max_days_past_due / 90).clip(upper=1) * SCORE_WEIGHTS["mora"]
        + (queue.credit_utilization / 1.5).clip(upper=1) * SCORE_WEIGHTS["uso_credito"]
        + (queue.portfolio_share / max(queue.portfolio_share.max(), 0.01)).clip(upper=1)
        * SCORE_WEIGHTS["concentracion"]
    ).round(1)
    queue["priority"] = queue.priority_score.map(_priority_label)
    queue["explanation"] = queue.apply(_explanation, axis=1)
    queue["recommended_action"] = queue.apply(
        lambda row: _recommended_action(row.priority_score, int(row.max_days_past_due)), axis=1
    )
    return queue.sort_values(
        ["priority_score", "overdue_balance", "balance"], ascending=False
    ).reset_index(drop=True)


def collection_message(customer_name: str, balance: float, days_past_due: int) -> str:
    timing = (
        f"La obligación más antigua registra {days_past_due} días de mora. "
        if days_past_due > 0
        else "El vencimiento se encuentra próximo. "
    )
    return (
        f"Hola, equipo de {customer_name}:\n\n"
        f"Nos contactamos por el saldo pendiente de {_pesos(balance)}. {timing}"
        "¿Podrían confirmarnos la fecha prevista de pago o indicarnos si necesitan "
        "que reenviemos la documentación?\n\n"
        "Muchas gracias. Quedamos atentos."
    )
