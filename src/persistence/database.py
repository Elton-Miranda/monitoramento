from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core import settings

engine = create_engine(settings.database_url, echo=False)
engine2 = create_engine(settings.DBURL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
SessionLocal2 = sessionmaker(bind=engine2, expire_on_commit=False)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_session_legacy():
    session = SessionLocal2()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
