# API de Envio de DARF - EFD-Reinf

Bem-vindo à **API de Envio de DARF - EFD-Reinf**, uma solução robusta para automatizar o envio de DARF por meio da conversão de planilhas no formato XLSX para XML, assinatura digital e organização dos dados no padrão EFD-Reinf.

---

## Sumário

- [Introdução](#introdução)
- [Configuração do Ambiente](#configuração-do-ambiente)
  - [Certificados Digitais](#certificados-digitais)
  - [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Autenticação](#autenticação)
- [Documentação](#documentação)
- [Execução com Docker](#execução-com-docker)
- [Futuras Funcionalidades](#futuras-funcionalides)

---

## Introdução

A API foi desenvolvida para atender às necessidades de automação no envio de informações fiscais por meio da geração de XMLs no formato exigido pela Receita Federal. Seu fluxo abrange:

1. Upload de planilhas do SIAFI.
2. Processamento e conversão de cada linha em XML.
3. Download dos XMLs gerados.
4. Upload dos XMLs assinados.
5. Envio dos XMLs assinados.
6. Possibilidade de listar e deletar arquivos gerados.
### Fluxograma
![fluxograma de funcionamento do algoritmo](<Processo Automação EFD-REINF.png>)
---

## Configuração do Ambiente

### Certificados Digitais

Para garantir o funcionamento adequado da API e o cumprimento das exigências do EFD-Reinf, é obrigatório o uso de certificados digitais válidos. Certifique-se de que:

- O certificado esteja no formato `.pfx`.

Caso não possua um certificado, entre em contato com o suporte responsável pela emissão.

---

### Variáveis de Ambiente

A configuração da API é gerenciada por um arquivo `.env` na raiz do projeto. Crie ou edite este arquivo para incluir as seguintes variáveis:

```.env
# Configurações principais

POSTGRES_DB=nome_do_banco_de_dados
POSTGRES_PASSWORD=senha_do_banco
FLASK_ENV=development
DEV_DATABASE_URL=postgresql+psycopg2://user:senha@postgres:5432/nome_do_banco_de_dados
SECRET_KEY=secret_key
ENDPOINT_URL=https://pre-reinf.receita.economia.gov.br/recepcao/lotes
```
## Autenticação

A API utiliza Bearer Token como mecanismo de autenticação. Para acessar as rotas protegidas, inclua o token no cabeçalho das requisições:
```http
Authorization: Bearer <seu_token>
```
Caso o token não seja fornecido ou seja inválido, a API retornará um erro 401 Unauthorized.
Documentação
## Documentação
Toda a documentação detalhada das rotas está disponível no arquivo APIEnvioReinf.json, localizado na raiz do projeto. Este arquivo pode ser importado diretamente no Postman ou em outras ferramentas para facilitar a interação com a API.
Para importar no Postman:

    Abra o Postman.
    Clique em Import.
    Selecione o arquivo APIEnvioReinf.json.
    Pronto! Agora você tem acesso a todas as rotas com exemplos de uso.

## Execução com Docker

A aplicação está dockerizada, permitindo fácil configuração e execução em qualquer ambiente que suporte Docker. Certifique-se de ter o Docker e o Docker Compose instalados no sistema.
Passos para execução:

1. Clone o repositório do projeto:
```bash
    git clone https://code.dadm.mb/dadm/EFDReinfSender.git
    cd EFDREINFSENDER
```

2. Construa e inicie os contêineres:
```bash
docker build -t nome_da_imagem .
docker compose up
```

3. Acesse a API:

    A aplicação estará disponível no endereço http://127.0.0.1:5000 (ou outro definido nas variáveis de ambiente).

4. Parar os contêineres:

Para interromper a execução, utilize:
```bash
    docker-compose down
```

### Criando Tabelas com Alembic

Após inicializar os contêineres, é necessário criar as tabelas no banco de dados utilizando o Alembic, a ferramenta de migração usada pela API. Siga os passos abaixo:

1. Acesse o contêiner da aplicação:
    ```bash
    docker exec -it nome_do_container bash
    ```
    Substitua nome_do_container pelo nome ou ID do contêiner do aplicativo, que pode ser obtido com o comando docker ps.

#### Execute as migrações do Alembic:

1. Modifique o o arquivo alembic.ini:

```bash
    sqlalchemy.url = postgresql://user:senha@postgres:5432/database
```
2. execute o comando abaixo:
    ```bash
    alembic upgrade head
    ```
    Isso aplicará todas as migrações disponíveis, criando as tabelas necessárias no banco de dados.

3. Verifique as tabelas criadas:

    Confirme que as tabelas foram criadas acessando o banco de dados com uma ferramenta como pgAdmin ou diretamente no terminal do contêiner PostgreSQL.


# Futuras Funcionalides

1. Possibilidade de editar os dados dos XMLs
2. Automatização da assinatura
3. Captura de certificados do usuario

# Observação:

Certifique-se de mapear corretamente os volumes e configurar as permissões de acesso ao certificado digital e aos arquivos de entrada/saída, se necessário.

