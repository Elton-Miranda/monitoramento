import requests
import json

# 1. Coloque sua URL aqui
URL = "https://telecom.hermeticshell.org/api/primarias"

# 2. Coloque seu Token/Header aqui exatamente como está no secrets.toml
# Exemplo se for um Bearer Token:
HEADERS = {
    "X-API-Key": "ewU1lO1Do2BGj5VNpwczJ30CT_f59qtzPlQtP9v0m6c",
    "Content-Type": "application/json"
}

print("Baixando dados da API...")
resposta = requests.get(URL, headers=HEADERS)

if resposta.status_code == 200:
    dados = resposta.json()
    
    # Salva o resultado no arquivo que o nosso painel vai ler!
    with open("historico_sigma.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)
        
    print("✅ Sucesso! Arquivo historico_sigma.json gerado na pasta.")
else:
    print(f"❌ Erro {resposta.status_code}: {resposta.text}")