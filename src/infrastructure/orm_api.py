import polars as pl
from loguru import logger
from sqlalchemy import select

from persistence.database import get_session_legacy
from persistence.models import OcorrenciaPrimaria, Ocorrencias


def primary_search(
    cod_primaria: str,
    cabo: str,
    primaria: str,
    municipio: str,
    contrato: str | None = None,
) -> pl.DataFrame:
    try:
        with get_session_legacy() as session:
            stmt = (
                select(
                    OcorrenciaPrimaria.cod_primaria,
                    OcorrenciaPrimaria.id_ocorrencia,
                    Ocorrencias.afetacao,
                    Ocorrencias.data_ocorrencia,
                    Ocorrencias.data_ocorrencia_final,
                    Ocorrencias.municipio,
                    Ocorrencias.logradouro,
                    Ocorrencias.lat_lon,
                )
                .join(
                    Ocorrencias,
                    OcorrenciaPrimaria.id_ocorrencia == Ocorrencias.id_ocorrencia,
                )
                .limit(300)
                .order_by(Ocorrencias.id_ocorrencia.desc())
            )

            if contrato:
                stmt = stmt.where(Ocorrencias.contratada == contrato)

            if cod_primaria:
                stmt = stmt.where(
                    OcorrenciaPrimaria.cod_primaria.ilike(f"%{cod_primaria}%")
                )

            if cabo:
                logger.debug(f"filter cable {cabo}")
                stmt = stmt.where(OcorrenciaPrimaria.cod_primaria.contains(cabo))

            if primaria:
                stmt = stmt.where(OcorrenciaPrimaria.cod_primaria.contains(primaria))

            if municipio:
                stmt = stmt.where(Ocorrencias.municipio == municipio)

            result = session.execute(stmt)

            df = pl.DataFrame(result.all(), schema=list(result.keys()))
            return df
    except Exception as e:
        logger.error(e)
        raise
