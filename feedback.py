from loguru import logger
from database import Feedback, Session


def salvar_feedback(tipo: str, descricao: str, contato: str | None) -> None:

    feedback = Feedback(
        tipo=tipo,
        descricao=descricao,
        contato=contato,
    )
    try:
        with Session() as session:
            session.add(feedback)
            session.commit()
    except Exception as e:
        logger.error(f"Erro ao salvar feedback: {e}")
        raise