"""
Configuração do Gunicorn para o DarfFlow API

Para iniciar a aplicação com Gunicorn:
    gunicorn -c gunicorn.conf.py "src:app"

Ou simplesmente:
    gunicorn "src:app"
(se este arquivo estiver no mesmo diretório)
"""

import os
import multiprocessing

# Endereço e porta de bind
bind = "0.0.0.0:5000"

# Número de workers
# Recomendação: (2 x núcleos de CPU) + 1
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Tipo de worker
# sync: workers síncronos (padrão, bom para aplicações I/O bound)
# gevent/eventlet: workers assíncronos (melhor para muitas conexões simultâneas)
worker_class = "sync"

# Timeout para requisições (em segundos)
timeout = 120

# Keep-alive connections (em segundos)
keepalive = 5

# Número máximo de requisições que um worker pode processar antes de ser reiniciado
# Ajuda a prevenir memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"  # Log para stdout
errorlog = "-"   # Erros para stdout
loglevel = "info"

# Graceful timeout - tempo para workers finalizarem requisições antes de serem forçadamente parados
graceful_timeout = 30

# Preload da aplicação
# True: carrega a aplicação antes de fazer fork dos workers (economiza RAM)
# False: cada worker carrega sua própria cópia (mais seguro se houver problemas com shared state)
preload_app = False
