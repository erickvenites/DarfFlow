# Guia de Configuração e Deploy - DarfFlow

## Índice
- [Requisitos do Sistema](#requisitos-do-sistema)
- [Instalação com Docker](#instalação-com-docker)
- [Configuração de Variáveis de Ambiente](#configuração-de-variáveis-de-ambiente)
- [Inicialização do Banco de Dados](#inicialização-do-banco-de-dados)
- [Configuração de Certificados](#configuração-de-certificados)
- [Deploy em Produção](#deploy-em-produção)
- [Monitoramento e Logs](#monitoramento-e-logs)
- [Backup e Recuperação](#backup-e-recuperação)
- [Troubleshooting](#troubleshooting)

---

## Requisitos do Sistema

### Hardware Mínimo
- **CPU:** 2 cores
- **RAM:** 4 GB
- **Disco:** 50 GB (+ espaço para arquivos)
- **Rede:** Conexão estável com internet

### Hardware Recomendado (Produção)
- **CPU:** 4+ cores
- **RAM:** 8+ GB
- **Disco:** 100+ GB SSD (+ espaço para arquivos)
- **Rede:** Conexão dedicada com baixa latência

### Software
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **Git:** 2.30+
- **Sistema Operacional:** Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+) ou Windows com WSL2

---

## Instalação com Docker

### 1. Clonar o Repositório

```bash
git clone <repo-url>
cd DarfFlow
```

### 2. Verificar a Estrutura

```bash
ls -la
# Você deve ver: app/, docs/, docker-compose.yml, Dockerfile, .env.example
```

### 3. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env  # ou use seu editor preferido
```

Edite as seguintes variáveis:

```bash
# Ambiente da Aplicação
FLASK_ENV=development  # ou production

# Banco de Dados
POSTGRES_DB=efdreinf
POSTGRES_PASSWORD=sua_senha_segura_aqui

# URL de Conexão (ajuste a senha)
DEV_DATABASE_URL=postgresql://postgres:sua_senha_segura_aqui@postgres:5432/efdreinf

# Chave Secreta (gere uma nova!)
SECRET_KEY=sua_chave_secreta_muito_segura_aqui

# Endpoint EFD-Reinf
ENDPOINT_URL=https://endpoint.efdreinf.gov.br
```

#### Gerando uma SECRET_KEY segura:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Construir e Iniciar os Containers

```bash
# Build das imagens
docker-compose build

# Iniciar os serviços
docker-compose up -d

# Verificar logs
docker-compose logs -f
```

### 5. Verificar Status dos Containers

```bash
docker-compose ps
```

Você deve ver:
```
NAME                   STATUS              PORTS
darfflow-postgres-1    Up (healthy)        0.0.0.0:8001->5432/tcp
darfflow-flask-1       Up                  0.0.0.0:5000->5000/tcp
```

### 6. Testar a Aplicação

```bash
curl http://localhost:5000/
```

Se receber uma resposta, a aplicação está funcionando!

---

## Configuração de Variáveis de Ambiente

### Arquivo .env Completo

```bash
# ============================================
# CONFIGURAÇÕES DA APLICAÇÃO
# ============================================
FLASK_APP=run.py
FLASK_ENV=development  # development, production, ou testing

# ============================================
# BANCO DE DADOS
# ============================================
POSTGRES_DB=efdreinf
POSTGRES_PASSWORD=SuaSenhaSegura123!

# URL de conexão ao banco
# Formato: postgresql://usuario:senha@host:porta/database
DEV_DATABASE_URL=postgresql://postgres:SuaSenhaSegura123!@postgres:5432/efdreinf

# ============================================
# SEGURANÇA
# ============================================
# Gere com: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=sua_chave_secreta_de_64_caracteres_hexadecimais_aqui

# ============================================
# ENDPOINT EXTERNO (EFD-REINF)
# ============================================
ENDPOINT_URL=https://endpoint.efdreinf.gov.br

# ============================================
# PROXY (Opcional - para ambientes corporativos)
# ============================================
# HTTP_PROXY=http://proxy.empresa.com.br:8080
# HTTPS_PROXY=http://proxy.empresa.com.br:8080

# ============================================
# LOGS E DEBUG
# ============================================
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Variáveis por Ambiente

#### Development
```bash
FLASK_ENV=development
LOG_LEVEL=DEBUG
```

#### Production
```bash
FLASK_ENV=production
LOG_LEVEL=WARNING
# Adicione também:
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
```

#### Testing
```bash
FLASK_ENV=testing
POSTGRES_DB=efdreinf_test
DEV_DATABASE_URL=postgresql://postgres:senha@postgres:5432/efdreinf_test
```

---

## Inicialização do Banco de Dados

### Automática (Recomendado)

O banco de dados é inicializado automaticamente ao subir os containers graças ao script `init_db.py`.

**O que acontece automaticamente:**
1. Aguarda o PostgreSQL ficar disponível
2. Cria todas as tabelas necessárias
3. Aplica índices de otimização
4. Inicia a aplicação Flask

### Manual (Se necessário)

Se precisar reinicializar o banco manualmente:

```bash
# Conectar ao container Flask
docker exec -it darfflow-flask-1 bash

# Executar o script de inicialização
python3 init_db.py

# Sair do container
exit
```

### Usar Migrações Alembic

```bash
# Conectar ao container Flask
docker exec -it darfflow-flask-1 bash

# Navegar para o diretório da aplicação
cd /app

# Ver o estado das migrações
alembic current

# Aplicar todas as migrações
alembic upgrade head

# Criar uma nova migração (após alterar models)
alembic revision --autogenerate -m "Descrição da mudança"

# Sair
exit
```

### Verificar Tabelas Criadas

```bash
# Conectar ao PostgreSQL
docker exec -it darfflow-postgres-1 psql -U postgres -d efdreinf

# Listar tabelas
\dt

# Você deve ver:
# tb_planilhas
# tb_planilhas_convertidas
# tb_xmls_assinados
# tb_xmls_enviados
# tb_resposta_envio

# Ver estrutura de uma tabela
\d tb_planilhas

# Sair
\q
```

---

## Configuração de Certificados

### Certificado para Assinatura de XMLs

O sistema precisa de um certificado digital ICP-Brasil para assinar XMLs.

#### 1. Obter o Certificado

- Adquira um certificado digital A1 ou A3
- Certificado deve ser válido e emitido por autoridade certificadora ICP-Brasil
- Exporte no formato `.pem`

#### 2. Colocar no Servidor

```bash
# Criar diretório para certificados
mkdir -p app/docs

# Copiar certificado para o servidor
cp /caminho/do/certificado.pem app/docs/certificate.pem

# Definir permissões (importante!)
chmod 600 app/docs/certificate.pem
chown 1000:1000 app/docs/certificate.pem
```

#### 3. Configurar no Código

O caminho do certificado é definido em:
```
app/src/controllers/receiving_signed_xml_files_controller.py:168
```

```python
certificate_path = "docs/certificate.pem"
```

#### 4. Testar o Certificado

```bash
# Verificar informações do certificado
openssl x509 -in app/docs/certificate.pem -text -noout

# Verificar validade
openssl x509 -in app/docs/certificate.pem -noout -dates
```

### Certificado SSL/TLS (HTTPS)

Para produção, configure HTTPS usando um reverse proxy (Nginx ou Traefik).

---

## Deploy em Produção

### 1. Preparação do Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose-plugin

# Criar usuário para a aplicação
sudo useradd -m -s /bin/bash darfflow
sudo usermod -aG docker darfflow
```

### 2. Clonar e Configurar

```bash
# Como usuário darfflow
sudo su - darfflow

# Clonar repositório
git clone <repo-url> ~/darfflow
cd ~/darfflow

# Configurar variáveis de produção
cp .env.example .env
nano .env
# Configure todas as variáveis para produção
```

### 3. Ajustar docker-compose para Produção

Crie um arquivo `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:18
    restart: always
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backup_db:/backup_db
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - darfflow-network

  flask:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./app:/app
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - FLASK_APP=run.py
      - FLASK_ENV=production
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - DEV_DATABASE_URL=${DEV_DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ENDPOINT_URL=${ENDPOINT_URL}
    networks:
      - darfflow-network
    expose:
      - 5000

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - flask
    networks:
      - darfflow-network

volumes:
  postgres-data:

networks:
  darfflow-network:
    driver: bridge
```

### 4. Configurar Nginx

Crie `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream flask_app {
        server flask:5000;
    }

    server {
        listen 80;
        server_name seu-dominio.com.br;

        # Redirecionar para HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name seu-dominio.com.br;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        client_max_body_size 20M;

        location / {
            proxy_pass http://flask_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 5. Usar Gunicorn (Recomendado para Produção)

Edite `app/docker-entrypoint.sh`:

```bash
#!/bin/bash
set -e

echo "Inicializando banco de dados..."
python3 init_db.py

echo "Iniciando aplicação com Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 run:app
```

Adicione ao `requirements.txt`:
```
gunicorn==21.2.0
```

### 6. Iniciar em Produção

```bash
# Build e start
docker-compose -f docker-compose.prod.yml up -d --build

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f

# Verificar status
docker-compose -f docker-compose.prod.yml ps
```

### 7. Configurar Firewall

```bash
# Permitir apenas HTTPS e SSH
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Monitoramento e Logs

### Logs da Aplicação

```bash
# Ver logs em tempo real
docker-compose logs -f flask

# Ver últimas 100 linhas
docker-compose logs --tail=100 flask

# Logs do PostgreSQL
docker-compose logs postgres
```

### Logs do Sistema

Configure logs persistentes editando `app/src/config/logging_config.py`:

```python
import logging
from logging.handlers import RotatingFileHandler
import os

# Criar diretório de logs
os.makedirs('/app/logs', exist_ok=True)

# Configurar logger
logger = logging.getLogger('darfflow')
logger.setLevel(logging.INFO)

# Handler para arquivo
file_handler = RotatingFileHandler(
    '/app/logs/darfflow.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))

logger.addHandler(file_handler)
```

### Monitoramento com Prometheus (Opcional)

Adicione ao `requirements.txt`:
```
prometheus-client==0.19.0
```

Crie `app/src/middleware/metrics.py`:
```python
from prometheus_client import Counter, Histogram, generate_latest
from flask import Response

# Métricas
http_requests_total = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
http_request_duration = Histogram('http_request_duration_seconds', 'HTTP Request Duration')

def metrics_endpoint():
    return Response(generate_latest(), mimetype='text/plain')
```

---

## Backup e Recuperação

### Backup Automático do Banco de Dados

Crie um script `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup_db"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="efdreinf_backup_$DATE.sql"

# Criar backup
docker exec darfflow-postgres-1 pg_dump -U postgres efdreinf > "$BACKUP_DIR/$FILENAME"

# Comprimir
gzip "$BACKUP_DIR/$FILENAME"

# Manter apenas últimos 30 dias
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup criado: $FILENAME.gz"
```

Configure no cron:
```bash
# Editar crontab
crontab -e

# Adicionar backup diário às 2h da manhã
0 2 * * * /home/darfflow/darfflow/backup.sh >> /home/darfflow/darfflow/logs/backup.log 2>&1
```

### Backup dos Arquivos

```bash
#!/bin/bash
BACKUP_DIR="/backup_files"
DATE=$(date +%Y%m%d)
SOURCE="/home/darfflow/darfflow/app/data"

# Criar backup dos arquivos
tar -czf "$BACKUP_DIR/files_backup_$DATE.tar.gz" "$SOURCE"

# Manter apenas últimos 30 dias
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Restaurar Backup

```bash
# Restaurar banco de dados
gunzip < efdreinf_backup_20250121_020000.sql.gz | \
  docker exec -i darfflow-postgres-1 psql -U postgres efdreinf

# Restaurar arquivos
tar -xzf files_backup_20250121.tar.gz -C /home/darfflow/darfflow/app/
```

---

## Troubleshooting

### Container Flask não inicia

**Sintoma:** Flask container sai imediatamente

**Soluções:**
```bash
# Ver logs completos
docker-compose logs flask

# Verificar se o entrypoint tem permissão
chmod +x app/docker-entrypoint.sh

# Verificar se PostgreSQL está healthy
docker-compose ps
```

### Erro de conexão com o banco

**Sintoma:** `psycopg2.OperationalError: could not connect to server`

**Soluções:**
```bash
# Verificar se PostgreSQL está rodando
docker-compose ps postgres

# Verificar variáveis de ambiente
docker-compose exec flask env | grep DATABASE

# Testar conexão manualmente
docker-compose exec flask python3 -c "from src import db; db.engine.connect()"
```

### Tabelas não são criadas

**Sintoma:** Aplicação funciona mas tabelas não existem

**Solução:**
```bash
# Executar manualmente o init_db
docker-compose exec flask python3 init_db.py

# Ou usar Alembic
docker-compose exec flask alembic upgrade head
```

### Erro ao enviar para o governo

**Sintoma:** Timeout ou erro SSL ao enviar XMLs

**Soluções:**
```bash
# Verificar conectividade
docker-compose exec flask curl -v https://endpoint.efdreinf.gov.br

# Verificar certificado
docker-compose exec flask ls -la docs/certificate.pem

# Verificar logs
docker-compose logs flask | grep -i "erro\|error"
```

### Falta de espaço em disco

**Sintoma:** `No space left on device`

**Soluções:**
```bash
# Verificar uso de disco
df -h

# Limpar imagens Docker antigas
docker system prune -a

# Limpar volumes não utilizados
docker volume prune

# Verificar tamanho dos arquivos
du -sh /home/darfflow/darfflow/app/data/*
```

---

## Segurança em Produção

### Checklist de Segurança

- [ ] Alterar todas as senhas padrão
- [ ] Usar HTTPS com certificado válido
- [ ] Configurar firewall (apenas portas necessárias)
- [ ] Definir permissões corretas nos arquivos (600 para .env, certificados)
- [ ] Implementar rate limiting
- [ ] Configurar rotação de logs
- [ ] Implementar backup automático
- [ ] Monitorar acessos não autorizados
- [ ] Manter sistema e dependências atualizados
- [ ] Usar secrets manager para credenciais sensíveis
- [ ] Habilitar auditoria no PostgreSQL
- [ ] Configurar alertas de erro

### Hardening do PostgreSQL

Edite `docker-compose.yml`:
```yaml
postgres:
  command:
    - postgres
    - -c
    - ssl=on
    - -c
    - max_connections=100
    - -c
    - shared_buffers=256MB
```

---

## Atualizações

### Atualizar a Aplicação

```bash
# Fazer backup primeiro!
./backup.sh

# Parar containers
docker-compose down

# Atualizar código
git pull origin main

# Rebuild e restart
docker-compose up -d --build

# Verificar logs
docker-compose logs -f
```

### Aplicar Migrações

```bash
docker-compose exec flask alembic upgrade head
```

---

**Última atualização:** 2025-01-21
**Versão:** 1.0.0
