# Referência da API - DarfFlow

## Índice
- [Autenticação](#autenticação)
- [Planilhas](#planilhas)
- [Arquivos Processados](#arquivos-processados)
- [Arquivos Assinados](#arquivos-assinados)
- [Códigos de Status](#códigos-de-status)

---

## Autenticação

A maioria dos endpoints requer autenticação via token. O token deve ser enviado no header da requisição:

```
Authorization: Bearer <seu_token>
```

**Exceção:** O endpoint `/api/planilhas/upload` não requer autenticação.

---

## Planilhas

Base URL: `/api/planilhas`

### 1. Upload de Planilha

Realiza o upload de uma planilha (.xlsx ou .xls) para processamento.

**Endpoint:** `POST /api/planilhas/upload`

**Autenticação:** Não requerida

**Parâmetros Query:**
| Parâmetro | Tipo   | Obrigatório | Descrição                           |
|-----------|--------|-------------|-------------------------------------|
| om        | string | Sim         | Empresa (ex: DADM)      |
| evento    | string | Sim         | Nome/código do evento (ex: 4020...) |

**Body (multipart/form-data):**
| Campo     | Tipo | Descrição                |
|-----------|------|--------------------------|
| planilha  | File | Arquivo da planilha      |

**Exemplo de Requisição:**
```bash
curl -X POST "http://localhost:5000/api/planilhas/upload?empresa_id=DADM&evento=4020" \
  -F "planilha=@/caminho/para/planilha.xlsx"
```

**Respostas:**
- `200 OK`: Planilha enviada com sucesso
- `400 Bad Request`: Parâmetros ausentes ou arquivo inválido
- `500 Internal Server Error`: Erro no processamento

---

### 2. Processar Planilha

Processa uma planilha recebida e gera os arquivos XML.

**Endpoint:** `POST /api/planilhas/processar`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo   | Obrigatório | Descrição                    |
|--------------|--------|-------------|------------------------------|
| planilha_id  | UUID   | Sim         | ID da planilha a processar   |
| cnpj         | string | Sim         | CNPJ da empresa              |

**Exemplo de Requisição:**
```bash
curl -X POST "http://localhost:5000/api/planilhas/processar?planilha_id=<uuid>&cnpj=12345678000190" \
  -H "Authorization: Bearer <token>"
```

**Respostas:**
- `200 OK`: Planilha processada com sucesso
- `400 Bad Request`: Parâmetros ausentes
- `404 Not Found`: Planilha não encontrada
- `500 Internal Server Error`: Erro no processamento

---

### 3. Listar Planilhas

Busca todas as planilhas cadastradas com filtros específicos.

**Endpoint:** `GET /api/planilhas/`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro | Tipo   | Obrigatório | Descrição                    |
|-----------|--------|-------------|------------------------------|
| om        | string | Sim         | Empresa          |
| ano       | string | Sim         | Ano de referência            |
| evento    | string | Sim         | Código do evento             |

**Exemplo de Requisição:**
```bash
curl -X GET "http://localhost:5000/api/planilhas/?empresa_id=DADM&ano=2025&evento=4020" \
  -H "Authorization: Bearer <token>"
```

**Resposta de Sucesso (200 OK):**
```json
[
  {
    "id": "uuid",
    "empresa_id": "DADM",
    "evento": "4020",
    "nome_arquivo": "planilha.xlsx",
    "tipo": "xlsx",
    "status": "Recebido",
    "caminho": "/path/to/file",
    "data_recebimento": "2025-01-21T10:30:00"
  }
]
```

---

### 4. Buscar Planilha por ID

Busca uma planilha específica pelo seu ID.

**Endpoint:** `GET /api/planilhas/`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo | Obrigatório | Descrição              |
|--------------|------|-------------|------------------------|
| planilha_id  | UUID | Sim         | ID da planilha         |

**Exemplo de Requisição:**
```bash
curl -X GET "http://localhost:5000/api/planilhas/?planilha_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```

**Resposta de Sucesso (200 OK):**
```json
{
  "id": "uuid",
  "empresa_id": "DADM",
  "evento": "4020",
  "nome_arquivo": "planilha.xlsx",
  "tipo": "xlsx",
  "status": "Recebido",
  "caminho": "/path/to/file",
  "data_recebimento": "2025-01-21T10:30:00"
}
```

---

### 5. Download de Planilha

Realiza o download de uma planilha registrada.

**Endpoint:** `POST /api/planilhas/download`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo | Obrigatório | Descrição              |
|--------------|------|-------------|------------------------|
| planilha_id  | UUID | Sim         | ID da planilha         |

**Exemplo de Requisição:**
```bash
curl -X POST "http://localhost:5000/api/planilhas/download?planilha_id=<uuid>" \
  -H "Authorization: Bearer <token>" \
  --output planilha.xlsx
```

**Respostas:**
- `200 OK`: Arquivo retornado para download
- `400 Bad Request`: ID ausente
- `404 Not Found`: Planilha não encontrada
- `500 Internal Server Error`: Erro no processamento

---

### 6. Deletar Planilha e Evento

Deleta uma planilha e o evento associado.

**Endpoint:** `DELETE /api/planilhas/`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo | Obrigatório | Descrição              |
|--------------|------|-------------|------------------------|
| planilha_id  | UUID | Sim         | ID da planilha         |

**Exemplo de Requisição:**
```bash
curl -X DELETE "http://localhost:5000/api/planilhas/?planilha_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```

**Respostas:**
- `200 OK`: Planilha deletada com sucesso
- `400 Bad Request`: ID ausente
- `404 Not Found`: Planilha não encontrada
- `500 Internal Server Error`: Erro ao deletar

---

## Arquivos Processados

Base URL: `/api/arquivos-processados`

### 1. Listar Arquivos Processados

Lista os diretórios de XMLs processados disponíveis.

**Endpoint:** `GET /api/arquivos-processados/listar`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro | Tipo   | Obrigatório | Descrição              |
|-----------|--------|-------------|------------------------|
| om        | string | Sim         | Empresa    |
| ano       | string | Sim         | Ano de referência      |
| evento    | string | Sim         | Código do evento       |

**Exemplo de Requisição:**
```bash
curl -X GET "http://localhost:5000/api/arquivos-processados/listar?empresa_id=DADM&ano=2025&evento=4020" \
  -H "Authorization: Bearer <token>"
```

**Resposta de Sucesso (200 OK):**
```json
[
  {
    "id": "uuid",
    "planilha_id": "uuid",
    "empresa_id": "DADM",
    "evento": "4020",
    "caminho": "/path/to/xmls",
    "total_xmls_gerados": 150,
    "data_conversao": "2025-01-21T11:00:00"
  }
]
```

---

### 2. Buscar Arquivo Processado por ID

Busca um arquivo processado específico pelo ID.

**Endpoint:** `GET /api/arquivos-processados`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo | Obrigatório | Descrição                  |
|--------------|------|-------------|----------------------------|
| arquivo_id   | UUID | Sim         | ID do arquivo processado   |

**Exemplo de Requisição:**
```bash
curl -X GET "http://localhost:5000/api/arquivos-processados?arquivo_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Download de Arquivos Processados

Faz o download de todos os XMLs de um diretório em formato ZIP.

**Endpoint:** `POST /api/arquivos-processados/download`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo | Obrigatório | Descrição                  |
|--------------|------|-------------|----------------------------|
| arquivo_id   | UUID | Sim         | ID do arquivo processado   |

**Exemplo de Requisição:**
```bash
curl -X POST "http://localhost:5000/api/arquivos-processados/download?arquivo_id=<uuid>" \
  -H "Authorization: Bearer <token>" \
  --output xmls.zip
```

**Respostas:**
- `200 OK`: Arquivo ZIP retornado para download
- `400 Bad Request`: ID ausente
- `404 Not Found`: Arquivo não encontrado
- `500 Internal Server Error`: Erro no processamento

---

### 4. Deletar Arquivos Processados

Exclui um diretório de XMLs processados.

**Endpoint:** `DELETE /api/arquivos-processados`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo | Obrigatório | Descrição                  |
|--------------|------|-------------|----------------------------|
| arquivo_id   | UUID | Sim         | ID do arquivo processado   |

**Exemplo de Requisição:**
```bash
curl -X DELETE "http://localhost:5000/api/arquivos-processados?arquivo_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```

---

## Arquivos Assinados

Base URL: `/api/assinados`

### 1. Upload de XMLs Assinados

Faz o upload de um arquivo ZIP contendo XMLs assinados.

**Endpoint:** `POST /api/assinados/upload`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo   | Obrigatório | Descrição                    |
|--------------|--------|-------------|------------------------------|
| om           | string | Sim         | Empresa          |
| evento       | string | Sim         | Código do evento             |
| planilha_id  | UUID   | Sim         | ID da planilha original      |

**Body (multipart/form-data):**
| Campo    | Tipo | Descrição                         |
|----------|------|-----------------------------------|
| arquivo  | File | Arquivo ZIP com XMLs assinados    |

**Exemplo de Requisição:**
```bash
curl -X POST "http://localhost:5000/api/assinados/upload?empresa_id=DADM&evento=4020&planilha_id=<uuid>" \
  -H "Authorization: Bearer <token>" \
  -F "arquivo=@/caminho/para/xmls_assinados.zip"
```

**Respostas:**
- `200 OK`: Arquivo enviado com sucesso
- `400 Bad Request`: Parâmetros ausentes ou arquivo inválido
- `500 Internal Server Error`: Erro no processamento

---

### 2. Listar XMLs Assinados

Lista todos os arquivos assinados para uma combinação específica.

**Endpoint:** `GET /api/assinados/listar`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro | Tipo   | Obrigatório | Descrição              |
|-----------|--------|-------------|------------------------|
| om        | string | Sim         | Empresa    |
| evento    | string | Sim         | Código do evento       |
| ano       | string | Sim         | Ano de referência      |

**Exemplo de Requisição:**
```bash
curl -X GET "http://localhost:5000/api/assinados/listar?empresa_id=DADM&evento=4020&ano=2025" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Buscar XML Assinado por ID

Busca um arquivo assinado pelo seu ID.

**Endpoint:** `GET /api/assinados`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro   | Tipo | Obrigatório | Descrição               |
|-------------|------|-------------|-------------------------|
| arquivo_id  | UUID | Sim         | ID do arquivo assinado  |

**Exemplo de Requisição:**
```bash
curl -X GET "http://localhost:5000/api/assinados?arquivo_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```

---

### 4. Enviar XMLs Assinados

Processa e envia os XMLs assinados para o endpoint externo (EFD-Reinf).

**Endpoint:** `POST /api/assinados/enviar`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro    | Tipo   | Obrigatório | Descrição                    |
|--------------|--------|-------------|------------------------------|
| om           | string | Sim         | Empresa          |
| evento       | string | Sim         | Código do evento             |
| planilha_id  | UUID   | Sim         | ID da planilha original      |
| cnpj         | string | Sim         | CNPJ da empresa              |
| ano          | string | Sim         | Ano de referência            |

**Exemplo de Requisição:**
```bash
curl -X POST "http://localhost:5000/api/assinados/enviar?empresa_id=DADM&evento=4020&planilha_id=<uuid>&cnpj=12345678000190&ano=2025" \
  -H "Authorization: Bearer <token>"
```

**Resposta de Sucesso (200 OK):**
```json
{
  "mensagem": "Lote processado com sucesso",
  "resposta": {
    "protocolo": "protocolo123",
    "status": "Enviado",
    "detalhes": "..."
  }
}
```

**Respostas:**
- `200 OK`: Lote processado e enviado com sucesso
- `400 Bad Request`: Parâmetros ausentes
- `500 Internal Server Error`: Falha ao processar o lote

---

### 5. Deletar XMLs Assinados

Exclui um arquivo ZIP de XMLs assinados.

**Endpoint:** `DELETE /api/assinados`

**Autenticação:** Requerida

**Parâmetros Query:**
| Parâmetro   | Tipo | Obrigatório | Descrição               |
|-------------|------|-------------|-------------------------|
| arquivo_id  | UUID | Sim         | ID do arquivo assinado  |

**Exemplo de Requisição:**
```bash
curl -X DELETE "http://localhost:5000/api/assinados?arquivo_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```

---

## Códigos de Status

| Código | Descrição                                      |
|--------|------------------------------------------------|
| 200    | Sucesso - Requisição processada com sucesso   |
| 400    | Bad Request - Parâmetros inválidos ou ausentes|
| 401    | Unauthorized - Token ausente ou inválido       |
| 404    | Not Found - Recurso não encontrado             |
| 500    | Internal Server Error - Erro no servidor       |

---

## Notas Importantes

1. **Formatos de Arquivo:**
   - Planilhas: `.xlsx`, `.xls`
   - Arquivos assinados: `.zip` contendo `.xml`

2. **UUIDs:**
   - Todos os IDs são UUID v4
   - Devem ser enviados no formato string

3. **Datas:**
   - Todas as datas são retornadas no formato ISO 8601
   - Exemplo: `2025-01-21T10:30:00`

4. **CNPJ:**
   - Deve ser enviado apenas números
   - Exemplo: `12345678000190`

5. **empresa_id (Empresa):**
   - Sempre em maiúsculas
   - A API faz conversão automática para uppercase
