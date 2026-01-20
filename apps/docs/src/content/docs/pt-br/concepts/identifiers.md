---
title: Identificadores
description: Handles externos que conectam o mundo real ao seu grafo de conhecimento
---

Um **Identificador** é um handle externo do mundo real que aponta para uma entidade no seu grafo de conhecimento. Exemplos incluem endereços de e-mail, números de telefone, nomes de usuário ou qualquer ID externo usado para referenciar um sujeito.

## O que é um Identificador?

Enquanto entidades usam UUIDs internos estáveis, o mundo real não funciona com UUIDs. As pessoas usam e-mails, números de telefone, nomes de usuário e outros identificadores. Identificadores preenchem essa lacuna — eles são os "endereços" externos que mapeiam para o seu sistema de entidade interno.

### Características Principais

- **Referências Externas**: Handles do mundo real como e-mails, telefones, nomes de usuário
- **Muitos-para-Um**: Múltiplos identificadores podem apontar para a mesma entidade
- **Valores Únicos**: Cada valor de identificador deve ser único em todo o sistema
- **Tipado**: Cada identificador tem um tipo (e-mail, telefone, nome de usuário, etc.)

## Propriedades do Identificador

| Propriedade | Tipo   | Obrigatório | Descrição                                        |
|-------------|--------|-------------|--------------------------------------------------|
| `value`     | string | Sim         | O valor do identificador (ex: "alice@exemplo.com") |
| `type`      | string | Sim         | Tipo de identificador (veja tipos suportados abaixo) |

### Tipos de Identificadores Suportados

O Nous valida tipos de identificadores para garantir consistência:

- `email` - Endereços de e-mail
- `phone` - Números de telefone
- `username` - Handles de nome de usuário
- `uuid` - UUIDs de sistemas externos
- `social_id` - Identificadores de mídia social

### Exemplo de Estrutura de Identificador

```json
{
  "value": "alice@exemplo.com",
  "type": "email"
}
```

## Por Que Usar Identificadores?

### O Problema da Resolução de Identidade

Considere estas interações:

1. **Segunda-feira**: Alguém envia um e-mail de `alice@empresa.com`
2. **Quarta-feira**: Você recebe uma ligação de `+1-555-0123`
3. **Sexta-feira**: Você recebe uma mensagem no Slack de `@alice.smith`

São três pessoas diferentes ou a mesma pessoa? Identificadores ajudam a resolver isso:

```
alice@empresa.com  ──┐
                     ├──> Entidade (UUID: 550e8400...)
+1-555-0123        ──┤
                     │
@alice.smith       ──┘
```

Todos os três identificadores apontam para a mesma entidade canônica.

### Benefícios

1. **Prevenir Perfis Duplicados**: Vincule novos identificadores a entidades existentes
2. **Consulta Flexível**: Encontre entidades usando qualquer identificador associado a elas
3. **Integração Multiplataforma**: Diferentes sistemas podem usar identificadores diferentes para a mesma entidade
4. **Rastreamento Histórico**: Mantenha identificadores antigos mesmo depois que alguém mudar seu e-mail ou telefone

## O Relacionamento HAS_IDENTIFIER

Identificadores se conectam a entidades através do relacionamento `HAS_IDENTIFIER`:

```
(Entity) -[HAS_IDENTIFIER]-> (Identifier)
```

### Propriedades do Relacionamento

| Propriedade          | Tipo     | Descrição                                |
|----------------------|----------|------------------------------------------|
| `from_entity_id`     | UUID     | A entidade que possui este identificador |
| `to_identifier_value`| string   | O identificador sendo conectado          |
| `is_primary`         | boolean  | Se este é o identificador primário       |
| `created_at`         | datetime | Quando este relacionamento foi estabelecido |

### Identificadores Primários

Você pode marcar um identificador como "primário" para servir como o padrão ou preferido para uma entidade:

```json
{
  "from_entity_id": "550e8400-e29b-41d4-a716-446655440000",
  "to_identifier_value": "alice@exemplo.com",
  "is_primary": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

Isso é útil para:
- Nomes de exibição em interfaces
- Métodos de contato padrão
- Priorizar identificadores quando múltiplos existem

## Trabalhando com Identificadores

### Consultando Entidades por Identificador

A operação mais comum é encontrar uma entidade usando um de seus identificadores:

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@exemplo.com
```

Isso retorna o perfil completo da entidade, incluindo:
- O UUID da entidade
- Todos os identificadores associados
- Todos os fatos
- Todas as fontes

### Adicionando Novos Identificadores

Quando você descobre um novo identificador para uma entidade existente, você pode vinculá-lo:

```bash
# Durante a assimilação, se o identificador já existir,
# o Nous adicionará fatos à entidade existente
POST /entities/assimilate
{
  "identifier": {
    "type": "phone",
    "value": "+1-555-0123"
  },
  "content": "Alice ligou para confirmar seu endereço em Paris."
}
```

Se `+1-555-0123` ainda não existir, isso o cria e potencialmente mescla com uma entidade existente (baseado na sua lógica de resolução de identidade).

### Validação de Identificador

O Nous valida identificadores para prevenir erros:

**Validação de Valor:**
- Não pode ser vazio ou conter apenas espaços em branco
- Automaticamente remove espaços no início/fim

**Validação de Tipo:**
- Deve ser um dos tipos suportados
- Tipos inválidos são rejeitados com um erro

## Casos de Uso

### 1. Suporte ao Cliente Multicanal

Rastreie um cliente através de canais:

```
cliente@email.com    ──┐
                       ├──> Entidade Cliente
+1-555-AJUDA         ──┤
                       │
@cliente_twitter     ──┘
```

Agentes de suporte podem buscar o cliente por qualquer identificador e ver o histórico completo de interação.

### 2. Migração de Usuário

Ao migrar usuários entre sistemas:

```
id_sistema_antigo: "12345"  ──┐
                              ├──> Entidade Usuário
id_sistema_novo: "uuid-..." ──┘
```

Mantenha ambos os identificadores vinculados durante o período de transição.

### 3. Exclusão Compatível com Privacidade

Quando um usuário solicita a exclusão do identificador (LGPD, etc.):
- Exclua o identificador específico
- Mantenha a entidade e outros identificadores intactos
- Mantenha a linhagem de dados sem o identificador excluído

## Melhores Práticas

### Sempre Use o Tipo Correto

Não armazene todos os identificadores como strings genéricas. Use o tipo apropriado:

```json
// Bom
{ "type": "email", "value": "alice@exemplo.com" }
{ "type": "phone", "value": "+1-555-0123" }

// Ruim
{ "type": "identifier", "value": "alice@exemplo.com" }
{ "type": "identifier", "value": "+1-555-0123" }
```

Isso permite:
- Validação no momento da criação
- Consulta específica por tipo
- Melhores análises e relatórios

### Normalize Valores Antes de Armazenar

Padronize valores de identificadores:

- **E-mails**: Minúsculas, sem espaços
- **Números de telefone**: Use formato E.164 (`+1-555-0123`)
- **Nomes de usuário**: Minúsculas, sem espaço em branco

Isso previne identificadores duplicados como `Alice@exemplo.com` e `alice@exemplo.com`.

### Use Flags Primárias com Sabedoria

Marque apenas um identificador como primário por entidade. Se precisar de múltiplos identificadores "preferidos":
- Use um identificador primário para exibição
- Armazene preferências em metadados da entidade ou como fatos

### Não Armazene Dados Sensíveis em Identificadores

Identificadores devem ser referências, não containers para informações sensíveis. Por exemplo:
- ✅ Armazene `identifier: "usuario123"`
- ❌ Não armazene `identifier: "cpf:123.456.789-00"`

Use fatos com medidas de segurança apropriadas para dados sensíveis.

## Estratégias de Resolução de Identidade

Quando você encontra um novo identificador, você enfrenta uma decisão chave: este identificador pertence a uma entidade existente ou a uma nova?

### Estratégia 1: Sempre Criar Novo

A abordagem mais simples — cada novo identificador cria uma nova entidade:

```
alice@trabalho.com    ──> Entidade A
alice@pessoal.com     ──> Entidade B
```

Mais tarde, você pode mesclar manualmente Entidade A e Entidade B se descobrir que são a mesma pessoa.

### Estratégia 2: Correspondência Baseada em Regras

Use lógica de negócios para vincular identificadores:
- Mesmo domínio de e-mail + mesmo primeiro nome → mesma entidade
- Mesmo número de telefone → mesma entidade
- Confirmação explícita do usuário → mesma entidade

### Estratégia 3: API de Vinculação Explícita

Forneça uma API para vincular identificadores manualmente:

```bash
POST /entities/{entity_id}/identifiers
{
  "type": "email",
  "value": "alice@pessoal.com",
  "is_primary": false
}
```

Isso lhe dá controle total sobre a resolução de identidade.

## Perguntas Comuns

### Duas entidades podem compartilhar o mesmo identificador?

Não. Cada valor de identificador deve ser único em todo o sistema. Isso garante consultas determinísticas — dado um identificador, você sempre pode encontrar exatamente uma entidade.

### O que acontece se eu tentar criar um identificador duplicado?

O sistema rejeitará com um erro de validação. Você deve primeiro verificar se o identificador existe e vincular a essa entidade se apropriado.

### Posso mudar o valor de um identificador?

Identificadores são feitos para serem referências imutáveis. Se o e-mail de alguém mudar, não atualize o identificador — em vez disso:
1. Crie um novo identificador com o novo e-mail
2. Opcionalmente marque-o como primário
3. Mantenha o identificador antigo para referência histórica

### Como lido com identificadores temporários?

Para identificadores temporários (IDs de sessão, tokens de uso único), considere:
- Usar um mecanismo de armazenamento diferente (cache, session store)
- Usar fatos com metadados de expiração
- Apenas criar identificadores para referências persistentes e de longa duração

## Conceitos Relacionados

- [Entidades](/pt-br/concepts/entities) - O sujeito canônico para o qual identificadores apontam
- [Fatos](/pt-br/concepts/facts) - Conhecimento associado a entidades
- [Visão Geral](/pt-br/concepts/overview) - Como todos os conceitos se encaixam
