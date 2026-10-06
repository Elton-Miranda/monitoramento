from datetime import datetime

from sqlalchemy import select

from persistence.database import get_session
from persistence.models.entities import OcorrenciaTxt as oc


def filter(
    id: int | None = None,
    contratada: str | None = None,
    afetacao: int | None = None,
    at: str | None = None,
    municipio: str | None = None,
    data_hora_limite_inferior: datetime | None = None,
    data_hora_limite_superior: datetime | None = None,
):
    stmt = select(
        oc.id_ocorrencia,
        oc.municipio,
        oc.afetacao,
        oc.at,
        oc.contratada,
        oc.data_ocorrencia_final,
    ).where(oc.at == "SJ")
    if id:
        stmt = stmt.where(oc.id_ocorrencia == id)
    if contratada:
        stmt = stmt.where(oc.contratada == contratada)
    if afetacao:
        stmt = stmt.where(oc.afetacao >= afetacao)
    if at:
        stmt = stmt.where(oc.at == at)
    if municipio:
        stmt = stmt.where(oc.municipio == municipio)
    if data_hora_limite_inferior:
        stmt = stmt.where(oc.data_ocorrencia_final >= data_hora_limite_inferior)
    if data_hora_limite_superior:
        stmt = stmt.where(oc.data_ocorrencia_final <= data_hora_limite_superior)
    with get_session() as session:
        result = session.execute(stmt).mappings().all()
        payload = []

        for item in result:
            process = {**item}
            process["data_ocorrencia_final"] = process[
                "data_ocorrencia_final"
            ].strftime("%d/%m/%Y %H:%M:%S")
            payload.append(process)

        return payload
