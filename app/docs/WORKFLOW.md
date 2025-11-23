# Fluxo de Trabalho - DarfFlow

## Visão Geral

O DarfFlow é um sistema para processamento e envio de arquivos EFD-Reinf ao governo. O fluxo completo envolve 4 etapas principais:

1. **Recebimento da Planilha** - Upload da planilha com dados
2. **Processamento e Geração de XMLs** - Conversão da planilha em arquivos XML
3. **Assinatura e Upload dos XMLs** - Upload dos XMLs assinados digitalmente
4. **Envio ao Governo** - Transmissão dos XMLs ao endpoint EFD-Reinf

Este documento explica detalhadamente cada etapa do processo.

---

## Diagrama do Fluxo

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FLUXO COMPLETO DO DARFFLOW                        │
└─────────────────────────────────────────────────────────────────────────┘

    [Cliente]
        │
        │ 1. Upload Planilha (.xlsx/.xls)
        ▼
    ┌───────────────────────┐
    │  POST /planilhas/     │  ← Sem autenticação
    │       upload          │
    └───────────────────────┘
        │
        │ Salva planilha
        │ Status: "Recebido"
        ▼
    ┌───────────────────────┐
    │  tb_planilhas         │
    │  (EventSpreadsheet)   │
    └───────────────────────┘
        │
        │ 2. Processa Planilha
        │    POST /planilhas/processar
        │    (com CNPJ)
        ▼
    ┌───────────────────────┐
    │  Gera XMLs            │
    │  Status: "Convertido" │
    └───────────────────────┘
        │
        │ Salva informações dos XMLs
        ▼
    ┌───────────────────────────┐
    │  tb_planilhas_convertidas │
    │  (ConvertedSpreadsheet)   │
    └───────────────────────────┘
        │
        │ 3. Usuário baixa XMLs
        │    GET /arquivos-processados/download
        │
        │ 4. Assina XMLs externamente
        │    (Certificado Digital)
        │
        │ 5. Upload ZIP com XMLs Assinados
        │    POST /assinados/upload
        ▼
    ┌───────────────────────┐
    │  tb_xmls_assinados    │
    │  (SignedXmls)         │
    │  Status: "Assinado"   │
    └───────────────────────┘
        │
        │ 6. Envia para Governo
        │    POST /assinados/enviar
        ▼
    ┌───────────────────────┐
    │  Processa e Envia     │
    │  para endpoint externo│
    │  Status: "Enviado"    │
    └───────────────────────┘
        │
        │ Salva protocolo e resposta
        ▼
    ┌───────────────────────┐
    │  tb_xmls_enviados     │
    │  (XmlsSent)           │
    └───────────────────────┘
        │
        │ Resposta do governo
        ▼
    ┌───────────────────────┐
    │  tb_resposta_envio    │
    │  (ShippingResponse)   │
    └───────────────────────┘
```

---

## Etapa 1: Recebimento da Planilha

### Objetivo
Receber a planilha enviada pelo usuário e armazená-la no sistema para processamento posterior.

### Processo

1. **Cliente envia a planilha**
   - Endpoint: `POST /api/planilhas/upload`
   - Parâmetros: `empresa_id` (Empresa), `evento` (código do evento)
   - Body: arquivo da planilha (formato .xlsx ou .xls)

2. **Sistema valida a requisição**
   - Verifica se os parâmetros obrigatórios estão presentes
   - Valida o formato do arquivo
   - Verifica se um arquivo foi realmente enviado

3. **Sistema armazena a planilha**
   - Cria um diretório estruturado: `empresa_id/ANO/EVENTO/`
   - Salva o arquivo no diretório
   - Registra no banco de dados (`tb_planilhas`)

4. **Registro no banco de dados**
   - **Tabela:** `EventSpreadsheet` (tb_planilhas)
   - **Campos salvos:**
     - `id`: UUID gerado automaticamente
     - `empresa_id`: Empresa
     - `evento`: Código do evento
     - `nome_arquivo`: Nome original da planilha
     - `tipo`: Formato do arquivo (xlsx, xls)
     - `status`: FileStatus.RECEBIDO
     - `caminho`: Caminho onde a planilha foi salva
     - `data_recebimento`: Timestamp do recebimento

### Resultado
- Planilha armazenada no sistema
- Status: **RECEBIDO**
- UUID gerado para identificação
- Cliente recebe confirmação do upload

### Exemplo de Resposta
```json
{
  "mensagem": "Planilha recebida com sucesso",
  "planilha_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "Recebido"
}
```

---

## Etapa 2: Processamento e Geração de XMLs

### Objetivo
Processar a planilha recebida e gerar os arquivos XML no formato EFD-Reinf.

### Processo

1. **Cliente solicita processamento**
   - Endpoint: `POST /api/planilhas/processar`
   - Parâmetros: `planilha_id` (UUID da planilha), `cnpj` (CNPJ da empresa)
   - Requer autenticação (token)

2. **Sistema busca a planilha**
   - Consulta o banco de dados pelo `planilha_id`
   - Verifica se a planilha existe e está com status RECEBIDO
   - Localiza o arquivo no sistema de arquivos

3. **Sistema processa a planilha**
   - Lê os dados da planilha Excel
   - Valida os dados de acordo com as regras do EFD-Reinf
   - Para cada linha da planilha, gera um arquivo XML
   - Aplica o CNPJ fornecido nos XMLs gerados

4. **Sistema salva os XMLs gerados**
   - Cria um diretório para os XMLs: `empresa_id/ANO/EVENTO/convertidos/`
   - Salva todos os XMLs gerados no diretório
   - Compacta os XMLs em um arquivo ZIP

5. **Registro no banco de dados**
   - **Tabela:** `ConvertedSpreadsheet` (tb_planilhas_convertidas)
   - **Campos salvos:**
     - `id`: UUID gerado automaticamente
     - `planilha_id`: Referência à planilha original
     - `caminho`: Caminho dos XMLs convertidos
     - `total_xmls_gerados`: Quantidade de XMLs criados
     - `data_conversao`: Timestamp da conversão

6. **Atualização da planilha original**
   - Status da planilha atualizado para: **CONVERTIDO**

### Resultado
- XMLs gerados e armazenados
- Status da planilha: **CONVERTIDO**
- Registro da conversão no banco
- XMLs disponíveis para download

### Exemplo de Resposta
```json
{
  "mensagem": "Planilha processada com sucesso",
  "total_xmls_gerados": 150,
  "arquivo_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

---

## Etapa 3: Assinatura e Upload dos XMLs

### Objetivo
Permitir que o usuário baixe os XMLs, assine-os digitalmente e faça o upload dos arquivos assinados.

### Processo

#### 3.1 Download dos XMLs para Assinatura

1. **Cliente solicita download**
   - Endpoint: `POST /api/arquivos-processados/download`
   - Parâmetro: `arquivo_id` (UUID do arquivo processado)
   - Requer autenticação

2. **Sistema prepara o download**
   - Localiza os XMLs pelo `arquivo_id`
   - Cria um arquivo ZIP com todos os XMLs
   - Retorna o ZIP para download

3. **Cliente realiza a assinatura**
   - **Importante:** Esta etapa é EXTERNA ao sistema
   - O usuário deve usar uma ferramenta de assinatura digital
   - Cada XML deve ser assinado com certificado digital válido
   - O certificado deve estar de acordo com os padrões ICP-Brasil

#### 3.2 Upload dos XMLs Assinados

1. **Cliente envia os XMLs assinados**
   - Endpoint: `POST /api/assinados/upload`
   - Parâmetros: `empresa_id`, `evento`, `planilha_id`
   - Body: arquivo ZIP contendo os XMLs assinados
   - Requer autenticação

2. **Sistema valida o upload**
   - Verifica os parâmetros obrigatórios
   - Valida o formato do arquivo (deve ser .zip)
   - Verifica se o arquivo não está vazio

3. **Sistema processa o ZIP**
   - Extrai os XMLs do arquivo ZIP
   - Valida a estrutura dos XMLs
   - Verifica as assinaturas digitais

4. **Sistema armazena os XMLs assinados**
   - Cria diretório: `empresa_id/ANO/EVENTO/assinados/`
   - Salva os XMLs assinados no diretório
   - Mantém o arquivo ZIP original

5. **Registro no banco de dados**
   - **Tabela:** `SignedXmls` (tb_xmls_assinados)
   - **Campos salvos:**
     - `id`: UUID gerado automaticamente
     - `planilha_convertida_id`: Referência aos XMLs convertidos
     - `caminho`: Caminho dos XMLs assinados
     - `data_assinatura`: Timestamp do upload

6. **Atualização da planilha original**
   - Status da planilha atualizado para: **ASSINADO**

### Resultado
- XMLs assinados armazenados no sistema
- Status da planilha: **ASSINADO**
- Arquivos prontos para envio ao governo

### Exemplo de Resposta
```json
{
  "mensagem": "XMLs assinados recebidos com sucesso",
  "total_arquivos": 150,
  "arquivo_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

---

## Etapa 4: Envio ao Governo (EFD-Reinf)

### Objetivo
Transmitir os XMLs assinados para o endpoint oficial do EFD-Reinf do governo.

### Processo

1. **Cliente solicita o envio**
   - Endpoint: `POST /api/assinados/enviar`
   - Parâmetros: `empresa_id`, `evento`, `planilha_id`, `cnpj`, `ano`
   - Requer autenticação

2. **Sistema prepara o envio**
   - Busca os XMLs assinados pelo `planilha_id`
   - Valida se todos os arquivos estão prontos
   - Carrega o certificado digital do servidor

3. **Sistema envia os XMLs em lote**
   - Para cada XML assinado:
     - Estabelece conexão SSL com o endpoint do governo
     - Envia o XML usando o protocolo HTTPS
     - Aguarda resposta do servidor
     - Registra o protocolo de envio

4. **Sistema processa as respostas**
   - Analisa a resposta de cada envio
   - Verifica se houve sucesso ou erro
   - Extrai o número do protocolo
   - Salva os detalhes da resposta

5. **Registro no banco de dados - Envio**
   - **Tabela:** `XmlsSent` (tb_xmls_enviados)
   - **Campos salvos:**
     - `id`: UUID gerado automaticamente
     - `id_xml_assinado`: Referência ao XML assinado
     - `caminho`: Caminho do XML enviado
     - `status_envio`: Status do envio (sucesso/erro)
     - `protocolo_envio`: Número do protocolo retornado
     - `data_envio`: Timestamp do envio

6. **Registro no banco de dados - Resposta**
   - **Tabela:** `ShippingResponse` (tb_resposta_envio)
   - **Campos salvos:**
     - `id`: UUID gerado automaticamente
     - `enviado_id`: Referência ao envio
     - `caminho`: Caminho do arquivo de resposta
     - `data_resposta`: Timestamp da resposta

7. **Atualização da planilha original**
   - Status da planilha atualizado para: **ENVIADO**

### Resultado
- XMLs transmitidos ao governo
- Status da planilha: **ENVIADO**
- Protocolos de envio registrados
- Respostas do governo armazenadas

### Exemplo de Resposta
```json
{
  "mensagem": "Lote processado com sucesso",
  "resposta": {
    "total_enviados": 150,
    "sucesso": 148,
    "erros": 2,
    "protocolo_principal": "RFB2025123456789",
    "detalhes": [
      {
        "arquivo": "evento_001.xml",
        "status": "sucesso",
        "protocolo": "RFB2025123456790"
      },
      {
        "arquivo": "evento_002.xml",
        "status": "erro",
        "mensagem": "Erro de validação: CNPJ inválido"
      }
    ]
  }
}
```

---

## Estados da Planilha

Durante todo o processo, a planilha passa por diferentes estados:

| Estado      | Descrição                                           | Pode Avançar Para |
|-------------|-----------------------------------------------------|-------------------|
| RECEBIDO    | Planilha foi recebida e está aguardando processamento | CONVERTIDO      |
| CONVERTIDO  | XMLs foram gerados e estão prontos para assinatura  | ASSINADO         |
| ASSINADO    | XMLs assinados foram recebidos e validados          | ENVIADO          |
| ENVIADO     | XMLs foram transmitidos ao governo com sucesso      | (Estado final)   |

---

## Relacionamentos entre Tabelas

```
tb_planilhas (EventSpreadsheet)
    │
    │ 1:N
    ▼
tb_planilhas_convertidas (ConvertedSpreadsheet)
    │
    │ 1:N
    ▼
tb_xmls_assinados (SignedXmls)
    │
    │ 1:N
    ▼
tb_xmls_enviados (XmlsSent)
    │
    │ 1:N
    ▼
tb_resposta_envio (ShippingResponse)
```

Cada etapa do processo cria registros nas respectivas tabelas, mantendo o histórico completo e rastreabilidade de todo o fluxo.

---

## Boas Práticas

### Para Desenvolvedores

1. **Sempre verifique o status da planilha** antes de executar uma operação
2. **Use transações de banco** para operações que modificam múltiplas tabelas
3. **Registre logs detalhados** em cada etapa do processo
4. **Valide os XMLs** antes de enviá-los ao governo
5. **Implemente retry** para falhas de comunicação com o endpoint externo
6. **Armazene as respostas completas** do governo para auditoria

### Para Operadores

1. **Verifique a planilha** antes de fazer o upload
2. **Aguarde o processamento completo** antes de baixar os XMLs
3. **Use certificado digital válido** para assinar os XMLs
4. **Assine TODOS os XMLs** antes de fazer o upload
5. **Verifique os protocolos** após o envio
6. **Guarde os números de protocolo** para consultas futuras

### Para Administradores

1. **Monitore o espaço em disco** - os arquivos acumulam ao longo do tempo
2. **Faça backup regular** do banco de dados e dos arquivos
3. **Mantenha o certificado atualizado** no servidor
4. **Configure alertas** para falhas de envio
5. **Implemente rotina de limpeza** para arquivos antigos
6. **Documente as credenciais** do endpoint governamental

---

## Troubleshooting

### Planilha não processa
- Verifique se o status está RECEBIDO
- Confirme se o arquivo existe no disco
- Valide o formato da planilha
- Verifique os logs de erro

### XMLs não geram
- Confirme se o CNPJ está no formato correto
- Verifique se a planilha tem dados válidos
- Analise as mensagens de erro no log
- Teste o processamento com uma planilha menor

### Assinatura falha
- Verifique se o certificado é válido
- Confirme se o certificado está no padrão ICP-Brasil
- Teste a assinatura com uma ferramenta standalone
- Verifique a data de validade do certificado

### Envio falha
- Confirme se o endpoint está acessível
- Verifique as credenciais de acesso
- Analise a resposta de erro do governo
- Teste com XMLs individuais primeiro
- Verifique se o certificado do servidor está configurado

---

## Segurança

### Autenticação
- Todos os endpoints (exceto upload inicial) requerem token JWT
- Tokens devem ser renovados periodicamente
- Implemente rate limiting para evitar abuso

### Certificados
- Use certificados A1 ou A3 válidos
- Armazene certificados de forma segura
- Rotacione certificados antes do vencimento
- Mantenha backup dos certificados

### Dados Sensíveis
- CNPJs são dados sensíveis - não exponha em logs públicos
- Proteja as credenciais do endpoint governamental
- Use HTTPS para todas as comunicações
- Implemente criptografia para dados em repouso

---

## Performance

### Otimizações Recomendadas

1. **Processamento assíncrono** - Para planilhas grandes, use filas
2. **Batch processing** - Envie XMLs em lotes ao governo
3. **Cache** - Mantenha cache dos dados consultados frequentemente
4. **Índices de banco** - Já implementados nas chaves estrangeiras
5. **Compressão** - Use compressão para arquivos grandes

### Limites Recomendados

- Tamanho máximo de planilha: 16 MB (configurado)
- Número máximo de XMLs por lote: 1000
- Timeout para envio ao governo: 60 segundos por XML
- Retenção de arquivos: 5 anos (conforme legislação)
