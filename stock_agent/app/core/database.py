from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from stock_agent.app.core.config import Settings


def engine_from_url(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def sessionmaker_for_url(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=engine_from_url(database_url), autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    session_factory = sessionmaker_for_url(Settings().database_url)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
