# Despliegue previsto

## Supabase

1. Crear un proyecto gratuito y copiar la cadena PostgreSQL con SSL.
2. Ejecutar localmente `DATABASE_URL=... python scripts/init_db.py --months 18`.
3. Verificar con `python scripts/validate_data.py`.
4. Guardar `DATABASE_URL` y `ENVAPLAST_SEED` en GitHub Actions Secrets.
5. Ejecutar manualmente el workflow y luego dejar activo el cron.

## Streamlit Community Cloud

1. Publicar la rama `main` en GitHub solo después de revisar que no contiene secretos.
2. En `share.streamlit.io`, crear una app desde el repositorio y apuntar a `app/app.py`.
3. Elegir Python 3.12. Streamlit instalará las dependencias desde `requirements.txt`.
4. Para una demo inmediata con SQLite, dejar Secrets vacío.
5. Para una versión persistente, definir en Secrets las claves raíz `DATABASE_URL` y `ENVAPLAST_SEED`.
6. Confirmar que Supabase permite la conexión de red y usa SSL.

Ejemplo de Secrets para la versión persistente, reemplazando el valor por la cadena entregada por Supabase:

```toml
DATABASE_URL = "postgresql+psycopg://usuario:contraseña@host:puerto/postgres?sslmode=require"
ENVAPLAST_SEED = "20260720"
ENVAPLAST_ENV = "production"
```

Nunca guardar ese contenido en el repositorio. `.streamlit/secrets.toml` está excluido mediante `.gitignore`.

Sin `DATABASE_URL`, la aplicación crea SQLite efímera de demostración. Esa base puede reiniciarse cuando el contenedor duerme y no sirve para actualización persistente.

Los planes gratuitos pueden suspender servicios inactivos, limitar cómputo/conexiones y cambiar condiciones. Antes de publicar, revisar límites vigentes de ambos proveedores. Para restablecer datos sintéticos, vaciar un esquema dedicado y volver a ejecutar `init_db.py`; no hacerlo sobre una base compartida.
