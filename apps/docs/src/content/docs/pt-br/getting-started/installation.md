---
title: Instalação
description: Como instalar e configurar o Nous para desenvolvimento local
---

> **Procurando implantar em produção?** Vá para o [Guia de Implantação](/pt-br/getting-started/deployment/).

Este guia ajudará você a executar o Nous localmente para desenvolvimento e testes.

## Pré-requisitos

Antes de começar, certifique-se de ter as seguintes ferramentas instaladas:

| Ferramenta | Versão | Propósito |
|------------|--------|-----------|
| [Node.js](https://nodejs.org/) | 24.11.0+ | Runtime JavaScript (recomendamos [nvm](https://github.com/nvm-sh/nvm)) |
| [pnpm](https://pnpm.io/installation) | Mais recente | Gerenciador de pacotes JavaScript |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Mais recente | Gerenciador de pacotes Python |
| [Docker](https://docs.docker.com/get-docker/) | Mais recente | Runtime de container para bancos de dados |

## Início Rápido

### 1. Clone e Instale as Dependências

```bash
git clone https://github.com/jwandekoken/nous.git
cd nous
pnpm install
```

### 2. Configure o Ambiente Python

```bash
cd apps/api
uv venv
uv sync
cd ../..
```

### 3. Configure as Variáveis de Ambiente

```bash
cp apps/api/.env.example apps/api/.env
```

Edite `apps/api/.env` com sua configuração:

```bash
# Necessário para extração de fatos e embeddings
GOOGLE_API_KEY=sua-google-api-key
```

### 4. Inicie os Bancos de Dados

O Nous requer dois bancos de dados:
- **PostgreSQL + Apache AGE** — Armazenamento em grafo para entidades e relacionamentos
- **Qdrant** — Armazenamento vetorial para busca semântica

```bash
docker compose up -d
```

### 5. Execute as Migrações de Banco de Dados

```bash
cd apps/api
uv run alembic upgrade head
cd ../..
```

### 6. Inicie os Servidores de Desenvolvimento

```bash
pnpm turbo dev
```

Isso inicia ambos os serviços:
- **API** em `http://localhost:8000`
- **Painel Web** em `http://localhost:5173`

## Verifique Sua Instalação

Assim que tudo estiver rodando, você pode verificar a instalação:

**1. Verifique o endpoint de saúde:**

```bash
curl http://localhost:8000/health
```

Você deve ver: `{"status":"healthy"}`

**2. Visualize os serviços:**
- **Documentação da API**: http://localhost:8000/docs
- **Painel Web**: http://localhost:5173

**3. Próximo:** Siga o [Guia de Início Rápido](/pt-br/getting-started/quickstart/) para configurar a autenticação e começar a usar a API.

## Solução de Problemas

### Porta Já em Uso

Se você vir `port is already allocated`, outro serviço está usando a porta (comumente PostgreSQL na 5432). Pare esse serviço ou modifique o mapeamento da porta no `docker-compose.yml` (por exemplo, altere `"5432:5432"` para `"5433:5432"`).

### Falha na Conexão com o Banco de Dados

1. Verifique se os containers estão rodando: `docker compose ps`
2. Veja os logs do banco de dados: `docker compose logs db`
3. Verifique se sua configuração no `.env` corresponde às credenciais do banco de dados

### Hot Reload Não Funciona

Certifique-se de que você está executando `pnpm turbo dev` da raiz do repositório. Verifique também se o limite de file watchers do seu sistema foi atingido (comum no Linux).

## Próximos Passos

Agora que o Nous está rodando localmente, você pode:
- Explorar a API em http://localhost:8000/docs
- Visualizar seu grafo de conhecimento no Painel Web
- Ler sobre [Implantação](/pt-br/getting-started/deployment/) quando estiver pronto para produção
