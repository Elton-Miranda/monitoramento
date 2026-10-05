from time import sleep

from sqlalchemy import select

from coord import buscar_coordenadas
from persistence.database import get_session_legacy
from persistence.models.entities import OcorrenciaTxt

while True:
    sleep(2)
    with get_session_legacy() as session:
        # stmt = select(oc.logradouro).where(oc.id_ocorrencia == 1110912)
        query = (
            select(OcorrenciaTxt)
            .where(
                OcorrenciaTxt.logradouro != "Endereço não localizado.",
                OcorrenciaTxt.contratada == "ABILITY_SJ",
                OcorrenciaTxt.lat_lon.is_(None),
            )
            .order_by(
                OcorrenciaTxt.id_ocorrencia.asc()
            )  # Ordena do menor ID para o maior
            .limit(1)  # Pega apenas o primeiro
        )

        # Executa e extrai o primeiro resultado
        ocorrencia = session.execute(query).scalar_one()

        if ocorrencia:
            logradouro = ocorrencia.logradouro
            municipio = ocorrencia.municipio

            result = buscar_coordenadas(f"{logradouro}, {municipio}")

            if result:
                lat = result["latitude"]
                lon = result["longitude"]
                injest = f"{lat},{lon}"
                ocorrencia.lat_lon = injest
                print(f"{logradouro},{municipio}")
                print(injest)
            else:
                ocorrencia.lat_lon = "not found"
        else:
            print("terminou")
            break
