#!/usr/bin/env pytho

import requests as rq
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def load_dminusOne(contrato_ofensor: str, url: str):
    from util import oc_vencida

    try:
        response = rq.get(url, params={"contrato": contrato_ofensor})
        count = len(response.json())
        reincidencia = sum([1 if x["reincidencia"] else 0 for x in response.json()])
        prazo = sum(
            [
                1
                if not oc_vencida(x["data_ocorrencia"], x["data_ocorrencia_final"])[
                    "expired"
                ]
                else 0
                for x in response.json()
            ]
        )
        return {"ocorrencias": count, "prazo": prazo, "reincidencia": reincidencia}
    except Exception as e:
        logger.error(e)


def obter_ocorrencias_filtradas(contrato, afetacao, municipio, status, at):
    pass
