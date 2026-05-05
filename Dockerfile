FROM ghcr.io/astral-sh/uv:latest AS uv_bin

FROM python:3.13-slim

WORKDIR /app

# Copia os binários do uv
COPY --from=uv_bin /uv /uvx /bin/

# Impede o uv de criar links físicos (melhor compatibilidade com Docker)
ENV UV_LINK_MODE=copy
# Evita que o uv crie um ambiente virtual dentro do container, instalando no sistema
ENV UV_SYSTEM_PYTHON=1

# 1. Copia apenas os arquivos de definição de pacotes
COPY pyproject.toml uv.lock ./

# 2. Instala as dependências (sem o código do app ainda)
# O --frozen garante que o uv não tente atualizar o lockfile
RUN uv sync --frozen --no-install-project --no-dev

# 3. Agora copia o restante dos arquivos (incluindo database.db)
COPY . .

EXPOSE 8501

# Executa o Streamlit usando o contexto do uv
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
