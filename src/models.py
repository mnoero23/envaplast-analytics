from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

MONEY = Numeric(16, 2)
PERCENT = Numeric(5, 2)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("credit_limit >= 0", name="ck_customer_credit_nonnegative"),
        CheckConstraint("payment_terms_days IN (0, 15, 30, 45, 60)", name="ck_payment_terms"),
        Index("ix_customer_region_segment", "region", "segment"),
    )
    customer_id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(120), unique=True)
    tax_id: Mapped[str] = mapped_column(String(13), unique=True)
    segment: Mapped[str] = mapped_column(String(30))
    province: Mapped[str] = mapped_column(String(40))
    region: Mapped[str] = mapped_column(String(30))
    credit_limit: Mapped[Decimal] = mapped_column(MONEY)
    payment_terms_days: Mapped[int]
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("current_price > 0 AND estimated_unit_cost > 0", name="ck_product_prices"),
        CheckConstraint("estimated_unit_cost <= current_price", name="ck_product_margin"),
        Index("ix_product_family", "product_family"),
    )
    product_id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(20), unique=True)
    product_name: Mapped[str] = mapped_column(String(120))
    product_family: Mapped[str] = mapped_column(String(50))
    unit_of_measure: Mapped[str] = mapped_column(String(15))
    current_price: Mapped[Decimal] = mapped_column(MONEY)
    estimated_unit_cost: Mapped[Decimal] = mapped_column(MONEY)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("promised_date >= order_date", name="ck_order_promised_date"),
        CheckConstraint(
            "status IN ('ingresado','en preparación','listo para despacho','entregado','cancelado')",
            name="ck_order_status",
        ),
        UniqueConstraint("source_key", name="uq_order_source_key"),
        Index("ix_order_date_status", "order_date", "status"),
    )
    order_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    order_date: Mapped[date] = mapped_column(Date)
    promised_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30))
    sales_channel: Mapped[str] = mapped_column(String(30))
    source_key: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    customer: Mapped[Customer] = relationship()
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_item_quantity"),
        CheckConstraint("unit_price > 0 AND net_amount >= 0", name="ck_item_amounts"),
        CheckConstraint("discount_percentage BETWEEN 0 AND 100", name="ck_item_discount"),
    )
    order_item_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(MONEY)
    discount_percentage: Mapped[Decimal] = mapped_column(PERCENT)
    net_amount: Mapped[Decimal] = mapped_column(MONEY)
    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint(
            "delivery_status IN ('programada','parcial','completa','demorada')",
            name="ck_delivery_status",
        ),
        CheckConstraint("delivered_percentage BETWEEN 0 AND 100", name="ck_delivery_pct"),
        UniqueConstraint("order_id", name="uq_delivery_order"),
    )
    delivery_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"))
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(20))
    delivered_percentage: Mapped[Decimal] = mapped_column(PERCENT)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("due_date >= invoice_date", name="ck_invoice_due_date"),
        CheckConstraint(
            "subtotal >= 0 AND tax_amount >= 0 AND total_amount >= 0", name="ck_invoice_amounts"
        ),
        CheckConstraint(
            "invoice_status IN ('pendiente','parcialmente pagada','pagada','vencida')",
            name="ck_invoice_status",
        ),
        UniqueConstraint("order_id", name="uq_invoice_order"),
        Index("ix_invoice_due_status", "due_date", "invoice_status"),
    )
    invoice_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    invoice_number: Mapped[str] = mapped_column(String(30), unique=True)
    invoice_status: Mapped[str] = mapped_column(String(25))
    subtotal: Mapped[Decimal] = mapped_column(MONEY)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY)
    total_amount: Mapped[Decimal] = mapped_column(MONEY)


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_collection_amount"),
        UniqueConstraint("reference", name="uq_collection_reference"),
        Index("ix_collection_date", "collection_date"),
    )
    collection_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.invoice_id"))
    collection_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    payment_method: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str] = mapped_column(String(50))


class CalendarDay(Base):
    __tablename__ = "calendar"
    calendar_date: Mapped[date] = mapped_column(Date, primary_key=True)
    year: Mapped[int]
    month: Mapped[int]
    month_name: Mapped[str] = mapped_column(String(15))
    day: Mapped[int]
    weekday: Mapped[int]
    is_weekend: Mapped[bool]


class GenerationRun(Base):
    __tablename__ = "generation_runs"
    run_id: Mapped[int] = mapped_column(primary_key=True)
    business_date: Mapped[date] = mapped_column(Date, unique=True)
    seed: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    rows_created: Mapped[str] = mapped_column(String(500), default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
