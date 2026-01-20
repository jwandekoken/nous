---
title: Entidades
description: O ponto de ancoragem canônico para todo o conhecimento no Nous
---

Uma **Entidade** é o sujeito central no seu grafo de conhecimento. Ela representa uma entidade do mundo real — uma pessoa, organização, conceito ou qualquer assunto sobre o qual você deseja lembrar informações.

## O que é uma Entidade?

Pense em uma entidade como o "perfil" ou "identidade" canônica para um sujeito no seu sistema. Ao contrário de bancos de dados tradicionais onde você pode identificar um usuário pelo seu e-mail, o Nous usa um UUID estável que nunca muda — mesmo se todas as informações de contato da pessoa mudarem.

### Características Principais

- **Identidade Estável**: Cada entidade possui um UUID único que persiste para sempre
- **Agnóstico a Identificadores**: A entidade existe independentemente de identificadores externos como e-mails ou nomes de usuário
- **Hub de Relacionamentos**: Todos os fatos e identificadores se conectam através da entidade
- **Metadados Flexíveis**: Pode armazenar informações semi-estruturadas adicionais conforme necessário

## Propriedades da Entidade

| Propriedade  | Tipo                 | Descrição                                      |
|--------------|----------------------|------------------------------------------------|
| `id`         | UUID                 | Identificador único do sistema, gerado automaticamente |
| `created_at` | datetime             | Quando esta entidade foi criada no sistema     |
| `metadata`   | dict[str, str] ou {} | Pares chave-valor flexíveis para dados adicionais |

### Exemplo de Estrutura de Entidade

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-15T10:30:00Z",
  "metadata": {
    "type": "person",
    "source_system": "crm"
  }
}
```

## Por Que Separar Entidades de Identificadores?

Uma pergunta comum: por que não usar apenas um endereço de e-mail como chave primária?

### O Problema com Identificadores Externos

Considere este cenário:
1. Alice se cadastra com `alice@empresa.com`
2. Ela muda de emprego e começa a usar `alice@novaempresa.com`
3. Ela também tem um e-mail pessoal `alice.smith@gmail.com`
4. Você recebe uma mensagem do número de telefone dela `+1-555-0123`

**Sem entidades**: Você pode criar 4 perfis separados, fragmentando as informações da Alice.

**Com entidades**: Todos os quatro identificadores apontam para o mesmo UUID de entidade canônico. O histórico completo dela permanece conectado.

### Benefícios do Design Baseado em Entidades

1. **Resolução de Identidade**: Mescle perfis quando descobrir que dois identificadores pertencem à mesma pessoa
2. **À Prova de Futuro**: Novos tipos de identificadores (nomes de usuário em redes sociais, endereços cripto) podem ser adicionados sem alterações no esquema
3. **Integração entre Sistemas**: Diferentes sistemas podem usar identificadores diferentes enquanto referenciam a mesma entidade
4. **Amigável à Privacidade**: O UUID da entidade pode persistir mesmo se identificadores externos forem excluídos

## Ciclo de Vida da Entidade

### 1. Criação

Entidades são tipicamente criadas durante o processo de **assimilação** quando você encontra um novo identificador pela primeira vez:

```bash
POST /entities/assimilate
{
  "identifier": {
    "type": "email",
    "value": "alice@exemplo.com"
  },
  "content": "Alice mudou-se para Paris e começou a trabalhar na Acme Corp."
}
```

Isso irá:
- Criar uma nova entidade com um UUID único
- Vincular o identificador `alice@exemplo.com` à entidade
- Extrair e associar fatos com a entidade

### 2. Lookup (Consulta)

Recupere uma entidade e todos os seus dados associados usando qualquer um dos seus identificadores:

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@exemplo.com
```

Retorna a entidade com todos os identificadores, fatos e fontes.

### 3. Atualização

Entidades em si são imutáveis (o UUID nunca muda), mas você pode:
- Adicionar novos identificadores a uma entidade
- Adicionar novos fatos a uma entidade
- Atualizar campos de metadados

## Relacionamentos da Entidade

### Possui Identificadores (Has Identifiers)

Uma entidade se conecta aos seus identificadores externos através de relacionamentos `HAS_IDENTIFIER`:

```
(Entity) -[HAS_IDENTIFIER]-> (Identifier)
```

**Propriedades do Relacionamento:**
- `is_primary`: Flag booleana marcando o identificador primário
- `created_at`: Quando o identificador foi vinculado

### Possui Fatos (Has Facts)

Uma entidade se conecta ao conhecimento sobre si mesma através de relacionamentos `HAS_FACT`:

```
(Entity) -[HAS_FACT]-> (Fact)
```

**Propriedades do Relacionamento:**
- `verb`: Relacionamento semântico (ex: "mora_em", "trabalha_na")
- `confidence_score`: Nível de confiança (0.0 a 1.0)
- `created_at`: Quando o fato foi vinculado

[Saiba mais sobre Fatos →](/pt-br/concepts/facts)

## Casos de Uso

### 1. Perfis de Clientes

Rastreie um cliente através de múltiplos pontos de contato:
- Conversas por e-mail
- Chamadas de suporte por telefone
- Interações em redes sociais
- Comportamento no aplicativo

Tudo unificado sob um único UUID de entidade.

### 2. Memória de Agente de IA

Dê ao seu agente de IA uma memória persistente dos usuários:
- Lembrar preferências entre sessões
- Manter histórico de conversas
- Construir contexto ao longo do tempo

### 3. Bases de Conhecimento de Pesquisa

Rastreie entidades em pesquisas:
- Organizações e seus relacionamentos
- Pessoas e suas afiliações
- Conceitos e suas conexões

## Melhores Práticas

### Use Metadados com Moderação

O campo `metadata` é flexível, mas abusar dele pode dificultar consultas. Reserve-o para:
- Dados de integração de sistema (ex: `source_system: "salesforce"`)
- Dicas leves de tipo (ex: `entity_type: "organization"`)

Armazene dados estruturados como Fatos.

### Não Reutilize UUIDs de Entidade

Uma vez criado um UUID de entidade, nunca o reutilize para um assunto diferente. Se precisar mesclar entidades, crie uma nova entidade e migre os relacionamentos.

### Use Identificadores Primários

Marque um identificador como `is_primary` para servir como o nome de exibição padrão ou método de contato para a entidade.

## Perguntas Comuns

### Posso criar uma entidade sem um identificador?

Tecnicamente sim, mas não é recomendado. Entidades sem identificadores são inalcançáveis através da API de lookup padrão. Sempre vincule pelo menos um identificador ao criar uma entidade.

### Entidades podem ter relacionamentos com outras entidades?

Não diretamente no esquema atual. Relacionamentos entidade-para-entidade podem ser modelados através de fatos compartilhados ou criando tipos de fatos personalizados que referenciam outras entidades.

### Como faço para excluir uma entidade?

O Nous atualmente foca em operações de escrita e leitura. A exclusão de entidades exigiria a exclusão em cascata de todos os identificadores, fatos e relacionamentos relacionados — algo a ser implementado cuidadosamente com base em suas políticas de retenção de dados.

## Conceitos Relacionados

- [Identificadores](/pt-br/concepts/identifiers) - Handles externos que apontam para entidades
- [Fatos](/pt-br/concepts/facts) - Conhecimento associado a entidades
- [Fontes](/pt-br/concepts/sources) - Origem da informação sobre entidades
