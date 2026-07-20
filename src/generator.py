from __future__ import annotations

import hashlib
import json
import random
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.config import settings
from src.database import engine as default_engine
from src.models import (
    Base,
    CalendarDay,
    Collection,
    Customer,
    Delivery,
    GenerationRun,
    Invoice,
    Order,
    OrderItem,
    Product,
)

CENT = Decimal("0.01")
MONTHS_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
PROVINCES = [
    ("Buenos Aires", "Pampeana", 35),
    ("Córdoba", "Centro", 14),
    ("Santa Fe", "Centro", 14),
    ("Mendoza", "Cuyo", 7),
    ("Tucumán", "NOA", 6),
    ("Salta", "NOA", 5),
    ("Neuquén", "Patagonia", 5),
    ("Entre Ríos", "Litoral", 6),
    ("Chaco", "NEA", 4),
    ("Río Negro", "Patagonia", 4),
]
PRODUCTS = [
    ("BOT-500", "Botella PET 500 ml", "Botellas PET", "unidad", 185, 112),
    ("BOT-1000", "Botella PET 1 litro", "Botellas PET", "unidad", 260, 158),
    ("BOT-2000", "Botella PET 2 litros", "Botellas PET", "unidad", 395, 242),
    ("FRS-250", "Frasco cosmético 250 ml", "Frascos", "unidad", 310, 190),
    ("FRS-500", "Frasco alimenticio 500 ml", "Frascos", "unidad", 365, 221),
    ("BID-5", "Bidón industrial 5 litros", "Bidones", "unidad", 1280, 790),
    ("BID-10", "Bidón apilable 10 litros", "Bidones", "unidad", 2180, 1360),
    ("TAP-28", "Tapa rosca 28 mm", "Tapas y cierres", "unidad", 42, 24),
    ("TAP-45", "Tapa inviolable 45 mm", "Tapas y cierres", "unidad", 68, 39),
    ("GAT-500", "Gatillo pulverizador", "Tapas y cierres", "unidad", 285, 174),
    ("BAL-10", "Balde plástico 10 litros", "Baldes", "unidad", 1890, 1170),
    ("BAL-20", "Balde plástico 20 litros", "Baldes", "unidad", 2980, 1840),
]


def money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def date_seed(day: date, base_seed: int) -> int:
    digest = hashlib.sha256(f"{base_seed}:{day.isoformat()}".encode()).hexdigest()
    return int(digest[:12], 16) % 2_147_483_647


def fictitious_cuit(number: int) -> str:
    body = f"307{number:07d}"[:10]
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    remainder = 11 - sum(int(n) * w for n, w in zip(body, weights, strict=True)) % 11
    check = 0 if remainder == 11 else 9 if remainder == 10 else remainder
    return f"{body[:2]}-{body[2:10]}-{check}"


def create_schema(target_engine: Engine = default_engine) -> None:
    Base.metadata.create_all(target_engine)
    migration = Base.metadata.tables["orders"].indexes
    _ = migration  # keeps schema creation explicit and portable


def seed_master_data(session: Session, base_seed: int = settings.seed) -> dict[str, int]:
    counts = {"customers": 0, "products": 0}
    if not session.scalar(select(func.count()).select_from(Customer)):
        rng = random.Random(base_seed)
        prefixes = [
            "Distribuidora",
            "Comercial",
            "Industrias",
            "Abastecedora",
            "Mayorista",
            "Soluciones",
        ]
        names = [
            "Aurora",
            "Calandria",
            "Del Plata",
            "Faro Sur",
            "Horizonte",
            "Litoral",
            "Malva",
            "Puelche",
            "Quebracho",
            "Trébol",
        ]
        suffixes = ["Envases", "Integral", "Regional", "Pack", "Mercantil"]
        province_names = [p[0] for p in PROVINCES]
        weights = [p[2] for p in PROVINCES]
        for i in range(1, 61):
            province = rng.choices(province_names, weights=weights, k=1)[0]
            region = next(p[1] for p in PROVINCES if p[0] == province)
            segment = "Grande" if i <= 8 else "Mediano" if i <= 28 else "Pequeño"
            terms = rng.choice([30, 45, 60]) if segment == "Grande" else rng.choice([15, 30, 45])
            limit = {"Grande": 45_000_000, "Mediano": 14_000_000, "Pequeño": 4_000_000}[segment]
            session.add(
                Customer(
                    customer_name=f"{rng.choice(prefixes)} {rng.choice(names)} {rng.choice(suffixes)} {i:02d} S.A.",
                    tax_id=fictitious_cuit(8_000_000 + i),
                    segment=segment,
                    province=province,
                    region=region,
                    credit_limit=money(limit * rng.uniform(0.7, 1.3)),
                    payment_terms_days=terms,
                    active=True,
                )
            )
        counts["customers"] = 60
    if not session.scalar(select(func.count()).select_from(Product)):
        for sku, name, family, unit, price, cost in PRODUCTS:
            session.add(
                Product(
                    sku=sku,
                    product_name=name,
                    product_family=family,
                    unit_of_measure=unit,
                    current_price=money(price),
                    estimated_unit_cost=money(cost),
                    active=True,
                )
            )
        counts["products"] = len(PRODUCTS)
    session.flush()
    return counts


def ensure_calendar(session: Session, start: date, end: date) -> int:
    existing = set(
        session.scalars(
            select(CalendarDay.calendar_date).where(CalendarDay.calendar_date.between(start, end))
        )
    )
    created = 0
    cursor = start
    while cursor <= end:
        if cursor not in existing:
            session.add(
                CalendarDay(
                    calendar_date=cursor,
                    year=cursor.year,
                    month=cursor.month,
                    month_name=MONTHS_ES[cursor.month - 1],
                    day=cursor.day,
                    weekday=cursor.weekday(),
                    is_weekend=cursor.weekday() >= 5,
                )
            )
            created += 1
        cursor += timedelta(days=1)
    return created


def _weighted_customer(rng: random.Random, customers: list[Customer]) -> Customer:
    weights = [
        10 if c.segment == "Grande" else 3.5 if c.segment == "Mediano" else 1 for c in customers
    ]
    return rng.choices(customers, weights=weights, k=1)[0]


def _order_volume(rng: random.Random, customer: Customer) -> int:
    base = {"Grande": 1600, "Mediano": 700, "Pequeño": 260}[customer.segment]
    return max(24, int(rng.lognormvariate(0, 0.55) * base))


def generate_day(
    session: Session, business_date: date, base_seed: int = settings.seed, as_of: date | None = None
) -> dict[str, int]:
    existing = session.scalar(
        select(GenerationRun).where(GenerationRun.business_date == business_date)
    )
    if existing:
        return {"skipped": 1}
    as_of = as_of or business_date
    seed = date_seed(business_date, base_seed)
    run = GenerationRun(business_date=business_date, seed=seed, status="running")
    session.add(run)
    session.flush()
    rng = random.Random(seed)
    counts = {"orders": 0, "order_items": 0, "deliveries": 0, "invoices": 0, "collections": 0}
    customers = list(session.scalars(select(Customer).where(Customer.active.is_(True))))
    products = list(session.scalars(select(Product).where(Product.active.is_(True))))
    weekend_factor = 0.14 if business_date.weekday() >= 5 else 1.0
    season = {
        1: 0.78,
        2: 0.82,
        3: 1.0,
        4: 0.96,
        5: 1.03,
        6: 1.0,
        7: 0.92,
        8: 1.02,
        9: 1.08,
        10: 1.16,
        11: 1.28,
        12: 1.36,
    }[business_date.month]
    trend = 1 + max(0, (business_date - date(2024, 1, 1)).days) / 365 * 0.055
    order_count = max(0, round(rng.gauss(8.2 * weekend_factor * season * trend, 2.0)))
    for sequence in range(order_count):
        customer = _weighted_customer(rng, customers)
        promised = business_date + timedelta(days=rng.randint(3, 10))
        cancelled = rng.random() < 0.025
        delivery_delay = rng.choices([-1, 0, 1, 2, 4, 7], weights=[8, 35, 25, 15, 10, 7], k=1)[0]
        delivery_date = max(business_date, promised + timedelta(days=delivery_delay))
        partial = not cancelled and rng.random() < 0.09
        if cancelled:
            status = "cancelado"
        elif delivery_date <= as_of and not partial:
            status = "entregado"
        elif promised <= as_of:
            status = "listo para despacho"
        elif business_date < as_of:
            status = "en preparación"
        else:
            status = "ingresado"
        order = Order(
            customer_id=customer.customer_id,
            order_date=business_date,
            promised_date=promised,
            status=status,
            sales_channel=rng.choice(
                ["Ejecutivo comercial", "WhatsApp B2B", "Portal mayorista", "Teléfono"]
            ),
            source_key=f"{business_date:%Y%m%d}-{sequence:03d}",
        )
        session.add(order)
        session.flush()
        counts["orders"] += 1
        subtotal = Decimal("0")
        for product in rng.sample(products, k=rng.randint(1, min(4, len(products)))):
            quantity = _order_volume(rng, customer)
            inflation = Decimal(
                str(
                    (1.0065) ** max(0, ((business_date.year - 2025) * 12 + business_date.month - 1))
                )
            )
            unit_price = money(
                product.current_price * inflation * Decimal(str(rng.uniform(0.96, 1.05)))
            )
            discount = Decimal(
                str(
                    rng.choice(
                        [0, 0, 2, 3, 5, 7, 10]
                        if customer.segment != "Grande"
                        else [5, 7, 8, 10, 12]
                    )
                )
            )
            net = money(Decimal(quantity) * unit_price * (Decimal("1") - discount / 100))
            session.add(
                OrderItem(
                    order_id=order.order_id,
                    product_id=product.product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount_percentage=money(discount),
                    net_amount=net,
                )
            )
            subtotal += net
            counts["order_items"] += 1
        if not cancelled:
            visible_delivery_date = delivery_date if delivery_date <= as_of else None
            delivered_pct = (
                Decimal("65")
                if partial
                else Decimal("100")
                if visible_delivery_date
                else Decimal("0")
            )
            delivery_status = (
                "parcial"
                if partial
                else "demorada"
                if not visible_delivery_date and promised < as_of
                else "completa"
                if visible_delivery_date
                else "programada"
            )
            session.add(
                Delivery(
                    order_id=order.order_id,
                    delivery_date=visible_delivery_date,
                    delivery_status=delivery_status,
                    delivered_percentage=delivered_pct,
                )
            )
            counts["deliveries"] += 1
            if visible_delivery_date:
                invoice_subtotal = money(subtotal * delivered_pct / 100)
                tax = money(invoice_subtotal * Decimal("0.21"))
                total = invoice_subtotal + tax
                invoice = Invoice(
                    customer_id=customer.customer_id,
                    order_id=order.order_id,
                    invoice_date=visible_delivery_date,
                    due_date=visible_delivery_date + timedelta(days=customer.payment_terms_days),
                    invoice_number=f"FV-A-0001-{order.order_id:08d}",
                    invoice_status="pendiente",
                    subtotal=invoice_subtotal,
                    tax_amount=tax,
                    total_amount=total,
                )
                session.add(invoice)
                session.flush()
                counts["invoices"] += 1
                behavior = {"Grande": 8, "Mediano": 14, "Pequeño": 24}[customer.segment]
                late_days = max(-5, round(rng.gauss(behavior, 18)))
                pay_date = invoice.due_date + timedelta(days=late_days)
                if pay_date <= as_of:
                    partial_payment = rng.random() < 0.12
                    amount = money(total * (Decimal("0.55") if partial_payment else Decimal("1")))
                    session.add(
                        Collection(
                            customer_id=customer.customer_id,
                            invoice_id=invoice.invoice_id,
                            collection_date=pay_date,
                            amount=amount,
                            payment_method=rng.choice(
                                ["Transferencia", "E-cheq", "Cheque", "Depósito"]
                            ),
                            reference=f"COB-{invoice.invoice_id:08d}-01",
                        )
                    )
                    invoice.invoice_status = "parcialmente pagada" if partial_payment else "pagada"
                    counts["collections"] += 1
                elif invoice.due_date < as_of:
                    invoice.invoice_status = "vencida"
    run.status = "success"
    run.rows_created = json.dumps(counts, ensure_ascii=False)
    run.finished_at = datetime.utcnow()
    return counts


def initialize_history(
    target_engine: Engine = default_engine,
    end: date | None = None,
    months: int = 18,
    base_seed: int = settings.seed,
) -> dict[str, int]:
    end = end or date.today()
    start = end - timedelta(days=round(months * 30.44))
    totals: dict[str, int] = {}
    with Session(target_engine) as session, session.begin():
        seed_master_data(session, base_seed)
        ensure_calendar(session, start, end + timedelta(days=90))
    cursor = start
    while cursor <= end:
        with Session(target_engine) as session, session.begin():
            result = generate_day(session, cursor, base_seed, as_of=end)
            for key, value in result.items():
                totals[key] = totals.get(key, 0) + value
        cursor += timedelta(days=1)
    return totals


def generate_missing(
    target_engine: Engine = default_engine,
    through: date | None = None,
    base_seed: int = settings.seed,
) -> dict[str, int]:
    through = through or date.today()
    with Session(target_engine) as session:
        first = session.scalar(select(func.min(GenerationRun.business_date)))
    if first is None:
        return initialize_history(target_engine, through, 18, base_seed)
    totals: dict[str, int] = {}
    cursor = first
    while cursor <= through:
        with Session(target_engine) as session, session.begin():
            result = generate_day(session, cursor, base_seed, as_of=through)
            for key, value in result.items():
                totals[key] = totals.get(key, 0) + value
        cursor += timedelta(days=1)
    return totals
