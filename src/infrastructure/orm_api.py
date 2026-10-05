import polars as pl
from loguru import logger
from sqlalchemy import select

from persistence.database import get_session_legacy
from persistence.models import OcorrenciaPrimaria, Ocorrencias


def primary_search(primary: str, cab: str, pri: str, mun: str) -> pl.DataFrame:
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
                ).where(OcorrenciaPrimaria.cod_primaria.ilike(f"%{primary}%"))
                .join(
                    Ocorrencias,
                    OcorrenciaPrimaria.id_ocorrencia == Ocorrencias.id_ocorrencia,
                )
            )
            result = session.execute(stmt)
            # df = pl.DataFrame(result)
            df = pl.DataFrame(result.all(), schema=list(result.keys()))
            # logger.info(df)
            return df
    except Exception as e:
        logger.error(e)
        raise
