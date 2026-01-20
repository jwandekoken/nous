---
title: Visão Geral
description: Entendendo os quatro conceitos principais que impulsionam o Nous
---

O Nous é construído em torno de quatro conceitos fundamentais que trabalham juntos para criar um grafo de conhecimento flexível e rastreável. Entender esses conceitos é essencial para usar o Nous de forma eficaz.

## Os Quatro Conceitos Principais

### 1. Entidade (Entity)

A **Entidade** é o ponto de ancoragem canônico no seu grafo de conhecimento. Ela representa um sujeito do mundo real — uma pessoa, organização, conceito ou qualquer sujeito central sobre o qual você deseja lembrar fatos.

- **Identidade Estável**: Cada entidade tem um UUID único que nunca muda
- **Agnóstico a Identificadores**: A entidade existe independentemente de identificadores externos
- **Hub Central**: Todos os fatos e identificadores se conectam à entidade

[Saiba mais sobre Entidades →](/pt-br/concepts/entities)

### 2. Identificador (Identifier)

Um **Identificador** é um handle externo do mundo real que aponta para uma entidade. Exemplos incluem endereços de e-mail, números de telefone, nomes de usuário ou qualquer ID externo.

- **Múltiplos Por Entidade**: Uma única entidade pode ter muitos identificadores
- **Evita Duplicatas**: Ajuda a resolver a identidade através de diferentes fontes
- **Mapeamento do Mundo Real**: Conecta sua entidade interna a sistemas externos

[Saiba mais sobre Identificadores →](/pt-br/concepts/identifiers)

### 3. Fato (Fact)

Um **Fato** é uma peça discreta de conhecimento associada a uma entidade. Fatos podem representar localizações, empresas, habilidades, relacionamentos ou qualquer informação nomeada.

- **Contexto Semântico**: Cada fato possui um verbo descrevendo o relacionamento (ex: "mora_em", "trabalha_na")
- **Pontuações de Confiança**: Rastreia níveis de certeza para cada fato
- **Reutilizável**: Múltiplas entidades podem compartilhar o mesmo fato (ex: "Localização:Paris")

[Saiba mais sobre Fatos →](/pt-br/concepts/facts)

### 4. Fonte (Source)

Uma **Fonte** representa a origem da informação — uma mensagem de chat, e-mail, documento ou qualquer conteúdo do qual os fatos foram extraídos.

- **Rastreamento de Proveniência**: Cada fato remete à sua fonte
- **Auditabilidade**: Saiba exatamente de onde veio cada peça de informação
- **Contexto Temporal**: Fontes capturam o timestamp do mundo real dos eventos

[Saiba mais sobre Fontes →](/pt-br/concepts/sources)

## Como Eles se Conectam

Os quatro conceitos formam uma estrutura de grafo conectada:

```
┌─────────────┐
│  Entidade   │ (Sujeito canônico com UUID estável)
└─────┬───┬───┘
      │   │
      │   └──────────────────┐
      │                      │
      ▼                      ▼
┌─────────────┐        ┌─────────────┐
│Identificador│        │    Fato     │
│             │        │             │
│ HAS_        │        │ HAS_FACT    │
│ IDENTIFIER  │        │relationship │
└─────────────┘        └──────┬──────┘
                              │
                              │ DERIVED_FROM
                              │
                              ▼
                        ┌─────────────┐
                        │    Fonte    │
                        └─────────────┘
```

### Relacionamentos Chave

1. **Entidade → Identificador** (`HAS_IDENTIFIER`)
   - Uma entidade pode ter múltiplos identificadores
   - Um identificador pode ser marcado como primário

2. **Entidade → Fato** (`HAS_FACT`)
   - Vincula uma entidade ao conhecimento sobre ela
   - Inclui um verbo e pontuação de confiança

3. **Fato → Fonte** (`DERIVED_FROM`)
   - Rastreia cada fato de volta à sua origem
   - Garante proveniência e rastreabilidade dos dados

## Princípios de Design

### Resolução de Identidade

Ao separar a **Entidade** canônica de seus **Identificadores** externos, o Nous evita perfis duplicados. Quando você encontra um novo identificador (como um segundo e-mail para a mesma pessoa), você pode vinculá-lo à entidade existente em vez de criar uma duplicata.

### Rastreabilidade

Cada fato no Nous pode responder à pergunta: "Como sabemos isso?". O relacionamento `DERIVED_FROM` garante a proveniência completa dos dados, do fato à fonte.

### Consciência Temporal

O Nous distingue entre dois tipos de tempo:
- **Tempo do Evento** (`Source.timestamp`): Quando algo realmente aconteceu no mundo real
- **Tempo do Sistema** (`created_at`): Quando foi registrado no Nous

Isso permite consultas contextuais precisas juntamente com auditoria do sistema.

## Referência Rápida

| Conceito     | Chave Primária | Propósito                         |
|--------------|----------------|-----------------------------------|
| Entidade     | UUID           | Âncora canônica para toda informação |
| Identificador| valor          | Handle externo para encontrar uma entidade |
| Fato         | fact_id        | Peça discreta de conhecimento     |
| Fonte        | UUID           | Origem da informação              |

## Próximos Passos

Pronto para mergulhar mais fundo? Comece com [Entidades](/pt-br/concepts/entities) para entender a fundação do grafo de conhecimento.
