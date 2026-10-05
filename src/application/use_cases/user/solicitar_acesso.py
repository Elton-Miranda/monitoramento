import bcrypt
from sqlalchemy import select

from persistence.database import get_session
from persistence.models import User


def cadastrar_novo_usuario(nome, email, contrato, senha):
    from . import valida_senha

    senha = valida_senha(senha)

    if not nome or nome == "":
        raise ValueError("Preencha o nome corretamentes")

    if len(nome) < 3:
        raise ValueError("Nome deve ter no mínimo 3 caracteres")

    if not email or email == "" or len(email) <= 3 or "@" not in email:
        raise ValueError("Email inválido")

    if not contrato or contrato == "":
        raise ValueError("Contrato inválido")

    with get_session() as session:
        stmt = select(User.email).where(User.email == email)
        if session.execute(stmt).scalar_one_or_none() is None:
            user = User(
                name=nome,
                email=email,
                contract=contrato,
                password=bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode(
                    "utf-8"
                ),
            )
            session.add(user)
            session.commit()
        else:
            raise ValueError("Email já cadastrado.")
