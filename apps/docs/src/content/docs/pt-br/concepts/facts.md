---
title: Fatos
description: Peças discretas de conhecimento que alimentam seu grafo de conhecimento
---

Um **Fato** representa uma peça discreta de conhecimento ou uma entidade nomeada no seu grafo de conhecimento. Fatos podem ser localizações (Paris), empresas (Acme Corp), habilidades (Python), relacionamentos ou qualquer peça estruturada de informação sobre uma entidade.

## O que é um Fato?

Fatos são os "átomos de conhecimento" no Nous — pequenas peças reutilizáveis de informação que podem ser associadas a entidades. Ao contrário de notas não estruturadas, fatos são estruturados e semânticos, tornando-os consultáveis e analisáveis.

### Características Principais

- **Discreto**: Cada fato representa uma peça de conhecimento
- **Tipado**: Cada fato tem uma categoria (Localização, Empresa, Habilidade, etc.)
- **Reutilizável**: Múltiplas entidades podem compartilhar o mesmo fato
- **Rastreável**: Cada fato remete à sua fonte

## Propriedades do Fato

| Propriedade | Tipo   | Obrigatório | Descrição                                        |
|-------------|--------|-------------|--------------------------------------------------|
| `name`      | string | Sim         | O valor do fato (ex: "Paris", "Python")          |
| `type`      | string | Sim         | A categoria (ex: "Localização", "Habilidade")    |
| `fact_id`   | string | Auto        | Chave sintética combinando tipo e nome           |

### A Chave Sintética fact_id

Fatos usam uma chave composta em vez de um UUID:

```
fact_id = "{type}:{name}"
```

**Exemplos:**
- `Location:Paris`
- `Company:Acme Corp`
- `Skill:Python`
- `Hobby:Photography`

Este design permite que o mesmo fato seja reutilizado em múltiplas entidades. Se 100 pessoas moram em Paris, todas referenciam o mesmo nó de fato `Location:Paris` em vez de criar 100 nós de fatos duplicados.

### Exemplo de Estrutura de Fato

```json
{
  "name": "Paris",
  "type": "Location",
  "fact_id": "Location:Paris"
}
```

## O Relacionamento HAS_FACT

Fatos se conectam a entidades através do relacionamento `HAS_FACT`, que fornece contexto semântico:

```
(Entity) -[HAS_FACT]-> (Fact)
```

### Propriedades do Relacionamento

| Propriedade       | Tipo     | Descrição                                      |
|-------------------|----------|------------------------------------------------|
| `from_entity_id`  | UUID     | A entidade que possui este fato                |
| `to_fact_id`      | string   | O fato sendo conectado                         |
| `verb`            | string   | Relacionamento semântico (ex: "lives_in")      |
| `confidence_score`| float    | Nível de confiança (0.0 a 1.0)                 |
| `created_at`      | datetime | Quando este relacionamento foi estabelecido    |

### O Verbo: Contexto Semântico

A propriedade `verb` é crucial — ela descreve COMO a entidade se relaciona com o fato:

```json
// Alice mora em Paris
{
  "from_entity_id": "uuid-alice",
  "to_fact_id": "Location:Paris",
  "verb": "lives_in",
  "confidence_score": 0.95
}

// Alice trabalha na Acme Corp
{
  "from_entity_id": "uuid-alice",
  "to_fact_id": "Company:Acme Corp",
  "verb": "works_at",
  "confidence_score": 1.0
}

// Alice sabe Python
{
  "from_entity_id": "uuid-alice",
  "to_fact_id": "Skill:Python",
  "verb": "knows",
  "confidence_score": 0.8
}
```

O mesmo fato (`Location:Paris`) pode ter verbos diferentes dependendo do relacionamento:
- `lives_in` - Residência da pessoa
- `visited` - Viagem passada
- `born_in` - Local de nascimento
- `wants_to_visit` - Intenção futura

### Pontuações de Confiança

Cada fato tem uma pontuação de confiança de 0.0 a 1.0, representando quão certo você está sobre a informação:

| Faixa de Pontuação | Significado            | Caso de Uso                           |
|--------------------|------------------------|---------------------------------------|
| 0.9 - 1.0          | Confiança Muito Alta   | Informação verificada, registros oficiais |
| 0.7 - 0.9          | Confiança Alta         | Declarações claras, fontes confiáveis |
| 0.5 - 0.7          | Confiança Moderada     | Informação implícita, fontes indiretas |
| 0.3 - 0.5          | Confiança Baixa        | Incerto, requer verificação           |
| 0.0 - 0.3          | Confiança Muito Baixa  | Especulação, rumores, sinais fracos   |

**Exemplo:**

```python
# Declaração direta: "Eu moro em Paris"
confidence_score = 1.0

# Informação implícita: "Eu amo os croissants aqui em Paris"
confidence_score = 0.85

# Pouco claro: "Eu talvez me mude para Paris ano que vem"
confidence_score = 0.4
```

## Extração de Fatos

Fatos são tipicamente extraídos automaticamente de texto não estruturado durante o processo de assimilação:

### Texto de Entrada
```
"Alice se mudou para Paris mês passado e começou a trabalhar na Acme Corp como Engenheira Sênior."
```

### Fatos Extraídos

```json
[
  {
    "name": "Paris",
    "type": "Location",
    "fact_id": "Location:Paris",
    "verb": "lives_in",
    "confidence_score": 0.95
  },
  {
    "name": "Acme Corp",
    "type": "Company",
    "fact_id": "Company:Acme Corp",
    "verb": "works_at",
    "confidence_score": 0.95
  },
  {
    "name": "Engenheira Sênior",
    "type": "JobTitle",
    "fact_id": "JobTitle:Engenheira Sênior",
    "verb": "has_title",
    "confidence_score": 0.95
  }
]
```

## Reutilização de Fatos

Uma das características mais poderosas dos fatos é a reutilização. Considere:

```
Alice -[lives_in]-> Location:Paris
Bob   -[lives_in]-> Location:Paris
Carol -[visited]->  Location:Paris
```

Todas as três pessoas referenciam o mesmo nó de fato `Location:Paris`. Isso permite:

1. **Armazenamento Eficiente**: Um nó de fato, muitos relacionamentos
2. **Consultas Ricas**: "Encontre todas as entidades morando em Paris"
3. **Análise de Rede**: Entenda conexões através de fatos compartilhados
4. **Consistência**: Atualize "Paris" em um lugar

## Tipos de Fatos Comuns

Embora o Nous não restrinja tipos de fatos, aqui estão categorias comuns:

| Tipo         | Exemplos                          | Verbos Comuns                   |
|--------------|-----------------------------------|---------------------------------|
| Location     | Paris, Nova York, Tóquio          | lives_in, visited, born_in      |
| Company      | Acme Corp, Google, Microsoft      | works_at, worked_at, founded    |
| Skill        | Python, JavaScript, Design        | knows, learning, expert_in      |
| JobTitle     | Engenheiro, Gerente, Designer     | has_title, had_title            |
| Hobby        | Fotografia, Caminhada, Jogos      | enjoys, practices               |
| Interest     | IA, Blockchain, Mudanças Climáticas| interested_in, researching     |
| Person       | João Silva, Maria Oliveira        | knows, reports_to, friends_with |
| Product      | iPhone, Tesla Model 3             | owns, uses, developing          |

## Casos de Uso

### 1. Memória de IA Pessoal

Rastreie o que a IA aprende sobre os usuários:

```
Entidade Usuário:
  -[lives_in]-> Location:São Francisco
  -[works_at]-> Company:Startup XYZ
  -[knows]-> Skill:Python
  -[interested_in]-> Interest:IA
```

A IA pode recordar: "Você mora em São Francisco, trabalha na Startup XYZ, sabe Python e está interessado em IA."

### 2. Rede Organizacional

Mapeie relacionamentos entre pessoas e organizações:

```
Alice -[works_at]-> Company:Acme Corp
Bob   -[works_at]-> Company:Acme Corp
Carol -[worked_at]-> Company:Acme Corp (confiança: 0.7)
```

Consulta: "Quem trabalha atualmente na Acme Corp?" (filtre por verb="works_at" e alta confiança)

### 3. Inventário de Habilidades

Rastreie capacidades da equipe:

```
Alice -[expert_in]-> Skill:Python (confiança: 0.95)
Bob   -[knows]-> Skill:Python (confiança: 0.7)
Carol -[learning]-> Skill:Python (confiança: 0.5)
```

Consulta: "Quem são nossos especialistas em Python?" (filtre por verb="expert_in")

### 4. Grafo de Conhecimento de Pesquisa

Rastreie conceitos e seus relacionamentos:

```
Paper_123 -[discusses]-> Concept:Redes Neurais
Paper_123 -[discusses]-> Concept:Transformers
Paper_456 -[discusses]-> Concept:Transformers
```

Consulta: "Quais papers discutem Transformers?"

## Melhores Práticas

### Escolha Tipos de Fatos Descritivos

Use nomes de tipo específicos e consistentes:

```json
// Bom
{ "type": "Location", "name": "Paris" }
{ "type": "Company", "name": "Acme Corp" }
{ "type": "Skill", "name": "Python" }

// Ruim (muito genérico)
{ "type": "Thing", "name": "Paris" }
{ "type": "Entity", "name": "Acme Corp" }
```

### Use Nomenclatura de Verbos Consistente

Padronize seus verbos para permitir consultas:

```json
// Bom (tempo e formato consistentes)
"lives_in", "works_at", "knows", "enjoys"

// Ruim (inconsistente)
"living_in", "workAt", "Knows", "is_enjoying"
```

**Recomendações:**
- Use snake_case (lives_in, não livesIn ou lives-in)
- Use tempo presente para fatos atuais (works_at, não worked_at)
- Use tempo passado para fatos históricos (worked_at, visited)
- Use verbos consistentes em relacionamentos similares

### Defina Pontuações de Confiança Apropriadas

Não coloque tudo como 1.0 por padrão:

```python
# Declaração explícita → confiança alta
"Eu moro em Paris" → 1.0

# Implícito mas claro → confiança moderada-alta
"Eu amo o clima aqui em Paris" → 0.85

# Ambíguo ou futuro → confiança mais baixa
"Eu talvez me mude para Paris" → 0.4
```

Pontuações de confiança mais baixas ajudam a:
- Priorizar informações confiáveis
- Sinalizar fatos que precisam de verificação
- Permitir filtragem baseada em confiança

### Normalize Nomes de Fatos

Mantenha nomes de fatos consistentes:

```json
// Bom (casing e formato consistentes)
{ "type": "Location", "name": "Paris" }
{ "type": "Location", "name": "Nova York" }

// Ruim (casing inconsistente)
{ "type": "Location", "name": "paris" }
{ "type": "Location", "name": "NOVA YORK" }
```

Isso previne fatos duplicados como `Location:Paris` e `Location:paris`.

## Consultando Fatos

### Encontrar Todos os Fatos para uma Entidade

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@exemplo.com
```

Retorna todos os fatos associados à entidade da Alice.

### Filtrar por Tipo de Fato

```cypher
# Exemplo de consulta Apache AGE
SELECT * FROM cypher('nous', $$
  MATCH (e:Entity)-[r:HAS_FACT]->(f:Fact)
  WHERE f.type = 'Location'
  RETURN e, r, f
$$) as (entity agtype, relation agtype, fact agtype);
```

### Filtrar por Confiança

```cypher
# Encontrar apenas fatos de alta confiança
SELECT * FROM cypher('nous', $$
  MATCH (e:Entity)-[r:HAS_FACT]->(f:Fact)
  WHERE r.confidence_score >= 0.8
  RETURN e, r, f
$$) as (entity agtype, relation agtype, fact agtype);
```

## Proveniência do Fato

Cada fato remete à sua fonte através do relacionamento `DERIVED_FROM`:

```
(Fact) -[DERIVED_FROM]-> (Source)
```

Isso permite:
- **Auditabilidade**: "De onde veio esse fato?"
- **Confiança**: Avaliar fatos com base na confiabilidade da fonte
- **Depuração**: Rastrear informações incorretas
- **Conformidade**: Manter linhagem de dados para regulamentações

[Saiba mais sobre Fontes →](/pt-br/concepts/sources)

## Perguntas Comuns

### Um fato pode pertencer a múltiplas entidades?

Sim! Esse é o poder do modelo de fatos. O mesmo nó de fato (ex: `Location:Paris`) pode ter muitos relacionamentos `HAS_FACT` apontando para ele de diferentes entidades.

### Como atualizo um fato?

Fatos em si são imutáveis. Se a informação mudar:
1. O nó de fato permanece o mesmo (`Location:Paris`)
2. Atualize o relacionamento `HAS_FACT` (mude verbo, pontuação de confiança)
3. Ou remova o relacionamento antigo e crie um novo

### Fatos podem referenciar outros fatos?

Não diretamente no esquema atual. Fatos são projetados para serem peças atômicas de conhecimento. Relacionamentos complexos devem ser modelados através de entidades.

### Devo criar um fato para cada peça de informação?

Não. Fatos funcionam melhor para:
- Informação discreta e reutilizável
- Conhecimento que precisa ser consultado
- Informação compartilhada entre entidades

Para notas específicas de entidade ou metadados, considere usar o campo de metadados da entidade ou criar um tipo de fato mais específico.

## Conceitos Relacionados

- [Entidades](/pt-br/concepts/entities) - Os sujeitos que possuem fatos
- [Fontes](/pt-br/concepts/sources) - De onde os fatos se originam
- [Visão Geral](/pt-br/concepts/overview) - Como os fatos se encaixam no grafo de conhecimento
