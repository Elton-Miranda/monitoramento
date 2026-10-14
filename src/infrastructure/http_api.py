#!/usr/bin/env pytho

from datetime import datetime

import requests as rq
from loguru import logger


def oc_vencida(start: str, end: str, limit: int = 8) -> dict[str, float | bool]:
    d_start = datetime.fromisoformat(start)
    d_end = datetime.fromisoformat(end)
    duration = d_end - d_start
    total_hour = duration.total_seconds() / 3600
    expired = total_hour > limit
    return {"duration": round(total_hour, 2), "expired": expired}


def load_dminusOne(contrato_ofensor: str, url: str = ""):
    try:
        if not url:
            raise ValueError("Invalid url")

        logger.debug(f'contrato usado na busca {contrato_ofensor}')

        response = rq.get(url, params={"contrato": contrato_ofensor}).json()
        count = len(response)
        reincidencia = sum([1 if x["reincidencia"] else 0 for x in response])
        prazo = sum(
            [
                1
                if not oc_vencida(
                    x["data_ocorrencia"],
                    x["data_ocorrencia_final"],
                    8 if not x["b2b_avancado"] else 4,
                )["expired"]
                else 0
                for x in response
            ]
        )
        return {
            "ocorrencias": count,
            "prazo": prazo,
            "reincidencia": reincidencia,
        }
    except Exception as e:
        logger.error(e)
        raise


if __name__ == "__main__":
    print(load_dminusOne("ABILITY_SJ", "http://localhost:8888/util/dminusone"))
