import requests
from loguru import logger


def buscar_coordenadas(endereco):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": endereco,
        "format": "json",
        "limit": 1,
        "countrycodes": "br",
        "email": "seu-email-corporativo@provedor.com",
    }

    headers = {
        "User-Agent": "VisioServerMonitoramento/1.0 (Contato: seu-email-corporativo@provedor.com)",
        "Accept": "*/*",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            dados = response.json()
            if len(dados) > 0:
                local = dados[0]
                return {
                    "endereco_formatado": local.get("display_name"),
                    "latitude": local.get("lat"),
                    "longitude": local.get("lon"),
                }
            else:
                logger.debug(f"Nenhum resultado encontrado para: {endereco}")
                return None
        else:
            logger.debug(f"Erro na requisição. Status code: {response.status_code}")
            logger.debug(f"Detalhes do erro: {response.text}")
            return None

    except Exception as e:
        logger.debug(f"Ocorreu um erro na execução: {e}")
        raise


if __name__ == "__main__":
    endereco_teste = "RUA LICURGO SANTOS, 52, Aparecida - SP"
    resultado = buscar_coordenadas(endereco_teste)
    if resultado:
        logger.debug("\n=== Sucesso ===")
        logger.debug(f"Endereço: {resultado['endereco_formatado']}")
        logger.debug(
            f"Coordenadas: {resultado['latitude']}, {resultado['longitude']}\n"
        )
