import bcrypt
from sqlalchemy import select

from persistence.database import get_session
from persistence.models import User


def atualizar_senha(email, senha_antiga, senha_nova):
    from . import valida_senha

    senha = valida_senha(senha_nova)
    with get_session() as session:
        stmt = select(User).where(User.email == email)
        user = session.execute(stmt).scalar_one_or_none()

        if user:
            if bcrypt.checkpw(
                senha_antiga.encode("utf-8"),
                user.password.encode("utf-8"),
            ):
                new_hashed = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
                user.password = new_hashed.decode("utf-8")
                session.commit()
            else:
                raise ValueError("Senha incorreta")
