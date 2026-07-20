from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "app.py"
PAGES = [
    "Resumen ejecutivo",
    "Facturación y ventas",
    "Pedidos",
    "Cuentas corrientes",
    "Clientes y ABC",
]

app = AppTest.from_file(str(APP), default_timeout=120).run()
results: dict[str, dict[str, int]] = {}
for page in PAGES:
    app.sidebar.radio[0].set_value(page).run()
    if app.exception:
        messages = [exception.message for exception in app.exception]
        raise RuntimeError(f"Fallo al renderizar {page}: {messages}")
    results[page] = {
        "metrics": len(app.metric),
        "dataframes": len(app.dataframe),
        "downloads": len(app.get("download_button")),
    }

if not results["Resumen ejecutivo"]["metrics"]:
    raise RuntimeError("El resumen no renderizó tarjetas KPI")
if not any(value["dataframes"] for value in results.values()):
    raise RuntimeError("No se renderizó ninguna tabla de detalle")
print(results)

