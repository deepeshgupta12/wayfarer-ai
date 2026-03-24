from app.clients.redis_client import check_redis_connection
from app.db.session import check_database_connection


def get_infra_status() -> dict[str, bool]:
    database_ok = check_database_connection()
    redis_ok = check_redis_connection()

    return {
        "database": database_ok,
        "redis": redis_ok,
    }