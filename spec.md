# Sistema RAG Especialista em Seguros Aeronáuticos e Regulamentações (CNSP/SUSEP)
## Documento de Especificação Técnica (spec.md)

Este documento serve como a **Fonte Única da Verdade (Single Source of Truth - SSOT)** para o desenvolvimento do sistema RAG. Ferramentas de IA (Cursor, Claude Code, etc.) devem seguir estritamente estas diretrizes e não avançar para os passos seguintes sem validação prévia.

---

## 1. Visão Geral do Sistema
O objetivo é construir um Agente de IA capaz de realizar consultas, auditorias cruzadas e análises de conformidade em apólices de seguros aeronáuticos e de hangares, baseando-se em 6 documentos específicos:
1. **Resolução CNSP nº 407/2021** (Regulamento mestre de Grandes Riscos da SUSEP)
2. **CG_AXA_RC Hangar.pdf** (Condições Gerais da AXA)
3. **CG_Essor_RC Hangar.pdf** (Condições Gerais da Essor)
4. **CG_Excelsior-RC-Hangar.pdf** (Condições Gerais da Excelsior)
5. **CG_EZZE_Hangar.pdf** (Condições Gerais da EZZE)
6. **CG_Mapfre_RC_HANGAR.pdf** (Condições Gerais da Mapfre)

---

## 2. Arquitetura de Software e Fluxo de Dados

O sistema será modular, dividido em 4 scripts principais escritos em Python (versão 3.10+), utilizando as bibliotecas `pypdf`, `langchain-community`, `openai` (ou SDK do Google) e banco de dados `Supabase` com a extensão `pgvector`.

### Estrutura de Pastas de Referência
```text
seguros-aeronauticos-rag/
├── dados/
│   ├── raw/                 # Os 6 PDFs originais
│   └── testes/              # dataset_testes.csv (Perguntas, respostas ideais, regras esperadas)
├── staging/                 # JSONs individuais por página gerados pelo ETL
├── .env                     # Chaves de API (OpenAI/Google, Supabase URL e Anon Key)
├── parse_pdf.py             # Script do Passo 1 (ETL e extração)
├── create_embeddings.py     # Script do Passo 2 (Chunking e Ingestão)
├── test_retrieval.py        # Script do Passo 3 (LLM as a Judge / Avaliação)
├── agent.py                 # Script do Passo 4 (Agente, Tools e Threshold Dinâmico)
├── Makefile                 # Automação de tarefas
└── spec.md                  # Este arquivo de especificações
```

---

## 3. Especificação dos Módulos (Passo a Passo)

### Passo 1: Script de ETL e Ingestão (`parse_pdf.py`)
* **Objetivo:** Ler os PDFs brutos da pasta `dados/raw/` e convertê-los em arquivos estruturados para evitar reprocessamento desnecessário.
* **Comportamento:**
  - Extrair o texto limpando caracteres especiais, quebras de linhas órfãs e mantendo tabelas lidas em formato corrido compreensível.
  - Salvar um arquivo `.json` individual para cada página na pasta `staging/`.
* **Esquema do JSON de Saída:**
  ```json
  {
    "nome_arquivo": "SUSEP 407_2021.pdf",
    "pagina": 1,
    "texto": "Conteúdo extraído da página...",
    "metadata": {
      "tipo": "resolucao_mestre",
      "orgao": "CNSP_SUSEP",
      "enquadramento": "grandes_riscos"
    }
  }
  ```
  *(Para seguradoras, o metadata deve mapear obrigatoriamente a chave `"seguradora": "AXA | Essor | Excelsior | EZZE | Mapfre"`).*

### Passo 2: Script de Chunking e Vetorização (`create_embeddings.py`)
* **Objetivo:** Fragmentar o texto do staging de forma semântica e alimentar o Supabase.
* **Comportamento:**
  - Ler a pasta `staging/`.
  - Implementar suporte a múltiplas estratégias de quebra utilizando LangChain.
  - Criar tabelas ou esquemas no Supabase correspondentes a cada estratégia sob uma coluna identificadora chamada `collection`.
* **Estratégias Obrigatórias:**
  - **Estratégia A (Cláusula/Artigo Inteiro):** Agrupar parágrafos e incisos de um mesmo Artigo (para SUSEP) ou Cláusula (para apólices) no mesmo bloco de texto. Essencial para preservar o contexto de exclusões secundárias.
  - **Estratégia B (Chunks Fixos):** Fragmentos de 256 e 512 tokens com overlap de 10% para páginas que contenham exclusivamente o Glossário de termos.
* **Armazenamento:** Enviar para o banco o texto bruto do chunk, os metadados herdados + o número do chunk, o vetor gerado (Embedding) e o nome da estratégia.

### Passo 3: Script de Teste Automático (`test_retrieval.py`)
* **Objetivo:** Avaliar de forma científica qual estratégia e método de busca performa melhor através de engenharia reversa e *LLM as a Judge*.
* **Comportamento:**
  - Carregar o arquivo `dados/testes/dataset_testes.csv`.
  - Executar a mesma pergunta em 3 modalidades de busca no banco vetorial:
    1. Busca vetorial por similaridade pura (Cenário de controle).
    2. **Busca Híbrida:** Combinação de similaridade de cosseno com busca textual padrão (Full-Text Search) para termos como "AVN38B", "SUSEP", "Franquia".
    3. **HyDE (Hypothetical Document Embeddings):** A LLM cria uma resposta fictícia com jargão técnico aeronáutico, o script gera o embedding dessa ficção e usa para buscar na base real.
  - **Métrica de Avaliação (LLM as a Judge):** Para cada retorno, invocar uma LLM via API com um System Prompt rígido instruindo a dar uma nota de `0` a `1` e `TRUE/FALSE` se as cláusulas fundamentais para responder à pergunta estão contidas nos chunks retornados pelo banco.
  - **Saída:** Printar uma tabela comparativa de performance no terminal. A melhor configuração será herdada pelo agente.

### Passo 4: Script do Agente e Ferramenta (`agent.py`)
* **Objetivo:** O orquestrador final que responde às interações do usuário.
* **Comportamento:**
  - Encapsular a busca campeã do Passo 3 em uma função Python e expô-la à LLM (`GPT-4o-mini` ou similar) como uma **Tool (Ferramenta)**.
  - Definir o parâmetro de similaridade inicial (`threshold`) rígido em `0.7`.
  - **Lógica de Segunda Tentativa Autônoma:** Se o retorno da ferramenta com threshold `0.7` for vazio ou insuficiente para responder à dúvida, a LLM deve reescrever a query buscando sinônimos do mercado securitário (ex: traduzindo "ataque hacker" para "dados eletrônicos" ou "riscos cibernéticos") e disparar uma segunda tentativa diminuindo dinamicamente o parâmetro para `0.6`.

---

## 4. Definição de Concluído (DoD)
Para cada script gerado pela IA, as seguintes condições devem ser validadas antes de passar para o próximo arquivo:
1. O script roda sem erros de tipagem ou imports órfãos.
2. Trata falhas de conexão de API (retries) e logs legíveis no terminal.
3. Não utiliza ferramentas visuais (No-code/Low-code); é 100% código Python nativo.