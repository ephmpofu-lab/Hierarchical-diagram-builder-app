"""Single connection pool for the whole app, built from DATABASE_URL. Sync (not async) to
match every existing endpoint in backend/api.py, which are all plain `def` — FastAPI already
runs those in a thread pool, and psycopg_pool's ConnectionPool is thread-safe, so this fits
the app's existing concurrency model without also introducing async in the same change."""

import os

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to a local .env file "
                "(DATABASE_URL=postgresql://...) — see Supabase dashboard > Settings > Database."
            )
        _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, open=True)
    return _pool
