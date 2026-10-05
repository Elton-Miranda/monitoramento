import bcrypt
from sqlalchemy import select

from persistence.database import get_session
from persistence.models import User


def _check_password(email, passwd) -> User:
    with get_session() as session:
        stmt = select(User).where(User.email == email)
        user = session.execute(stmt).scalar_one_or_none()

        if user and bcrypt.checkpw(
            passwd.encode("utf-8"), user.password.encode("utf-8")
        ):
            return user

        raise ValueError("Email ou senha inválidos")


def logar_usuario(email, senha) -> User:
    user = _check_password(email, senha)
    if not user.approved:
        raise ValueError("Usuário pendente de aprovação")

    return user


def obter_usuario_por_email(email) -> User:
    with get_session() as session:
        user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user:
            raise ValueError("Usuário não encontrado")

        return user
