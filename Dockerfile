FROM python:3.10-slim

# Evita o warning do pip
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_WARN_SCRIPT_LOCATION=1

WORKDIR /app

# Copia todos os arquivos
COPY . .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Dá permissão para o diretório
RUN chmod 777 /app

CMD ["python", "minhastarefinhasbot.py"]
