---
title: Implantação
description: Implante o Nous em produção
---

> **Apenas começando?** Veja o [Guia de Instalação](/pt-br/getting-started/installation/) para configuração de desenvolvimento local.

Este guia cobre a implantação do Nous em um ambiente de produção usando Docker Compose.

## Modos de Implantação

O Nous suporta dois modos de implantação:

| Modo | Caso de Uso |
|------|-------------|
| **Standalone** | Servidores novos — inclui um proxy reverso Caddy empacotado com HTTPS automático |
| **Proxy Reverso Próprio (BYO)** | Servidores com Caddy, Nginx ou Traefik existentes — apenas serviços principais |

## Pré-requisitos

- Um servidor com Docker e Docker Compose instalados
- Um nome de domínio (para HTTPS no modo standalone)
- Uma chave de API do Google para embeddings

## Configuração

### 1. Clone o Repositório

```bash
git clone https://github.com/jwandekoken/nous.git
cd nous
```

### 2. Crie Seu Arquivo de Ambiente

```bash
cp .env.example .env
```

### 3. Configure as Variáveis de Ambiente

Edite `.env` com seus valores de produção:

```bash
# Obrigatório — gere com: openssl rand -hex 32
SECRET_KEY=sua-chave-secreta-aqui

# Obrigatório para embeddings e extração de fatos
GOOGLE_API_KEY=sua-google-api-key

# Credenciais do banco de dados (mude dos padrões)
POSTGRES_PASSWORD=sua-senha-segura

# Para modo standalone com HTTPS
DOMAIN=seudominio.com
```

## Opção A: Implantação Standalone

Use isso se você não tiver um proxy reverso existente. O Caddy lidará com os certificados SSL automaticamente via Let's Encrypt.

### Inicie Todos os Serviços

```bash
docker compose -f docker-compose.prod.yml --profile with-proxy up -d --build
```

Sua aplicação estará disponível em:
- `http://localhost` (se nenhum domínio for configurado)
- `https://seudominio.com` (se `DOMAIN` estiver definido)

## Opção B: Proxy Reverso Próprio (BYO)

Use isso se você já tiver um proxy reverso (Caddy, Nginx, Traefik) rodando em seu servidor.

### Inicie os Serviços Principais

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Isso inicia os bancos de dados, API e frontend web — mas nenhum proxy reverso.

### Conecte Seu Proxy Reverso

Seu proxy reverso precisa se conectar à rede Docker `nous-net` para alcançar os serviços internos.

**Passo 1:** Adicione a rede ao `docker-compose.yml` do seu proxy reverso:

```yaml
networks:
  nous_nous-net:
    external: true

services:
  caddy:  # ou nginx, traefik, etc.
    networks:
      - sua-rede-existente
      - nous_nous-net
```

**Passo 2:** Adicione regras de roteamento. Exemplo para Caddy:

```caddyfile
nous.seudominio.com {
    handle /api/* {
        reverse_proxy nous_api:8000
    }
    handle {
        reverse_proxy nous_web:80
    }
}
```

**Passo 3:** Recarregue seu proxy reverso:

```bash
docker exec seu-container-caddy caddy reload --config /etc/caddy/Caddyfile
```

## Arquitetura de Serviços

| Serviço | Container | Porta (Interna) | Descrição |
|---------|-----------|-----------------|-----------|
| db | postgres_age | 5432 | PostgreSQL com Apache AGE (armazenamento de grafo) |
| qdrant | qdrant | 6333 | Banco de dados vetorial (busca semântica) |
| api | nous_api | 8000 | Backend FastAPI |
| web | nous_web | 80 | Frontend estático Vue.js |
| reverse-proxy | nous_proxy | 80, 443 | Caddy (apenas modo standalone) |

## Gerenciando Sua Implantação

### Ver Logs

```bash
# Todos os serviços
docker compose -f docker-compose.prod.yml logs -f

# Serviço específico
docker compose -f docker-compose.prod.yml logs -f api
```

### Parar Serviços

```bash
docker compose -f docker-compose.prod.yml down
```

### Atualizar para a Versão Mais Recente

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Referência Rápida

| Comando | Descrição |
|---------|-----------|
| `docker compose -f docker-compose.prod.yml up -d --build` | Inicia serviços principais (proxy BYO) |
| `docker compose -f docker-compose.prod.yml --profile with-proxy up -d --build` | Inicia com Caddy empacotado |
| `docker compose -f docker-compose.prod.yml down` | Para todos os serviços |
| `docker compose -f docker-compose.prod.yml logs -f` | Vê logs |
| `docker compose -f docker-compose.prod.yml ps` | Verifica status do serviço |

## Solução de Problemas

### Containers Não Iniciam

1. Verifique os logs: `docker compose -f docker-compose.prod.yml logs`
2. Verifique se o arquivo `.env` existe e tem as variáveis obrigatórias
3. Garanta que as portas 80/443 não estejam em uso (modo standalone)

### Problemas de Conexão com Banco de Dados

1. Verifique a saúde do banco: `docker compose -f docker-compose.prod.yml ps`
2. Veja logs do banco: `docker compose -f docker-compose.prod.yml logs db`
3. Verifique se `POSTGRES_PASSWORD` corresponde no seu `.env`

### Problemas com Certificado SSL (Standalone)

1. Garanta que o DNS do seu domínio aponte para seu servidor
2. Verifique logs do Caddy: `docker compose -f docker-compose.prod.yml logs reverse-proxy`
3. Verifique se a porta 443 está acessível da internet

### API Retorna 502 Bad Gateway

1. Verifique se o container da API está rodando: `docker compose -f docker-compose.prod.yml ps api`
2. Veja logs da API para erros: `docker compose -f docker-compose.prod.yml logs api`
3. Garanta que as migrações de banco de dados tenham rodado com sucesso
