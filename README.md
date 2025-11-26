## Backend Docker Quickstart

1. Copy `env.example` to `.env` and adjust secrets (especially `SECRET_KEY` and DB creds).
2. Ensure the Django project module is `backend` (or change the `gunicorn` target/`DJANGO_SETTINGS_MODULE` accordingly).
3. Build and start the dev stack:
   ```
   docker compose up --build
   ```
4. Visit http://localhost:8000 for the dev server. Source code is bind-mounted, so changes hot-reload.
5. For a production image, remove the volume mount and rely on the default `CMD` (Gunicorn). Update settings to point to managed Postgres + persistent storage.

