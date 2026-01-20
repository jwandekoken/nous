---
title: Fontes
description: Rastreando a proveniência e origem do conhecimento no seu grafo
---

Uma **Fonte** (Source) representa a origem da informação no seu grafo de conhecimento. Fontes capturam de onde os fatos vieram — uma mensagem de chat, e-mail, documento, chamada de API ou qualquer peça de conteúdo da qual o conhecimento foi extraído.

## O que é uma Fonte?

No Nous, cada fato deve ser rastreável até sua origem. Fontes fornecem essa rastreabilidade, respondendo à questão crítica: "Como sabemos isso?"

### Características Principais

- **Rastreamento de Proveniência**: Cada fato remete a uma fonte
- **Preservação de Conteúdo**: Armazena o texto ou dados originais
- **Contexto Temporal**: Registra quando a fonte foi criada
- **Trilha de Auditoria**: Permite verificação e depuração

## Propriedades da Fonte

| Propriedade | Tipo     | Obrigatório | Descrição                                      |
|-------------|----------|-------------|------------------------------------------------|
| `id`        | UUID     | Auto        | Identificador único do sistema                 |
| `content`   | string   | Sim         | O conteúdo/texto original da fonte             |
| `timestamp` | datetime | Auto        | Timestamp do mundo real quando a fonte foi criada |

### Exemplo de Estrutura de Fonte

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "content": "Alice mudou-se para Paris mês passado e começou a trabalhar na Acme Corp.",
  "timestamp": "2025-01-15T14:30:00Z"
}
```

## Por Que Rastrear Fontes?

### 1. Auditabilidade

Quando fatos entram em conflito ou precisam de verificação, as fontes fornecem a evidência:

```
Fato: Alice mora em Paris
  ↓ DERIVED_FROM
Fonte (15 Jan): "Alice mudou-se para Paris mês passado"

Fato: Alice mora em Londres
  ↓ DERIVED_FROM
Fonte (10 Dez): "Alice está se instalando em seu novo apartamento em Londres"
```

Ao comparar fontes e timestamps, você pode determinar:
- Qual informação é mais recente?
- Qual fonte é mais autoritativa?
- Se os fatos precisam de atualização ou reconciliação

### 2. Confiança e Credibilidade

Nem todas as fontes são igualmente confiáveis. Fontes permitem raciocínio baseado em confiança:

```
Fonte A: Anúncio oficial da empresa → Confiança alta
Fonte B: Rumor de mídia social → Confiança mais baixa
Fonte C: Mensagem direta da pessoa → Confiança mais alta
```

Você pode ajustar pontuações de confiança de fatos com base na confiabilidade da fonte.

### 3. Depuração e Correção

Quando você descobre informações incorretas:
1. Rastreie o fato de volta à sua fonte
2. Identifique por que a extração estava errada
3. Corrija a causa raiz (lógica de extração, qualidade da fonte)
4. Reprocesse ou atualize o fato

### 4. Conformidade e Regulamentações

Muitas indústrias exigem linhagem de dados:
- **Saúde**: Rastreie onde a informação do paciente se originou
- **Finanças**: Trilha de auditoria para dados financeiros
- **Jurídico**: Cadeia de custódia para evidências
- **LGPD**: Saiba de onde os dados pessoais vieram

## O Relacionamento DERIVED_FROM

Fatos se conectam a fontes através do relacionamento `DERIVED_FROM`:

```
(Fact) -[DERIVED_FROM]-> (Source)
```

### Propriedades do Relacionamento

| Propriedade    | Tipo   | Descrição                           |
|----------------|--------|-------------------------------------|
| `from_fact_id` | string | O fato que foi derivado             |
| `to_source_id` | UUID   | A fonte onde o fato se originou     |

### Exemplo de Relacionamento

```json
{
  "from_fact_id": "Location:Paris",
  "to_source_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

Isso vincula o fato `Location:Paris` à fonte contendo "Alice mudou-se para Paris mês passado."

## Entendendo Timestamps

Fontes usam um **timestamp do mundo real** (`timestamp`) que representa quando o evento original ocorreu:

```json
{
  "timestamp": "2025-01-15T14:30:00Z"  // Quando a mensagem foi enviada
}
```

Isso é diferente de timestamps de sistema como `created_at` em entidades e relacionamentos, que rastreiam quando registros foram adicionados ao Nous.

### Tempo do Evento vs Tempo do Sistema

| Tipo de Tempo   | Campo        | Significado                             |
|-----------------|--------------|------------------------------------------|
| Tempo do Evento | `timestamp`  | Quando o evento do mundo real aconteceu  |
| Tempo do Sistema| `created_at` | Quando o Nous registrou a informação     |

**Exemplo:**

```
Usuário envia uma mensagem em 15 Jan às 14:00
  → Source.timestamp = "2025-01-15T14:00:00Z"

Mensagem é processada pelo Nous em 16 Jan às 10:00
  → Entity.created_at = "2025-01-16T10:00:00Z"
```

Essa separação permite:
- **Consultas Temporais**: "O que sabíamos sobre Alice em Dezembro?"
- **Análise Histórica**: Reconstruir o estado do conhecimento em qualquer ponto no tempo
- **Trilhas de Auditoria**: Distinguir quando eventos ocorreram vs. quando foram registrados

## Tipos de Fonte e Metadados

Embora o modelo de fonte seja flexível, fontes diferentes têm características diferentes. Considere usar o padrão de metadados de entidade para categorização de fonte:

### Tipos de Fonte Comuns

```json
// Mensagem de chat
{
  "content": "Alice: Acabei de me mudar para Paris!",
  "timestamp": "2025-01-15T14:30:00Z",
  "metadata": {
    "type": "chat_message",
    "channel": "slack",
    "user_id": "U12345"
  }
}

// E-mail
{
  "content": "Assunto: Novo Endereço\n\nOlá equipe, meu novo endereço é...",
  "timestamp": "2025-01-10T09:00:00Z",
  "metadata": {
    "type": "email",
    "from": "alice@exemplo.com",
    "subject": "Novo Endereço"
  }
}

// Documento
{
  "content": "Registro de funcionário atualizado: Alice Smith, Localização: Paris",
  "timestamp": "2025-01-15T16:00:00Z",
  "metadata": {
    "type": "document",
    "document_id": "doc-123",
    "file_type": "pdf"
  }
}

// Chamada de API
{
  "content": "{\"user\": \"alice\", \"location\": \"Paris\"}",
  "timestamp": "2025-01-15T14:35:00Z",
  "metadata": {
    "type": "api_response",
    "endpoint": "/users/alice",
    "source_system": "crm"
  }
}
```

Nota: O esquema atual não inclui um campo de metadados em fontes, mas você pode estendê-lo ou codificar metadados no campo de conteúdo.

## Trabalhando com Fontes

### Criando Fontes Durante Assimilação

Fontes são tipicamente criadas automaticamente durante o processo de assimilação:

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
1. Criar uma nova fonte com o conteúdo
2. Extrair fatos do conteúdo
3. Vincular fatos à fonte via `DERIVED_FROM`
4. Associar fatos com a entidade

### Recuperando Fontes para Fatos

Quando você consulta uma entidade, fontes são incluídas na resposta:

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@exemplo.com
```

Resposta inclui:
- A entidade
- Todos os fatos
- Todas as fontes para esses fatos

Isso fornece transparência completa: "Aqui está o que sabemos sobre Alice e onde aprendemos isso."

## Casos de Uso

### 1. Memória de IA Conversacional

Rastreie histórico de conversa:

```
Fonte 1 (5 Jan): "Eu amo caminhar nas montanhas"
  → Fato: Hobby:Caminhada

Fonte 2 (12 Jan): "Estou planejando uma viagem para o Colorado"
  → Fato: Location:Colorado (verbo: planning_to_visit)

Fonte 3 (20 Jan): "Acabei de voltar de uma caminhada incrível no Rocky Mountain National Park"
  → Fato: Location:Colorado (verbo: visited)
```

A IA pode dizer: "A última vez que conversamos em 12 de janeiro, você estava planejando uma viagem para o Colorado. Como foi?"

### 2. Contexto de Suporte ao Cliente

Construa uma linha do tempo de interações com o cliente:

```
Fonte A (1 Dez): "Minha conta está bloqueada"
  → Fato: Issue:Conta Bloqueada

Fonte B (2 Dez): Ticket de suporte resolvido
  → Fato: Status:Resolvido

Fonte C (5 Jan): "Mesmo problema de novo!"
  → Fato: Issue:Conta Bloqueada (segunda ocorrência)
```

Agentes de suporte podem ver: "Esta é a segunda vez este mês que o cliente reporta este problema."

### 3. Gestão de Conhecimento de Pesquisa

Rastreie a linhagem de descobertas de pesquisa:

```
Paper A (2023): Afirma que X é verdadeiro
  → Fato: Claim:X (confiança: 0.8)

Paper B (2024): Confirma X com evidência adicional
  → Mesmo Fato: Claim:X (confiança: 0.95)

Paper C (2025): Disputa X
  → Fato Conflitante: Claim:Não-X (confiança: 0.7)
```

Pesquisadores podem ver: "A afirmação X tem suporte dos Papers A e B mas é disputada no Paper C."

### 4. Linhagem de Dados para Conformidade

Demonstre de onde dados pessoais vieram:

```
Fonte: Formulário de registro de usuário (2024-01-15)
  → Fato: Email:alice@exemplo.com
  → Fato: Location:Paris

Fonte: Chat de suporte ao cliente (2024-03-20)
  → Fato: Phone:+1-555-0123

Fonte: Atualização de configurações da conta (2024-06-10)
  → Fato: Location:Londres (atualizado)
```

Para solicitações LGPD, você pode fornecer: "Aqui estão todos os dados que coletamos sobre você e quando coletamos."

## Melhores Práticas

### Preserve Conteúdo Original

Sempre armazene o texto fonte completo e original:

```json
// Bom
{
  "content": "Usuário: Acabei de me mudar para Paris semana passada! Adorando até agora."
}

// Ruim (informação perdida)
{
  "content": "Mudou para Paris"
}
```

Conteúdo original permite:
- Reprocessamento com lógica de extração melhorada
- Revisão humana quando fatos conflitam
- Contexto para informação ambígua

### Use Timestamps Precisos

Defina o `timestamp` para quando o evento ocorreu, não quando você o processou:

```python
# Bom
source.timestamp = message.sent_at  # Quando o usuário enviou a mensagem

# Ruim
source.timestamp = datetime.now()  # Quando você está processando
```

### Não Exclua Fontes Prematuramente

Mesmo depois que fatos são extraídos, mantenha fontes para:
- Trilhas de auditoria
- Re-extração com modelos melhorados
- Verificação humana

Apenas exclua fontes quando:
- Requisitos legais exigirem (solicitações de exclusão LGPD)
- Restrições de armazenamento absolutamente exigirem
- Fatos foram completamente verificados através de outros meios

### Considere Autoridade da Fonte

Quando fatos conflitam, autoridade da fonte importa:

```python
# Alta autoridade
fonte_documento_oficial → confiança = 1.0

# Média autoridade
fonte_declaracao_usuario → confiança = 0.85

# Baixa autoridade
fonte_rumor_terceiros → confiança = 0.5
```

Você pode codificar autoridade em:
- Pontuação de confiança do fato
- Metadados da fonte (se estendido)
- Sua lógica de extração de fatos

## Consultando Fontes

### Encontrar Todas as Fontes para uma Entidade

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@exemplo.com
```

Retorna entidade com todos os fatos e suas fontes.

### Rastrear um Fato Específico para Fontes

```cypher
# Exemplo de consulta Apache AGE
SELECT * FROM cypher('nous', $$
  MATCH (f:Fact {fact_id: 'Location:Paris'})-[d:DERIVED_FROM]->(s:Source)
  RETURN f, d, s
  ORDER BY s.timestamp DESC
$$) as (fact agtype, relation agtype, source agtype);
```

### Encontrar Fontes por Intervalo de Tempo

```cypher
SELECT * FROM cypher('nous', $$
  MATCH (s:Source)
  WHERE s.timestamp >= '2025-01-01T00:00:00Z'
    AND s.timestamp < '2025-02-01T00:00:00Z'
  RETURN s
  ORDER BY s.timestamp
$$) as (source agtype);
```

## Validação de Fonte

Fontes validam seu conteúdo para prevenir erros:

**Validação de Conteúdo:**
- Não pode ser vazio ou conter apenas espaços em branco
- Automaticamente remove espaços no início/fim

```python
# Válido
Source(content="Alice mudou-se para Paris")

# Inválido (levanta ValueError)
Source(content="")
Source(content="   ")
```

## Perguntas Comuns

### Múltiplos fatos podem vir da mesma fonte?

Sim! Uma única fonte frequentemente produz múltiplos fatos:

```
Fonte: "Alice mudou-se para Paris e começou a trabalhar na Acme Corp"
  ↓ DERIVED_FROM
  ├── Fato: Location:Paris
  ├── Fato: Company:Acme Corp
  └── Fato: JobTitle:Funcionário
```

### Um fato pode ter múltiplas fontes?

Sim! O mesmo fato pode ser confirmado por múltiplas fontes:

```
Fato: Location:Paris
  ↓ DERIVED_FROM (de múltiplas fontes)
  ├── Fonte A: "Alice mora em Paris"
  ├── Fonte B: "Enviado de Paris, França"
  └── Fonte C: "Escritório da Alice em Paris"
```

Isso aumenta a confiança no fato.

### Devo criar uma fonte para fatos inseridos manualmente?

Sim. Mesmo para entradas manuais, crie uma fonte para manter a proveniência:

```json
{
  "content": "Admin verificou manualmente: Alice trabalha na Acme Corp",
  "timestamp": "2025-01-15T10:00:00Z"
}
```

Isso documenta quem adicionou a informação e quando.

### Como lido com fontes que contêm múltiplas entidades?

Uma fonte pode mencionar múltiplas entidades:

```
Fonte: "Alice e Bob ambos mudaram-se para Paris"
  ↓ DERIVED_FROM
  ├── Entidade (Alice) → Fato: Location:Paris
  └── Entidade (Bob) → Fato: Location:Paris
```

A mesma fonte produz fatos para diferentes entidades.

## Conceitos Relacionados

- [Fatos](/pt-br/concepts/facts) - O conhecimento derivado de fontes
- [Entidades](/pt-br/concepts/entities) - Os sujeitos sobre os quais são os fatos
- [Visão Geral](/pt-br/concepts/overview) - Como fontes se encaixam no grafo de conhecimento

