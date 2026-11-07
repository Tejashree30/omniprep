from celery import Celery
from .config import REDIS_URL
from .db import init_db

# Without Redis (local dev) tasks run eagerly in-process so the app still works.
celery_app = Celery("omniprep", broker=REDIS_URL or "memory://", backend=REDIS_URL or "cache+memory://")
celery_app.conf.task_always_eager = not REDIS_URL

@celery_app.task(name="ingest")
def ingest_task(source_id: str):
    init_db()
    from .ingest import ingest_source
    ingest_source(source_id)
