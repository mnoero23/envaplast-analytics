-- Esquema ejecutable de referencia. La creación portable se realiza desde SQLAlchemy.
-- Consulte src/models.py para restricciones compatibles con SQLite y PostgreSQL.
CREATE INDEX IF NOT EXISTS ix_orders_customer_date ON orders(customer_id, order_date);
CREATE INDEX IF NOT EXISTS ix_invoices_customer_date ON invoices(customer_id, invoice_date);
CREATE INDEX IF NOT EXISTS ix_collections_invoice ON collections(invoice_id);

