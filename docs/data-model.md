# Modelo de datos

```mermaid
erDiagram
  CUSTOMERS ||--o{ ORDERS : realiza
  ORDERS ||--|{ ORDER_ITEMS : contiene
  PRODUCTS ||--o{ ORDER_ITEMS : integra
  ORDERS ||--o| DELIVERIES : recibe
  ORDERS ||--o| INVOICES : factura
  CUSTOMERS ||--o{ INVOICES : adeuda
  INVOICES ||--o{ COLLECTIONS : cancela
  CUSTOMERS ||--o{ COLLECTIONS : paga
  GENERATION_RUNS }o--|| CALENDAR : fecha
```

El grano de `order_items` es producto por pedido; el de facturas es una factura por pedido entregado; cobranzas admite varios pagos por factura. `source_key` y `generation_runs.business_date` hacen idempotente la carga. Los estados se restringen con `CHECK`, y fechas, importes e integridad referencial se validan tanto en el esquema como después de cada proceso.

