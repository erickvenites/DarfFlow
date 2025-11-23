# Modelos de Dados - DarfFlow

## Visão Geral

O DarfFlow utiliza PostgreSQL como banco de dados e SQLAlchemy como ORM. Este documento detalha todas as tabelas, seus campos, relacionamentos e índices.

---

## Diagrama de Relacionamentos

```
┌──────────────────────────────┐
│    EventSpreadsheet          │
│    (tb_planilhas)            │
│                              │
│  • id (PK)                   │
│  • om                        │
│  • evento                    │
│  • nome_arquivo              │
│  • tipo                      │
│  • status (Enum)             │
│  • caminho                   │
│  • data_recebimento          │
└──────────────┬───────────────┘
               │ 1:N
               │
┌──────────────▼───────────────┐
│   ConvertedSpreadsheet       │
│   (tb_planilhas_convertidas) │
│                              │
│  • id (PK)                   │
│  • planilha_id (FK)          │
│  • caminho                   │
│  • total_xmls_gerados        │
│  • data_conversao            │
└──────────────┬───────────────┘
               │ 1:N
               │
┌──────────────▼───────────────┐
│      SignedXmls              │
│      (tb_xmls_assinados)     │
│                              │
│  • id (PK)                   │
│  • planilha_convertida_id (FK)│
│  • caminho                   │
│  • data_assinatura           │
└──────────────┬───────────────┘
               │ 1:N
               │
┌──────────────▼───────────────┐
│        XmlsSent              │
│      (tb_xmls_enviados)      │
│                              │
│  • id (PK)                   │
│  • id_xml_assinado (FK)      │
│  • caminho                   │
│  • status_envio              │
│  • protocolo_envio           │
│  • data_envio                │
└──────────────┬───────────────┘
               │ 1:N
               │
┌──────────────▼───────────────┐
│    ShippingResponse          │
│    (tb_resposta_envio)       │
│                              │
│  • id (PK)                   │
│  • enviado_id (FK)           │
│  • caminho                   │
│  • data_resposta             │
└──────────────────────────────┘
```

---

## Tabela: tb_planilhas (EventSpreadsheet)

### Descrição
Armazena informações sobre as planilhas recebidas no sistema.

### Campos

| Campo            | Tipo         | Nulo | Descrição                                    |
|------------------|--------------|------|----------------------------------------------|
| id               | UUID         | Não  | Identificador único (PK)                     |
| om               | String(50)   | Não  | Empresa (ex: DADM, CMNE)         |
| evento           | String(255)  | Não  | Código/nome do evento                        |
| nome_arquivo     | String(255)  | Não  | Nome original do arquivo da planilha         |
| tipo             | String(255)  | Não  | Formato do arquivo (xlsx, xls)               |
| status           | Enum         | Não  | Status atual (FileStatus enum)               |
| caminho          | String(255)  | Não  | Caminho completo do arquivo no servidor      |
| data_recebimento | DateTime     | Não  | Data e hora do recebimento (default: now())  |

### Enum: FileStatus

| Valor      | Descrição                                    |
|------------|----------------------------------------------|
| RECEBIDO   | Planilha recebida, aguardando processamento  |
| CONVERTIDO | XMLs gerados com sucesso                     |
| ASSINADO   | XMLs assinados recebidos                     |
| ENVIADO    | XMLs enviados ao governo                     |

### Relacionamentos
- **1:N** com `ConvertedSpreadsheet` (uma planilha pode ter múltiplas conversões)

### Métodos

#### to_dict()
Converte o objeto em dicionário para serialização JSON.

**Retorno:**
```python
{
    "id": UUID,
    "empresa_id": str,
    "evento": str,
    "nome_arquivo": str,
    "tipo": str,
    "status": str,  # Nome do enum
    "caminho": str,
    "data_recebimento": datetime
}
```

### Exemplo de Uso
```python
from src.models.database import EventSpreadsheet, FileStatus

# Criar novo registro
planilha = EventSpreadsheet(
    om="DADM",
    evento="4020",
    nome_arquivo="planilha_janeiro.xlsx",
    tipo="xlsx",
    status=FileStatus.RECEBIDO,
    caminho="/data/DADM/2025/4020/planilha_janeiro.xlsx"
)
db.session.add(planilha)
db.session.commit()

# Buscar por ID
planilha = EventSpreadsheet.query.filter_by(id=uuid).first()

# Atualizar status
planilha.status = FileStatus.CONVERTIDO
db.session.commit()
```

---

## Tabela: tb_planilhas_convertidas (ConvertedSpreadsheet)

### Descrição
Armazena informações sobre os XMLs gerados a partir das planilhas.

### Campos

| Campo              | Tipo         | Nulo | Descrição                                    |
|--------------------|--------------|------|----------------------------------------------|
| id                 | UUID         | Não  | Identificador único (PK)                     |
| planilha_id        | UUID         | Não  | Referência à planilha original (FK)          |
| caminho            | String(255)  | Não  | Caminho do diretório com os XMLs             |
| total_xmls_gerados | Integer      | Não  | Quantidade de XMLs gerados                   |
| data_conversao     | DateTime     | Não  | Data e hora da conversão (default: now())    |

### Relacionamentos
- **N:1** com `EventSpreadsheet` (backref: `arquivo`)
- **1:N** com `SignedXmls` (backref: `convertido`)

### Índices
- `ix_planilha_id_convertida` - Índice em `planilha_id` para otimizar buscas

### Métodos

#### to_dict()
Converte o objeto em dicionário, incluindo dados da planilha original.

**Retorno:**
```python
{
    "planilha_id": UUID,      # Da planilha original
    "empresa_id": str,                # Da planilha original
    "evento": str,            # Da planilha original
    "id": UUID,
    "caminho": str,
    "total_xmls_gerados": int,
    "data_conversao": datetime
}
```

### Exemplo de Uso
```python
from src.models.database import ConvertedSpreadsheet

# Criar novo registro
convertida = ConvertedSpreadsheet(
    planilha_id=planilha.id,
    caminho="/data/DADM/2025/4020/convertidos/",
    total_xmls_gerados=150
)
db.session.add(convertida)
db.session.commit()

# Buscar por planilha
convertidas = ConvertedSpreadsheet.query.filter_by(
    planilha_id=planilha_id
).all()

# Acessar planilha original via relacionamento
om = convertida.arquivo.om
evento = convertida.arquivo.evento
```

---

## Tabela: tb_xmls_assinados (SignedXmls)

### Descrição
Armazena informações sobre os XMLs assinados digitalmente.

### Campos

| Campo                    | Tipo         | Nulo | Descrição                                    |
|--------------------------|--------------|------|----------------------------------------------|
| id                       | UUID         | Não  | Identificador único (PK)                     |
| planilha_convertida_id   | UUID         | Não  | Referência aos XMLs convertidos (FK)         |
| caminho                  | String(255)  | Não  | Caminho do diretório com XMLs assinados      |
| data_assinatura          | DateTime     | Não  | Data e hora do upload (default: now())       |

### Relacionamentos
- **N:1** com `ConvertedSpreadsheet` (backref: `convertido`)
- **1:N** com `XmlsSent` (backref: `assinado`)

### Índices
- `ix_convertido_id_assinado` - Índice em `planilha_convertida_id`

### Métodos

#### to_dict()
Converte o objeto em dicionário, incluindo dados da planilha original.

**Retorno:**
```python
{
    "planilha_id": UUID,      # Da planilha original
    "empresa_id": str,                # Da planilha original
    "evento": str,            # Da planilha original
    "id": UUID,
    "caminho": str,
    "data_assinatura": datetime
}
```

### Exemplo de Uso
```python
from src.models.database import SignedXmls

# Criar novo registro
assinado = SignedXmls(
    planilha_convertida_id=convertida.id,
    caminho="/data/DADM/2025/4020/assinados/"
)
db.session.add(assinado)
db.session.commit()

# Buscar por conversão
assinados = SignedXmls.query.filter_by(
    planilha_convertida_id=convertida_id
).all()

# Acessar dados originais via relacionamentos
planilha_id = assinado.convertido.arquivo.id
```

---

## Tabela: tb_xmls_enviados (XmlsSent)

### Descrição
Armazena informações sobre os XMLs enviados ao governo.

### Campos

| Campo              | Tipo         | Nulo | Descrição                                    |
|--------------------|--------------|------|----------------------------------------------|
| id                 | UUID         | Não  | Identificador único (PK)                     |
| id_xml_assinado    | UUID         | Não  | Referência ao XML assinado (FK)              |
| caminho            | String(255)  | Não  | Caminho do XML enviado                       |
| status_envio       | String(255)  | Não  | Status do envio (sucesso, erro, etc)         |
| protocolo_envio    | String(255)  | Não  | Número do protocolo retornado pelo governo   |
| data_envio         | DateTime     | Não  | Data e hora do envio (default: now())        |

### Relacionamentos
- **N:1** com `SignedXmls` (backref: `assinado`)
- **1:N** com `ShippingResponse` (backref: `enviado`)

### Índices
- `ix_assinado_id_enviado` - Índice em `id_xml_assinado`

### Métodos

#### to_dict()
Converte o objeto em dicionário, incluindo dados da planilha original.

**Retorno:**
```python
{
    "planilha_id": UUID,      # Da planilha original
    "empresa_id": str,                # Da planilha original
    "evento": str,            # Da planilha original
    "status": str,            # Status da planilha original
    "sent_id": UUID,
    "caminho": str,
    "status_envio": str,
    "data_envio": datetime
}
```

### Exemplo de Uso
```python
from src.models.database import XmlsSent

# Criar novo registro
enviado = XmlsSent(
    id_xml_assinado=assinado.id,
    caminho="/data/DADM/2025/4020/enviados/evento_001.xml",
    status_envio="sucesso",
    protocolo_envio="RFB2025123456789"
)
db.session.add(enviado)
db.session.commit()

# Buscar por protocolo
enviado = XmlsSent.query.filter_by(
    protocolo_envio="RFB2025123456789"
).first()

# Buscar enviados com erro
erros = XmlsSent.query.filter_by(status_envio="erro").all()
```

---

## Tabela: tb_resposta_envio (ShippingResponse)

### Descrição
Armazena as respostas recebidas do governo para os envios realizados.

### Campos

| Campo          | Tipo         | Nulo | Descrição                                    |
|----------------|--------------|------|----------------------------------------------|
| id             | UUID         | Não  | Identificador único (PK)                     |
| enviado_id     | UUID         | Não  | Referência ao envio (FK)                     |
| caminho        | String(255)  | Não  | Caminho do arquivo de resposta               |
| data_resposta  | DateTime     | Não  | Data e hora da resposta (default: now())     |

### Relacionamentos
- **N:1** com `XmlsSent` (backref: `enviado`)

### Índices
- `ix_enviado_id_resposta` - Índice em `enviado_id`

### Métodos

#### to_dict()
Converte o objeto em dicionário, incluindo dados da planilha original.

**Retorno:**
```python
{
    "planilha_id": UUID,      # Da planilha original
    "empresa_id": str,                # Da planilha original
    "evento": str,            # Da planilha original
    "status": str,            # Status da planilha original
    "response_id": UUID,
    "caminho": str,
    "data_resposta": datetime
}
```

### Exemplo de Uso
```python
from src.models.database import ShippingResponse

# Criar novo registro
resposta = ShippingResponse(
    enviado_id=enviado.id,
    caminho="/data/DADM/2025/4020/respostas/resposta_001.xml"
)
db.session.add(resposta)
db.session.commit()

# Buscar resposta de um envio
resposta = ShippingResponse.query.filter_by(
    enviado_id=enviado_id
).first()

# Acessar toda a cadeia de relacionamentos
planilha = resposta.enviado.assinado.convertido.arquivo
```

---

## Índices do Banco de Dados

O sistema implementa índices para otimizar as consultas mais frequentes:

| Índice                      | Tabela                     | Campo(s)               | Propósito                        |
|-----------------------------|----------------------------|------------------------|----------------------------------|
| ix_planilha_id_convertida   | tb_planilhas_convertidas   | planilha_id            | Buscar conversões por planilha   |
| ix_convertido_id_assinado   | tb_xmls_assinados          | planilha_convertida_id | Buscar assinados por conversão   |
| ix_assinado_id_enviado      | tb_xmls_enviados           | id_xml_assinado        | Buscar enviados por assinado     |
| ix_enviado_id_resposta      | tb_resposta_envio          | enviado_id             | Buscar respostas por envio       |

---

## Consultas Comuns

### Buscar todas as planilhas de uma empresa_id em um ano

```python
from sqlalchemy import extract

planilhas = EventSpreadsheet.query.filter(
    EventSpreadsheet.om == "DADM",
    extract('year', EventSpreadsheet.data_recebimento) == 2025
).all()
```

### Buscar planilhas por status

```python
from src.models.database import EventSpreadsheet, FileStatus

# Todas as planilhas recebidas
recebidas = EventSpreadsheet.query.filter_by(
    status=FileStatus.RECEBIDO
).all()

# Todas as planilhas enviadas
enviadas = EventSpreadsheet.query.filter_by(
    status=FileStatus.ENVIADO
).all()
```

### Buscar XMLs convertidos de uma planilha

```python
convertidos = ConvertedSpreadsheet.query.filter_by(
    planilha_id=planilha_id
).all()
```

### Buscar envios com erro

```python
erros = XmlsSent.query.filter_by(
    status_envio="erro"
).all()

for erro in erros:
    print(f"Planilha: {erro.assinado.convertido.arquivo.nome_arquivo}")
    print(f"Protocolo: {erro.protocolo_envio}")
```

### Rastrear todo o histórico de uma planilha

```python
planilha = EventSpreadsheet.query.get(planilha_id)

# Via relacionamentos
for convertida in planilha.planilhas:
    print(f"Convertida em: {convertida.data_conversao}")
    print(f"Total XMLs: {convertida.total_xmls_gerados}")

    for assinado in convertida.assinados:
        print(f"Assinado em: {assinado.data_assinatura}")

        for enviado in assinado.enviados:
            print(f"Enviado em: {enviado.data_envio}")
            print(f"Protocolo: {enviado.protocolo_envio}")

            for resposta in enviado.respostas:
                print(f"Resposta em: {resposta.data_resposta}")
```

---

## Migrações com Alembic

O projeto usa Alembic para gerenciar migrações de banco de dados.

### Criar uma nova migração

```bash
cd app
alembic revision --autogenerate -m "Descrição da mudança"
```

### Aplicar migrações

```bash
alembic upgrade head
```

### Reverter migração

```bash
alembic downgrade -1
```

### Ver histórico de migrações

```bash
alembic history
```

---

## Considerações de Performance

### Lazy Loading
Os relacionamentos usam `lazy='dynamic'`, permitindo queries otimizadas:

```python
# Ao invés de carregar todos os registros
planilha.planilhas.all()  # Carrega tudo

# Você pode filtrar antes de carregar
planilha.planilhas.filter_by(
    data_conversao >= datetime(2025, 1, 1)
).all()
```

### Eager Loading
Para evitar N+1 queries, use joinedload:

```python
from sqlalchemy.orm import joinedload

planilhas = EventSpreadsheet.query.options(
    joinedload(EventSpreadsheet.planilhas)
).all()
```

### Transações
Sempre use transações para operações que modificam múltiplas tabelas:

```python
try:
    planilha.status = FileStatus.CONVERTIDO
    convertida = ConvertedSpreadsheet(...)
    db.session.add(convertida)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise
```

---

## Backup e Restauração

### Backup do banco de dados

```bash
docker exec darfflow-postgres-1 pg_dump -U postgres efdreinf > backup.sql
```

### Restauração do banco de dados

```bash
docker exec -i darfflow-postgres-1 psql -U postgres efdreinf < backup.sql
```

### Exportar dados para CSV

```sql
COPY tb_planilhas TO '/backup/planilhas.csv' DELIMITER ',' CSV HEADER;
```

---

## Validações e Constraints

### UUIDs
Todos os IDs são UUID v4, garantindo unicidade global.

### NOT NULL
Todos os campos são obrigatórios (NOT NULL), garantindo integridade dos dados.

### Foreign Keys
As chaves estrangeiras garantem integridade referencial:
- Não é possível deletar uma planilha que tem conversões
- Não é possível deletar uma conversão que tem assinados
- E assim por diante

Para deletar em cascata, seria necessário modificar os relacionamentos.

---

## Manutenção

### Limpeza de dados antigos

```python
from datetime import datetime, timedelta

# Deletar planilhas com mais de 5 anos
data_limite = datetime.now() - timedelta(days=5*365)
planilhas_antigas = EventSpreadsheet.query.filter(
    EventSpreadsheet.data_recebimento < data_limite
).all()

for planilha in planilhas_antigas:
    # Deletar arquivos do disco primeiro
    # Depois deletar do banco
    db.session.delete(planilha)

db.session.commit()
```

### Estatísticas do banco

```sql
-- Total de planilhas por status
SELECT status, COUNT(*)
FROM tb_planilhas
GROUP BY status;

-- Total de XMLs gerados por mês
SELECT
    DATE_TRUNC('month', data_conversao) as mes,
    SUM(total_xmls_gerados) as total
FROM tb_planilhas_convertidas
GROUP BY mes
ORDER BY mes DESC;

-- Taxa de sucesso de envios
SELECT
    status_envio,
    COUNT(*) as total,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as percentual
FROM tb_xmls_enviados
GROUP BY status_envio;
```
