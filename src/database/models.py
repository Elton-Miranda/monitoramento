from contextlib import contextmanager
from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DBURL = getenv("DBURL", "")

print(DBURL)

engine = create_engine(DBURL)


@contextmanager
def get_session():
    with engine.begin() as session:
        yield session
        print('fechando sessão')
        session.close()


if __name__ == "__main__":
    with get_session() as conn:
        stmt = text("SELECT * FROM hashes")
        result = conn.execute(stmt).mappings().all()
        print(result)
