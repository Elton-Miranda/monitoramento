from database import Log, Session


def salvar_log_no_sqlite(message):
    record = message.record
    with Session() as db:
        try:
            novo_log = Log(
                level=record["level"].name,
                message=record["message"]
            )
            db.add(novo_log)
            db.commit()
        except Exception:
            db.rollback()
            raise
