# Use a imagem base do Ubuntu mais recente
FROM python:3.10.12


# Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

COPY /app /app

# Defina as variáveis de ambiente do proxy como argumentos de build
ARG HTTP_PROXY
ARG HTTPS_PROXY

# Configurar variáveis de ambiente para o proxy
ENV http_proxy=$HTTP_PROXY
ENV https_proxy=$HTTPS_PROXY


# Instale as dependências Python especificadas no requirements.txt usando o proxy
RUN pip3 install --proxy=$HTTP_PROXY -r requirements.txt

# Exponha a porta
EXPOSE 5000

# Comando padrão para executar a aplicação quando o contêiner for iniciado
CMD ["python3", "./run.py"]
