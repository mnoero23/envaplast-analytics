# Diccionario de datos

| Tabla | Grano | Campos principales |
|---|---|---|
| `customers` | Cliente ficticio | nombre, CUIT ficticio, segmento, geografía, límite, plazo |
| `products` | SKU | familia, unidad, precio vigente, costo estimado |
| `orders` | Pedido | cliente, fechas, estado, canal, clave de origen |
| `order_items` | Producto por pedido | cantidad, precio histórico, descuento, neto |
| `deliveries` | Entrega por pedido | fecha, estado, porcentaje entregado |
| `invoices` | Factura por pedido | fechas, número ficticio, subtotal, IVA, total, estado |
| `collections` | Cobranza | factura, fecha, importe, medio, referencia ficticia |
| `calendar` | Día | año, mes, día, semana y fin de semana |
| `generation_runs` | Fecha procesada | semilla, estado, conteos y timestamps |

Los IDs son enteros internos. Importes usan `NUMERIC(16,2)`, porcentajes `NUMERIC(5,2)` y fechas de negocio usan `DATE`.

