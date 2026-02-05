import os
import sys
import time

# --- CORREÇÃO PARA PYTHON 3.13 ---
try:
    import distutils
except ImportError:
    import setuptools
    import types
    distutils = types.ModuleType("distutils")
    distutils.version = types.ModuleType("version")
    sys.modules["distutils"] = distutils
    sys.modules["distutils.version"] = distutils.version
    from setuptools._distutils.version import LooseVersion
    distutils.version.LooseVersion = LooseVersion
# ---------------------------------

import undetected_chromedriver as uc

# --- CONFIGURAÇÕES ---
URL_ALVO = "https://oltm.vivo.com.br/SigmaFibra/public/index"
PASTA_DESTINO = os.path.join(os.getcwd(), "dados")
ARQUIVO_FINAL_XLSX = "base_atualizada.xlsx"

# ==============================================================================
# ⚠️ IMPORTANTE: COLE AQUI O SEU SCRIPT JAVASCRIPT DO CONSOLE
# ==============================================================================
MEU_SCRIPT_JS = """
(async function() {
    console.log("🚀 Iniciando Download Excel...");
    const filtros = ["tel_ji", "ability_sj"]; 
    const esperar = (ms) => new Promise(r => setTimeout(r, ms));

    for (const filtro of filtros) {
        console.log("Filtro: " + filtro);
        const $inputBusca = $('input[type="search"]').first();
        if ($inputBusca.length) {
            $inputBusca.val(filtro).trigger('keyup');
        }
        await esperar(3000);

        const $btnExportar = $("button.dt-button.buttons-excel.buttons-html5");
        if ($btnExportar.length) {
            $btnExportar[0].click();
            console.log("⬇️ Clique realizado para: " + filtro);
            await esperar(5000); // Tempo para o download iniciar
        } else {
            console.warn("⚠️ Botão não encontrado para: " + filtro);
        }
        
        // Limpa busca
        if ($inputBusca.length) $inputBusca.val('').trigger('keyup');
        await esperar(2000);
    }
    return "Downloads Concluídos";
})();
"""
# ==============================================================================

def executar_robo():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)
    
    # Limpa arquivos temporários antigos
    for f in os.listdir(PASTA_DESTINO):
        if f.endswith(".crdownload") or f.endswith(".tmp"):
            try: os.remove(os.path.join(PASTA_DESTINO, f))
            except: pass

    options = uc.ChromeOptions()
    prefs = {
        "download.default_directory": PASTA_DESTINO,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    print("🚀 Abrindo navegador (Forçando v144)...")
    
    # --- CORREÇÃO AQUI: version_main=144 ---
    try:
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=144)
    except Exception as e:
        print(f"Erro ao iniciar driver v144, tentando automático... Erro: {e}")
        driver = uc.Chrome(options=options, use_subprocess=True)
        
    driver.maximize_window()

    try:
        print(f"🔗 Acessando: {URL_ALVO}")
        driver.get(URL_ALVO)

        print("🛑 AÇÃO MANUAL NECESSÁRIA: Faça o Login.")
        
        max_tentativas_login = 300
        contador = 0
        logado = False
        
        while contador < max_tentativas_login:
            try:
                url_atual = driver.current_url
                # Ajuste se necessário para detectar a URL pós-login
                if "ocorrencia/lista" in url_atual and "login" not in url_atual:
                    logado = True
                    print("🟢 Login detectado!")
                    break
            except: pass
            time.sleep(1)
            contador += 1
        
        if not logado:
            print("❌ Tempo esgotado esperando login.")
            return False

        print("⏳ Aguardando carregamento da tabela...")
        time.sleep(5) 

        print("💉 Injetando JS...")
        try:
            retorno = driver.execute_script(MEU_SCRIPT_JS)
            print(f"✅ Retorno: {retorno}")
        except Exception as e:
            print(f"❌ Erro JS: {e}")
            return False

        print("⏳ Aguardando downloads...")
        tempo = 0
        timeout = 180
        sucesso = False
        
        while tempo < timeout:
            arquivos = os.listdir(PASTA_DESTINO)
            # Procura qualquer Excel novo que não seja temporário
            arquivos_validos = [f for f in arquivos if (f.endswith('.xlsx') or f.endswith('.csv')) and not f.endswith('.crdownload')]
            
            if arquivos_validos:
                # Verifica se o arquivo é recente (modificado nos últimos 3 min)
                caminhos = [os.path.join(PASTA_DESTINO, f) for f in arquivos_validos]
                mais_recente = max(caminhos, key=os.path.getctime)
                
                if (time.time() - os.path.getctime(mais_recente)) < timeout:
                    time.sleep(2) # Espera acabar de escrever no disco
                    sucesso = True
                    break
            time.sleep(1)
            tempo += 1

        if sucesso:
            # Pega o arquivo mais recente
            caminhos = [os.path.join(PASTA_DESTINO, f) for f in os.listdir(PASTA_DESTINO) if (f.endswith('.xlsx') or f.endswith('.csv'))]
            mais_recente = max(caminhos, key=os.path.getctime)
            
            extensao = os.path.splitext(mais_recente)[1]
            nome_final = "base_atualizada" + extensao
            destino_final = os.path.join(PASTA_DESTINO, nome_final)
            
            # Substitui o antigo
            if os.path.exists(destino_final):
                try: os.remove(destino_final)
                except: pass
            
            # Se o arquivo baixado já tiver o nome certo, não faz nada, senão renomeia
            if mais_recente != destino_final:
                os.rename(mais_recente, destino_final)
                
            print(f"✅ Arquivo pronto: {destino_final}")
            return True
        else:
            print("❌ Falha: Nenhum arquivo novo encontrado.")
            return False

    except Exception as e:
        print(f"🔥 Erro durante execução: {e}")
        return False
    finally:
        try: driver.quit()
        except: pass

if __name__ == "__main__":
    executar_robo()