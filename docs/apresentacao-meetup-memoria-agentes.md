# Apresentacao Meetup: Memoria para Agentes de IA

## 1. Abertura - O Problema (5 min)

> "Imaginem ter uma conversa com alguem que esquece tudo que voces disseram 5 minutos atras..."

- LLMs sao **stateless** - nao tem memoria persistente
- Context windows sao limitados (mesmo os maiores tem limites)
- Cada nova conversa = "amnesia total"

---

## 2. Paralelo com Memoria Humana (10 min)

| Memoria Humana | Analogia em IA |
|----------------|----------------|
| **Memoria Sensorial** (milissegundos) | Input tokens - o prompt atual |
| **Memoria de Curto Prazo** (segundos/minutos) | Context window - a conversa atual |
| **Memoria de Longo Prazo** | Nao existe nativamente em LLMs! |

### Subdivisoes da Memoria de Longo Prazo

| Tipo | Humano | Em Agentes |
|------|--------|------------|
| **Episodica** | Lembrar eventos especificos ("Ontem fui ao medico") | Historico de conversas, fontes |
| **Semantica** | Conhecimento factual ("Paris e capital da Franca") | **Knowledge Graph** - fatos estruturados |
| **Procedural** | Saber fazer algo (andar de bicicleta) | Tools, plugins, codigo |

**Ponto-chave:** O Nous foca na **memoria semantica** - armazenar **fatos** sobre entidades.

---

## 3. Como Agentes "Lembram" Hoje? (5 min)

### Abordagens comuns

1. **Prompt stuffing** - jogar todo historico no contexto (caro, limitado)
2. **Summarization** - resumir conversas (perde detalhes)
3. **Vector search (RAG)** - busca semantica (sem estrutura relacional)
4. **Knowledge Graphs** - estrutura relacional (sem busca semantica)

**Insight:** Cada abordagem tem limitacoes. E se combinassemos as melhores?

---

## 4. A Motivacao do Nous (5 min)

> "Um agente que realmente conhece voce"

### Cenario

Um assistente pessoal que:
- Sabe que voce mora em Sao Paulo
- Lembra que voce e alergico a camarao
- Conhece seus hobbies e preferencias
- E pode **explicar de onde** veio cada informacao

### Nous combina

- **Graph Database** (PostgreSQL + Apache AGE) - Estrutura e relacoes
- **Vector Database** (Qdrant) - Busca semantica
- **LLM** (Gemini) - Extracao automatica de fatos

---

## 5. Arquitetura do Nous (10 min)

```
+-------------------------------------------------------------+
|                      Aplicacao / Agente                      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                        Nous API                              |
|  +-------------+  +-------------+  +---------------------+  |
|  |  Assimilate |  |   Lookup    |  |  Lookup Summary     |  |
|  |  (Escrever) |  |   (Ler)     |  |  (Resumo p/ LLM)    |  |
|  +-------------+  +-------------+  +---------------------+  |
+-------------------------------------------------------------+
         |                    |
         v                    v
+-----------------+  +-----------------+
|   Graph DB      |  |   Vector DB     |
|  (PostgreSQL    |  |    (Qdrant)     |
|   + AGE)        |  |                 |
|                 |  |  Embeddings     |
|  Entity-Fact    |  |  semanticos     |
|  relationships  |  |                 |
+-----------------+  +-----------------+
```

### Conceitos-chave

- **Entity** - O sujeito central (pessoa, empresa, conceito)
- **Fact** - Pedaco discreto de conhecimento
- **Source** - De onde veio a informacao (proveniencia)
- **Identifier** - Formas de encontrar a entidade (email, telefone, etc.)

---

## 6. Demo ao Vivo (15 min)

### Roteiro

#### 1. Assimilar informacao (POST /assimilate)

```
"Meu nome e Joao, moro em Curitiba e trabalho como engenheiro de dados.
Adoro jogar xadrez nos fins de semana."
```

#### 2. Visualizar o grafo (Frontend)

- Mostrar a entidade criada
- Mostrar os fatos extraidos automaticamente
- Mostrar as relacoes (lives_in, works_as, enjoys)

#### 3. Busca semantica (GET /lookup com RAG)

```
Query: "onde essa pessoa mora?"
Query: "quais sao os hobbies?"
```

#### 4. Lookup Summary

Mostrar como fica otimizado para contexto de LLM

#### 5. Adicionar mais informacao

```
"Recentemente comecei a aprender piano e estou planejando
uma viagem para Portugal em marco."
```

#### 6. Mostrar evolucao do grafo

Novos fatos adicionados ao conhecimento existente

---

## 7. Casos de Uso (5 min)

- **Assistentes pessoais** que lembram preferencias
- **CRM inteligente** - historico de interacoes com clientes
- **Tutores de IA** - lembrar progresso do aluno
- **Assistentes de saude** - historico medico contextualizado
- **Agentes de vendas** - conhecer o cliente profundamente

---

## 8. Q&A e Discussao (5-10 min)

### Perguntas provocativas para a audiencia

- "Se agentes tiverem memoria perfeita, quais sao as implicacoes de privacidade?"
- "Como lidar com informacoes contraditorias ao longo do tempo?"
- "Memoria de agentes deve ser editavel pelo usuario?"

---

## Dicas para a Apresentacao

1. **Comece com uma historia** - nao com tecnologia
2. **Use analogias** - a comparacao com memoria humana e poderosa
3. **Demo > Slides** - mostre funcionando
4. **Prepare fallback** - tenha screenshots/video caso algo falhe na demo

---

## Tempo Total Estimado

| Secao | Duracao |
|-------|---------|
| Abertura | 5 min |
| Paralelo Memoria Humana | 10 min |
| Como Agentes Lembram | 5 min |
| Motivacao do Nous | 5 min |
| Arquitetura | 10 min |
| Demo ao Vivo | 15 min |
| Casos de Uso | 5 min |
| Q&A | 5-10 min |
| **Total** | **~60 min** |
