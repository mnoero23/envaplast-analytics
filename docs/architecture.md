# Decisión de arquitectura

## Opciones evaluadas

| Criterio | Streamlit + SQLAlchemy | Next.js + FastAPI |
|---|---|---|
| Despliegue económico | Excelente | Bueno, pero requiere dos servicios |
| URL pública | Directa con Community Cloud | Requiere coordinar frontend y API |
| Calidad visual | Alta para un dashboard | Muy alta |
| Mantenimiento individual | Bajo | Medio/alto |
| Secretos | Integración nativa | Variables en dos entornos |
| Automatización | Python y Actions directos | Similar, con más superficie |
| Portfolio de Analytics | Muy alto | Alto, más orientado a software |
| Extensibilidad | Suficiente para el roadmap | Superior a costa de complejidad |

## Decisión

El MVP usa **Streamlit + Plotly + SQLAlchemy 2**. Hace visible el trabajo analítico, comparte Python entre generación, calidad y aplicación, y se despliega con poco mantenimiento. React/FastAPI sería razonable si el producto necesitara autenticación compleja, una API pública o UX altamente personalizada; ninguna es necesaria en esta etapa.

SQLite ofrece ejecución local sin cuentas. `DATABASE_URL` permite sustituirlo por PostgreSQL/Supabase sin cambiar la capa analítica. GitHub Actions automatiza cargas persistentes únicamente contra la base remota.

## Flujo

1. El generador deriva una semilla por fecha y crea operaciones en una transacción.
2. SQLAlchemy aplica el mismo modelo en SQLite o PostgreSQL.
3. Los servicios producen datasets reconciliados.
4. Streamlit cachea lecturas determinísticas y presenta cinco vistas.
5. El workflow ejecuta generación, controles y tests; los secretos permanecen en GitHub.

