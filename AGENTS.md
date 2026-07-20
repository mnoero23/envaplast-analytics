# Guía para agentes

## Estructura

- `app/`: entrada y componentes Streamlit.
- `src/`: configuración, ORM, generación, métricas, consultas y calidad.
- `scripts/`: inicialización, actualización y validación.
- `tests/`: pruebas unitarias e integración.
- `docs/`: decisiones, definiciones y operación.

## Comandos

`python -m pip install -e ".[dev]"`, `python scripts/init_db.py`, `streamlit run app/app.py`, `pytest`, `ruff check .`, `ruff format --check .` y `python scripts/validate_data.py`.

## Reglas

- Python 3.12, type hints, Ruff y funciones pequeñas.
- Importes en `Decimal`/`NUMERIC(16,2)`; nunca persistir dinero como texto o float.
- Preservar claves, restricciones, secuencia pedido→entrega→factura→cobranza y precios históricos.
- Toda generación por fecha debe continuar siendo determinística, transaccional e idempotente.
- No incluir secretos, datos reales ni identificadores de entidades existentes.
- Antes de terminar: tests, lint, calidad, repetición idempotente y smoke test de Streamlit.

