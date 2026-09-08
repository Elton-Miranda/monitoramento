# --- Estágio 1: Build & Instalação de Dependências ---
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Força o uv a compilar os arquivos de bytecode para um startup mais rápido
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copia apenas os arquivos de definição de pacotes
COPY pyproject.toml uv.lock ./

# Instala as dependências criando uma .venv isolada (sem pacotes de desenvolvimento)
RUN uv sync --frozen --no-install-project --no-dev

# --- Estágio 2: Imagem Final de Produção (Super Leve) ---
FROM python:3.13-slim AS runner

WORKDIR /app

# Copia o ambiente virtual inteiro gerado pelo uv
COPY --from=builder /app/.venv /app/.venv

# MÁGICA AQUI: Adiciona os binários da .venv ao PATH do sistema final
ENV PATH="/app/.venv/bin:$PATH"

# Copia o código fonte do seu app Streamlit
COPY . .

EXPOSE 8501

# Agora o sistema encontra o 'streamlit' nativamente no PATH
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
