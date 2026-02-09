import requests
import pandas as pd
import json

# Configurações
URL = "https://telecom.hermeticshell.org/api/view"
HEADERS = {
    "X-API-Key": "a6e41c2a5f544c1ca9dbf6e9bfc1e8e5",
    "Content-Type": "application/json"
}

print(f"📡 Conectando a {URL}...")

try:
    response = requests.get(URL, headers=HEADERS, timeout=15)
    
    if response.status_code == 200:
        print("✅ Sucesso! Dados recebidos.")
        data = response.json()
        
        if 'ocorrencias' in data:
            df = pd.DataFrame(data['ocorrencias'])
            
            print("\n" + "="*50)
            print("🔍 LISTA DE COLUNAS REAIS (Copie o nome exato)")
            print("="*50)
            for col in sorted(df.columns):
                print(f" -> {col}")
            
            print("\n" + "="*50)
            print("🧪 AMOSTRA DE VALORES (Para entender o formato)")
            print("="*50)
            
            # Procura colunas suspeitas
            suspeitas = [c for c in df.columns if any(x in c.lower() for x in ['vip', 'cond', 'alto', 'valor', 'b2b', 'imp', 'pri'])]
            
            if suspeitas:
                print(df[suspeitas].head(5).to_string())
            else:
                print("⚠️ Nenhuma coluna óbvia de VIP encontrada. Verifique a lista completa acima.")
                
        else:
            print("❌ O JSON não tem a chave 'ocorrencias'.")
            print("Chaves encontradas:", data.keys())
            
    else:
        print(f"❌ Erro na requisição: {response.status_code}")
        print("Resposta:", response.text)

except Exception as e:
    print(f"❌ Falha de conexão: {e}")
    print("Dica: Verifique se a VPN está ligada.")