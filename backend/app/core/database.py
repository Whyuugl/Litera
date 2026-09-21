import os
from functools import lru_cache
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

load_dotenv()


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        raise RuntimeError("DATABASE_URL environment variable is required") from exc


@lru_cache
def get_engine() -> Engine:
    return create_engine(database_url())


def get_session() -> Iterator[Session]:
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
