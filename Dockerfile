# Base com Python e FFmpeg
FROM python:3.11-slim

# Instala ffmpeg e certificados (para SSL) e curl (healthcheck)
RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
  && update-ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copia arquivos do app
COPY . /app

# Instala dependências
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

# Exposição da porta
EXPOSE 5000

# Variáveis de ambiente
ENV FLASK_ENV=production \
    HOST=0.0.0.0 \
    PORT=5000

# Healthcheck simples (usa /healthz)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD curl -fsS http://127.0.0.1:${PORT}/healthz || exit 1

# Comando de inicialização (Gunicorn para produção) com expansão de PORT
CMD ["sh", "-c", "gunicorn downloader:app --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120"]
