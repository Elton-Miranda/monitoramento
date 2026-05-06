import bcrypt
from datetime import datetime
from sqlalchemy import ForeignKey, create_engine, func, event, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

engine = create_engine('sqlite:///user.db')
Session = sessionmaker(bind=engine, expire_on_commit=False, autocommit=False, autoflush=False)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    pass


class Contract(Base):
    __tablename__ = 'contracts'
    id_contract: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)

    users: Mapped[list['User']] = relationship(back_populates='contract_rel')


class User(Base):
    __tablename__ = 'users'
    id_user: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    approved: Mapped[bool] = mapped_column(nullable=False, default=False)
    contract: Mapped[str] = mapped_column(
        ForeignKey('contracts.id_contract'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(nullable=False, default='user')

    contract_rel: Mapped['Contract'] = relationship(back_populates='users')




if __name__ == '__main__':
    Base.metadata.create_all(engine)
    with Session(bind=engine) as session:
        try:
            contratos = [Contract(name=x) for x in ["ABILITY_SJ", "TEL_JI", "ABILITY_OS",
                        "TEL_INTERIOR", "TEL_PC_SC", "TELEMONT"]]
            session.add_all(contratos)
            session.commit()
        except IntegrityError:
            session.rollback()
            pass

        try:
            user = User(
                name='admin',
                approved=True,
                contract='ABILITY_SJ',
                email='admin',
                password=bcrypt.hashpw('@sigmaops*ykd8b5'.encode(), bcrypt.gensalt()).decode('utf-8'),
                role='admin'
            )
            session.add(user)
            session.commit()
        except IntegrityError:
            session.rollback()
            pass

