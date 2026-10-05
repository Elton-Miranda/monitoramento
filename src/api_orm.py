import polars as pl
from sqlalchemy import select

from persistence.database import get_session
from persistence.models import (
    TelaOcorrencia as oc,
)


def get_ocorrencias():
    with get_session() as session:
        stmt = select(
            oc.ocorrencia.label("Ocorrência"),
            oc.data_abertura.label("Abertura"),
            oc.contrato.label("Contrato"),
            oc.cnl.label("CNL"),
            oc.at.label("AT"),
            oc.afetacao.label("Afetação"),
            oc.vip.label("VIP"),
            oc.cond_alto_valor.label("Cond. Alto Valor"),
            oc.b2b_avancado.label("B2B"),
            oc.tecnicos.label("Técnicos"),
            oc.origem.label("Origem"),
            oc.cabo.label("Cabo"),
            oc.primarias.label("Primárias"),
            oc.bd.label("BD"),
            oc.propenso_anatel.label("Propensos - Anatel"),
            oc.reclamado_anatel.label("Reclamados - Anatel"),
            oc.reincidencia.label("Reincidência"),
        )

        result = session.execute(
            stmt.order_by(oc.ocorrencia.desc()).limit(1000)
        ).fetchall()

        df = pl.DataFrame(result)

        format_reinc_pl = (
            pl.col("Reincidência")
            .cast(pl.Float64, strict=False)
            .cast(pl.Int64, strict=False)
            .cast(pl.String)
            .fill_null("")
        )

        df = df.with_columns(format_reinc_pl).with_columns(
            pl.col("Abertura").alias("Abertura_dt")
        )

        return df


result = get_ocorrencias()
print(result)

# if "Técnicos" in df_api.columns:
#     df_api["Técnicos"] = df_api["Técnicos"].apply(
#         lambda x: len(x) if isinstance(x, list) else 0
#     )

# if "Afetação" in df_api.columns:
#     df_api["Afetação"] = (
#         pd.to_numeric(df_api["Afetação"], errors="coerce").fillna(0).astype(int)
#     )

# def formatar_flag(val):
#     if pd.isna(val):
#         return "NÃO"
#     s = str(val).upper().strip()
#     if s in ["TRUE", "SIM", "S", "YES"]:
#         return "SIM"
#     try:
#         return "SIM" if float(val) > 0 else "NÃO"
#     except:
#         return "NÃO"

# for col in ["VIP", "Cond. Alto Valor", "B2B"]:
#     if col in df_api.columns:
#         df_api[col] = df_api[col].apply(formatar_flag)
