---
title: Início Rápido
description: Comece rapidamente com o Nous configurando a autenticação e fazendo suas primeiras chamadas de API
---

Agora que você tem o Nous instalado e rodando, este guia o guiará pela configuração inicial, criação do seu primeiro tenant e realização de chamadas de API.

## 1. Configuração Inicial

### Criar Super Admin
1. Navegue até o **Painel Web** em [http://localhost:5173](http://localhost:5173).
2. Como esta é sua primeira vez acessando o sistema, você será redirecionado automaticamente para a página de **Configuração**.
3. Crie sua conta de **Super Admin** fornecendo um e-mail e senha.

### Login
Assim que a conta de admin for criada, você será redirecionado para a página de login. Faça login com suas novas credenciais.

## 2. Criar um Tenant

Como Super Admin, seu papel principal é gerenciar tenants (organizações ou espaços de trabalho).

1. Após fazer login, você estará na página de **Gerenciamento de Tenants** (`/tenants`).
2. Clique no botão **"Create Tenant"** (Criar Tenant).
3. Preencha os detalhes para o novo tenant e seu administrador:
   - **Tenant Name** (Nome do Tenant) (ex: "Minha Organização")
   - **Admin Email** (E-mail do Admin) (para o admin do tenant)
   - **Admin Password** (Senha do Admin)
4. Clique em **Create Tenant**. Isso cria a organização e seu primeiro usuário administrador simultaneamente.

## 3. Gerar uma Chave de API

Para usar a API do Nous programaticamente, você precisa de uma chave de API.

1. **Faça Logout** da conta de Super Admin.
2. **Faça Login** usando as credenciais de **Admin do Tenant** que você acabou de criar (o e-mail e senha do passo 2).
3. Navegue até a seção **API Keys** (Chaves de API) (`/api-keys`) usando a barra lateral.
4. Clique em **"Create API Key"** (Criar Chave de API).
5. Dê um nome à sua chave (ex: "Chave de Desenvolvimento").
6. **Copie a chave imediatamente**. Você não poderá vê-la novamente.

## 4. Usar a API

Com sua Chave de API, você pode agora interagir com o cérebro do Nous. A API está disponível em `http://localhost:8000`.

### Assimilar Informações (Escrita)

O endpoint `assimilate` permite que você alimente texto no grafo de conhecimento. O Nous extrairá fatos e os associará a uma entidade identificada por um identificador externo (como e-mail).

```bash
curl -X POST "http://localhost:8000/api/v1/graph/entities/assimilate" \
  -H "X-API-Key: SUA_CHAVE_DE_API" \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": {
      "type": "email",
      "value": "alice@exemplo.com"
    },
    "content": "Alice é uma engenheira de software que mora em Nova York. Ela trabalha na TechCorp e adora fazer trilhas."
  }'
```

### Consultar Informações (Leitura)

O endpoint `lookup` permite recuperar informações da entidade usando um identificador (ex: e-mail, telefone).

```bash
curl -X GET "http://localhost:8000/api/v1/graph/entities/lookup?type=email&value=alice@exemplo.com" \
  -H "X-API-Key: SUA_CHAVE_DE_API"
```

Você também pode usar busca semântica com o parâmetro `rag_query`:

```bash
curl -X GET "http://localhost:8000/api/v1/graph/entities/lookup?type=email&value=alice@exemplo.com&rag_query=Onde%20a%20Alice%20trabalha" \
  -H "X-API-Key: SUA_CHAVE_DE_API"
```

### Explorar o Grafo

De volta ao Painel Web, você pode visualizar os dados que acabou de adicionar:
1. Vá para o **Graph Explorer** (Explorador de Grafo) (`/graph`).
2. Você deve ver nós representando "Alice", "TechCorp", "Nova York", etc., e os relacionamentos conectando-os.

## Próximos Passos

- Leia o [Guia de Implantação](/pt-br/getting-started/deployment/) para aprender como implantar o Nous em produção.
- Confira a [Documentação completa da API](http://localhost:8000/docs) (Swagger UI).
