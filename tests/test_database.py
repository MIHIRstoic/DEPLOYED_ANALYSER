from sqlalchemy.orm import Session, DeclarativeMeta
from sqlalchemy.engine import Engine

from app.core.database import engine, SessionLocal, Base, get_db


def test_database_components():
    assert isinstance(engine, Engine)
    assert callable(SessionLocal)
    assert isinstance(Base, DeclarativeMeta)


def test_get_db_generator():
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)
    try:
        next(db_gen)
    except StopIteration:
        pass
