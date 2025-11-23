#!/bin/bash
set -e

echo "Inicializando banco de dados..."
python3 init_db.py

# Verifica o ambiente e inicia o servidor apropriado
if [ "$FLASK_ENV" = "production" ]; then
    echo "Iniciando aplicação em modo PRODUÇÃO com Gunicorn..."
    exec gunicorn -c gunicorn.conf.py "src:app"
else
    echo "Iniciando aplicação em modo DESENVOLVIMENTO com Flask..."
    exec python3 run.py
fi
