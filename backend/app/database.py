from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"timeout": 30} if settings.database_url.startswith("sqlite") else {},
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.database_url.startswith("sqlite"):
            await ensure_sqlite_schema(conn)


async def ensure_sqlite_schema(conn):
    """Non-destructive SQLite schema patching for early deployments.

    This only adds missing columns. It never drops tables or data.
    """
    await ensure_columns(conn, "documents", {
        "department": "VARCHAR(100) DEFAULT ''",
        "project": "VARCHAR(200) DEFAULT ''",
        "is_information_system": "BOOLEAN DEFAULT 1",
        "applies_system_introduction_grading": "BOOLEAN DEFAULT 1",
        "is_critical_infrastructure": "BOOLEAN DEFAULT 1",
        "organization_category": "VARCHAR(50) DEFAULT '特定非公務機關'",
        "security_responsibility_level": "VARCHAR(1) DEFAULT 'A'",
        "confidentiality_level": "VARCHAR(1) DEFAULT '中'",
        "integrity_level": "VARCHAR(1) DEFAULT '中'",
        "availability_level": "VARCHAR(1) DEFAULT '中'",
        "legal_compliance_level": "VARCHAR(1) DEFAULT '中'",
        "protection_level": "VARCHAR(1) DEFAULT '中'",
        "system_importance": "VARCHAR(255) DEFAULT ''",
        "processes_personal_data": "BOOLEAN DEFAULT 0",
        "personal_data_description": "VARCHAR(500) DEFAULT ''",
    })


async def ensure_columns(conn, table_name: str, columns: dict[str, str]):
    result = await conn.exec_driver_sql(f"PRAGMA table_info({table_name})")
    existing = {row[1] for row in result.fetchall()}
    for column_name, column_type in columns.items():
        if column_name not in existing:
            await conn.exec_driver_sql(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )
