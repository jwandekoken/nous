---
title: Introdução
description: Introdução ao Nous - Memória em Grafo de Conhecimento para Agentes de IA
---

Nous é um sistema de memória baseado em grafo de conhecimento projetado para dar aos agentes de IA memória persistente e estruturada.

## O Problema

Imagine ter uma conversa com alguém que esquece tudo que você disse cinco minutos atrás. É essencialmente assim que a maioria dos agentes de IA funciona hoje.

Large Language Models são **stateless** — não têm memória persistente. Cada conversa começa do zero, e mesmo dentro de uma conversa, são limitados por janelas de contexto. A maioria dos agentes hoje sofre de "amnésia de curto prazo", operando com janelas de contexto deslizantes que só lembram das últimas mensagens.

Isso cria uma limitação fundamental: **agentes não conseguem realmente conhecer você**. Eles não conseguem lembrar suas preferências, seu histórico, ou o contexto que torna as interações significativas.

## Abordagens Atuais e Suas Limitações

Várias abordagens existem para dar memória aos agentes, mas cada uma tem desvantagens significativas:

| Abordagem | Como Funciona | Limitação |
|-----------|---------------|-----------|
| **Prompt Stuffing** | Incluir todo histórico da conversa no prompt | Caro, atinge limites de contexto rapidamente |
| **Sumarização** | Comprimir conversas passadas em resumos | Perde detalhes importantes |
| **Busca Vetorial (RAG)** | Armazenar e recuperar por similaridade semântica | Sem relacionamentos estruturados |
| **Grafos de Conhecimento** | Armazenar entidades e relacionamentos | Sem busca semântica/fuzzy |

O insight chave é que **a memória humana não funciona apenas por similaridade — funciona por conexão**. Quando você aprende que "Alice se mudou para Berlim", você não cria apenas um ponto de dados flutuante. Você atualiza seu modelo mental de Alice com um novo atributo. É um grafo, não uma lista.

## A Abordagem do Nous

Nous (do Grego, "intelecto" ou "mente") combina o melhor dos dois mundos:

- **Banco de Dados em Grafo** — Armazena entidades e seus relacionamentos de forma estruturada
- **Banco de Dados Vetorial** — Permite busca semântica e correspondência fuzzy

Essa abordagem híbrida significa que você obtém tanto o **raciocínio estrutural** de um grafo de conhecimento quanto a **flexibilidade semântica** da busca vetorial.

## Como Funciona

Nous fornece duas operações principais:

### Assimilar (Escrita)

Quando você envia texto para o Nous, ele:
1. Extrai fatos atômicos do conteúdo usando um LLM
2. Identifica ou cria entidades relevantes
3. Armazena os fatos no grafo com seus relacionamentos
4. Cria embeddings vetoriais para busca semântica

```
Entrada: "João mora em Curitiba e trabalha como engenheiro de dados.
          Ele adora jogar xadrez nos fins de semana."

Resultado:
  Entidade: João
  Fatos:
    - mora_em: Curitiba
    - trabalha_como: Engenheiro de Dados
    - gosta_de: Xadrez
```

### Lookup (Leitura)

Quando você precisa recuperar informações:
1. Consulte por entidade, busca semântica, ou ambos
2. Obtenha fatos estruturados com suas fontes
3. Receba contexto otimizado para consumo por LLM

Isso permite que seu agente responda perguntas como "Onde essa pessoa mora?" ou "Quais são os hobbies dela?" com informações precisas e com fonte.

## Casos de Uso

- **Assistentes Pessoais** — Lembrar preferências e contexto do usuário
- **CRM Inteligente** — Rastrear histórico de interações com clientes
- **Tutores de IA** — Lembrar progresso e estilo de aprendizado do aluno
- **Assistentes de Saúde** — Manter histórico médico contextualizado
- **Agentes de Vendas** — Construir conhecimento profundo de cada cliente

## Próximos Passos

Pronto para começar? Vá para o guia de [Instalação](/pt-br/getting-started/installation/) para configurar o Nous.
