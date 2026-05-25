# HANDOFF — Sistema RAG Especialista em Seguros Aeronáuticos

> Documento de continuidade técnica do projeto **seguros_aeronauticos_RAG**.
> Escrito para que outro time consiga retomar o desenvolvimento sem depender do histórico de conversa.
> Última atualização: 2026-05-25.

---

## 1. Visão geral do projeto

Este projeto implementa um **sistema RAG (Retrieval-Augmented Generation) especialista** em apólices e regulamentações de **seguros aeronáuticos de Responsabilidade Civil de Hangares e Operações Aeroportuárias** no mercado brasileiro.

O sistema constrói uma base vetorial a partir de documentos regulatórios (SUSEP) e de condições gerais (CGs) de cinco seguradoras, permitindo consultas semânticas e auditorias cruzadas com rastreabilidade total por fonte, página e seguradora.

A entrega final será um **agente de IA** capaz de responder perguntas técnicas sobre coberturas, exclusões, glossário, franquias e obrigações regulatórias, **citando explicitamente o documento e a página de onde a resposta foi extraída**.

---

## 2. Objetivo do RAG

O RAG deve:

- Responder perguntas técnicas sobre **Condições Gerais (CGs) de RC Hangar** das seguradoras AXA, Essor, Excelsior, EZZE e Mapfre.
- Responder perguntas sobre a **Resolução CNSP/SUSEP nº 407/2021** (regime de Grandes Riscos).
- Permitir **auditorias cruzadas**, por exemplo, comparar a redação de uma exclusão entre duas seguradoras.
- Garantir **rastreabilidade**: cada resposta deve apontar `nome_arquivo`, `pagina`, `seguradora` (ou `orgao` para a SUSEP) e `enquadramento` regulatório.
- Suportar futuramente diferentes estratégias de busca (vetorial pura, híbrida com Full-Text Search e HyDE) — ver [spec.md](./spec.md).

---

## 3. Base documental

O projeto trabalha com 6 PDFs originais (em [dados/raw/](./dados/raw/)):

| # | Arquivo | Função |
|---|---|---|
| 1 | `SUSEP 407_2021.pdf` | Resolução CNSP/SUSEP 407/2021 — regulamento mestre que define o regime de Grandes Riscos da SUSEP. Aplica-se a todas as apólices listadas. |
| 2 | `CG_AXA_RC Hangar.pdf` | Condições Gerais de RC Hangar — seguradora **AXA**. |
| 3 | `CG_Essor_RC Hangar.pdf` | Condições Gerais de RC Hangar — seguradora **Essor**. |
| 4 | `CG_Excelsior-RC-Hangar.pdf` | Condições Gerais de RC Hangar — seguradora **Excelsior**. |
| 5 | `CG_EZZE_Hangar.pdf` | Condições Gerais de RC Hangar — seguradora **EZZE**. |
| 6 | `CG_Mapfre_RC_HANGAR.pdf` | Condições Gerais de RC Hangar — seguradora **Mapfre**. |

Os PDFs originais **não devem ser apagados nem modificados**.

---

## 4. Arquitetura atual

Esteira de dados ponta-a-ponta:

```
[ 6 PDFs em dados/raw/ ]
         │
         ▼
   parse_pdf.py            (Passo 1 — ETL: PDF -> JSON por página)
         │
         ▼
   staging/  (274 JSONs)
         │
         ▼
  validate_staging.py      (auditoria dos JSONs — 0 erros críticos)
         │
         ▼
  create_embeddings.py     (Passo 2 — chunking + embeddings Gemini)
         │
         ▼
   Supabase pgvector       (tabela public.document_chunks, vector(768))
         │
         ▼
  Busca vetorial via RPC   (public.match_document_chunks)
         │
         ▼
   Agente RAG futuro       (Passo 4 — agent.py, ainda não implementado)
```

---

## 5. Estrutura de pastas e arquivos

| Arquivo / pasta | Papel |
|---|---|
| [spec.md](./spec.md) | SSOT (Single Source of Truth) original do projeto. Define os 4 passos e o DoD geral. |
| [parse_pdf.py](./parse_pdf.py) | **Passo 1**. Lê PDFs de `dados/raw/`, extrai texto por página e grava `staging/<nome>_pagina_N.json`. |
| [validate_staging.py](./validate_staging.py) | Auditoria dos arquivos JSON gerados: checagem de schema, encoding, páginas vazias e avisos benignos. |
| [create_embeddings.py](./create_embeddings.py) | **Passo 2**. Lê `staging/`, gera embeddings via Gemini e insere em `public.document_chunks` no Supabase. Possui `DRY_RUN`, `MAX_RECORDS`, cache local, retry com backoff e idempotência. |
| [test_supabase_connection.py](./test_supabase_connection.py) | Smoke test: valida `SUPABASE_URL` e conecta em `document_chunks` **sem** chamar Gemini e **sem** inserir nada. |
| [test_match.py](./test_match.py) | **Passo 2D**. Testa Retrieval: gera embedding da pergunta com `task_type="RETRIEVAL_QUERY"` e chama a RPC `match_document_chunks`. **Não** gera resposta final com LLM. Suporta `--question "..."` para pergunta única. |
| [generate_eval_dataset.py](./generate_eval_dataset.py) | **Passo 2E**. Lê `staging/` e gera o **draft** do dataset de avaliação em `eval/evaluation_dataset_draft.csv`. Não chama Gemini, não chama Supabase. |
| [curate_eval_dataset.py](./curate_eval_dataset.py) | **Passo 2F**. Curadoria automática do draft: gera `eval/evaluation_dataset_v1.csv` (até 30 linhas filtradas) e `eval/evaluation_dataset_rejected.csv` (linhas removidas + motivo). |
| [review_eval_dataset.py](./review_eval_dataset.py) | **Passo 2G**. Revisão assistida (sem LLM) da v1: gera `eval/evaluation_dataset.csv` (oficial preliminar, com coluna `revisao_observacao` e `status_revisao=aprovado_preliminar`) e `eval/evaluation_dataset_review.md` (versão legível em Markdown). |
| [eval/](./eval/) | Pasta do dataset de avaliação (`draft`, `v1`, `rejected`, oficial preliminar `.csv` + revisão `.md`) + `README.md` com fluxo de revisão humana. **Não é dataset de treino.** |
| [supabase_schema.sql](./supabase_schema.sql) | DDL para criar `public.document_chunks` (com `vector(768)`), índices (ivfflat, GIN para FTS e metadata, btree para colunas filtradas) e a RPC `match_document_chunks`. |
| [supabase_diagnostics.sql](./supabase_diagnostics.sql) | Queries de diagnóstico (colunas, índices, RPC, contagem de registros). |
| [supabase_add_unique_constraint.sql](./supabase_add_unique_constraint.sql) | **Opcional, não executado automaticamente**. Adiciona `UNIQUE (nome_arquivo, pagina, chunk_strategy, chunk_index)` em `document_chunks`. |
| [task.md](./task.md) | Checklist incremental de tarefas com status. |
| [walkthrough.md](./walkthrough.md) | Diário técnico dos passos 2A, 2B e 2C com decisões, sintomas e correções. |
| [requirements.txt](./requirements.txt) | Dependências Python (somente bibliotecas necessárias). |
| [.env.example](./.env.example) | Modelo de variáveis de ambiente. Não contém segredos reais. |
| [.gitignore](./.gitignore) | Cobertura ampla para Python, IDE, OS, caches e segredos. |
| [staging/](./staging/) | **Saída do Passo 1**. 274 JSONs, um por página dos 6 PDFs. **Não apagar.** |
| [dados/raw/](./dados/raw/) | PDFs originais. **Não apagar nem modificar.** |
| `.cache/` (gerado em runtime) | Cache local de embeddings Gemini (`gemini_embeddings_cache.jsonl`). **Não versionar e não apagar entre execuções** — ele protege a quota. |

---

## 6. Estado atual do projeto

### Passo 1 — ETL (CONCLUÍDO)
- `parse_pdf.py` implementado.
- `staging/` gerado com **274 arquivos JSON** (um por página).
- `validate_staging.py` retorna **0 erros críticos**.
- **Aviso benigno** conhecido: `CG_Essor_RC_Hangar_pagina_57.json` contém apenas `"essor.com.br"`. É um rodapé/página final e é **legitimamente ignorado** na geração de embeddings por ter menos de 30 caracteres.

### Passo 2A — Schema Supabase (CONCLUÍDO)
- Projeto Supabase configurado.
- Tabela oficial criada: `public.document_chunks` com `embedding vector(768)`.
- RPC `public.match_document_chunks` criada.
- Tabela antiga `public.documentos` **existe ou pode existir, mas NÃO deve ser usada como destino da pipeline**.
- Scripts SQL disponíveis: `supabase_schema.sql`, `supabase_diagnostics.sql`, `supabase_add_unique_constraint.sql` (este último opcional).

### Passo 2B — Pipeline de embeddings (CONCLUÍDO)
- `create_embeddings.py` implementado.
- Migrado para SDK novo **`google-genai`** (`google-generativeai` legado foi removido).
- Modelo: `gemini-embedding-001`, `output_dimensionality=768`, `task_type="RETRIEVAL_DOCUMENT"`.
- Estratégia de chunking atual: `chunk_strategy="page"` — **um chunk por página válida**.
- `DRY_RUN=True` gerou **273 chunks** (1 página ignorada por `MIN_CHARS_FOR_EMBEDDING = 30`).
- Distribuição: AXA 90 / EZZE 59 / Essor 56 / Mapfre 37 / Excelsior 25 / SUSEP 6.

### Passo 2C — Carga real validada com 3 chunks (CONCLUÍDO)
- Pipeline corrigida para **validar Supabase antes de chamar Gemini**.
- `test_supabase_connection.py` criado e validado.
- `SUPABASE_URL` validada após correção do bug `PGRST125`.
- Carga real limitada com `MAX_RECORDS=3` rodou com sucesso:
  - `DRY_RUN=False`, `MAX_RECORDS=3`
  - 273 páginas válidas processadas, 1 ignorada
  - 273 chunks criados em memória
  - 3 chunks considerados para carga real
  - **3 chamadas reais ao Gemini**
  - **3 inserções no Supabase**
  - 0 falhas de embedding
  - 0 falhas de inserção

> Em outras palavras: **a esteira ponta a ponta está funcional**. Faltam **270 chunks restantes** a inserir, em blocos controlados.

### Passo 2D — Teste de busca vetorial básica (CONCLUÍDO — esqueleto)
- [test_match.py](./test_match.py) criado.
- Testa **somente o Retrieval** do RAG (o "R" de RAG). **Não** gera resposta final com LLM.
- Gera embedding da pergunta com `task_type="RETRIEVAL_QUERY"` (modelo `gemini-embedding-001`, dim 768).
- Chama a RPC `public.match_document_chunks` no Supabase com `match_count=8` e `match_threshold=0.5` (valor baixo inicial para diagnóstico — pode ser elevado para `0.6`/`0.7` depois).
- Imprime cada chunk recuperado com `nome_arquivo`, `pagina`, `tipo`, `seguradora`/`orgao`, `chunk_strategy`, `chunk_index`, `token_count`, `similarity` e trecho do `content` (até `SHOW_CONTENT_CHARS=900`).
- Para cada pergunta, imprime uma linha de **avaliação manual** (`OK / PARCIAL / RUIM / NÃO ENCONTRADO`) para o time copiar do terminal e analisar relevância.
- Não insere, não altera, não apaga, não recria schema, não chama LLM de geração, não imprime chaves.
- Perguntas iniciais embutidas em `TEST_QUESTIONS`:
  1. "O que é casco aeronáutico?"
  2. "O seguro cobre pane seca?"
  3. "O que significa exclusão operacional?"
  4. "O que é responsabilidade civil no seguro aeronáutico?"
  5. "Quando a seguradora pode negar indenização?"
- Suporta modo interativo: `python test_match.py --question "..."` roda apenas a pergunta passada.

### Passo 2E — Dataset DRAFT de avaliação (CONCLUÍDO)
- [generate_eval_dataset.py](./generate_eval_dataset.py) implementado.
- Lê os 274 JSONs em `staging/` e gera **perguntas a partir de gatilhos lexicais** (riscos excluídos, perda de direito, recusa de sinistro, responsabilidade civil, obrigações do segurado, limite máximo de indenização, liquidação, franquia, âmbito geográfico, grandes riscos, CNSP/SUSEP, agravamento de risco, fraude etc.).
- Saída: `eval/evaluation_dataset_draft.csv` com **80 linhas** (5 perguntas manuais + 75 automáticas).
- Distribuição: AXA 15 / Excelsior 17 / Mapfre 16 / EZZE 12 / Essor 12 / CNSP_SUSEP 3 / TODAS 5 (manuais).
- Round-robin entre fontes garante representatividade de todas as seguradoras + SUSEP antes do cap global.
- Páginas com menos de 30 caracteres são ignoradas.
- O draft **não é dataset oficial** — é rascunho bruto e contém perguntas vindas de capa, sumário e índice. É a entrada da curadoria.
- **Não chama Gemini, não chama Supabase, não toca em `staging/` e não lê `.env`.**

### Passo 2F — Curadoria automática do dataset (CONCLUÍDO)
- [curate_eval_dataset.py](./curate_eval_dataset.py) implementado.
- Lê `eval/evaluation_dataset_draft.csv` e gera:
  - `eval/evaluation_dataset_v1.csv` — até 30 linhas, filtradas e renumeradas.
  - `eval/evaluation_dataset_rejected.csv` — linhas removidas + coluna `motivo_rejeicao`.
- Rejeita linhas automáticas quando a `resposta_ideal_draft`:
  - está vazia, é curta (< 80 chars) ou contém pontos de índice (`................`);
  - traz ruído de capa/sumário/contato/registro (`sumário`, `www.`, `telefone`, `cep:`, `endereço:`, `central de atendimento`, `sac`, `whatsapp`, `processo mapfre`, `processo ezze`, `nº interno axa`, `registro deste plano`, `condições contratuais versão`);
  - começa com fragmento de palavra (`usula`, `ico`, `dar `, `r vila`, `ão `, `ara `, `gações`, `enova`, `ontrole`, `ções `, `uer `, `rtuárias`, `omicílio`);
  - não traz sinal forte para o próprio tipo (lista por tipo definida em `STRONG_SIGNALS`).
- Priorização das aprovadas: `sinistro > exclusao > cobertura > obrigacao > regulatorio > conceitual > comparacao`, com distribuição entre seguradoras e preferência por páginas > 2.
- Mantém sempre as 5 perguntas manuais (`Q_manual_001..005`).
- Limpa: normaliza espaços, trunca `resposta_ideal_draft` a 600 chars, mantém `status_revisao=pendente_revisao`, anexa observação `"Selecionado automaticamente para revisão v1..."`.
- Renumera: manuais permanecem `Q_manual_*`; automáticas viram `Q001..Qnn`.
- Resultado da execução: 80 lidas → **30 na v1 (5 manuais + 25 automáticas)** + 50 rejeitadas.
- Distribuição da v1 por tipo: `exclusao 7 / conceitual 6 / sinistro 6 / cobertura 4 / obrigacao 4 / regulatorio 3`.
- Distribuição da v1 por fonte: AXA 5 / EZZE 5 / Essor 4 / Mapfre 4 / Excelsior 4 / CNSP_SUSEP 3 / TODAS 5.
- A v1 **ainda precisa de revisão humana** antes de virar dataset oficial.
- **Não chama Gemini, não chama Supabase, não apaga o draft.**

### Passo 2G — Revisão assistida + dataset oficial preliminar (CONCLUÍDO)
- [review_eval_dataset.py](./review_eval_dataset.py) implementado.
- Lê `eval/evaluation_dataset_v1.csv` e gera:
  - `eval/evaluation_dataset.csv` — **dataset oficial preliminar** com `status_revisao = aprovado_preliminar` e nova coluna `revisao_observacao` com alertas automáticos por linha.
  - `eval/evaluation_dataset_review.md` — versão legível em Markdown, para revisão humana sem abrir planilha.
- Alertas automáticos cobrem: `documento_esperado`/`pagina_esperada` vazios em perguntas automáticas, resposta ainda em estado de "Revisar manualmente", resposta curta (< 120 chars), ruído de capa/contato, e falta de termos esperados por tipo (exclusao, sinistro, cobertura, regulatorio, ou pergunta de responsabilidade civil sem termos relacionados). Quando nada dispara, a linha recebe `ok para avaliação preliminar`.
- Resultado da execução: 30 lidas → 30 salvas; 25 sem alerta e 5 com alerta (as 5 manuais, todas com `resposta ideal ainda é instrução de revisão` — comportamento esperado).
- Estados de `status_revisao` no projeto agora são três:
  1. `pendente_revisao` — gerada automaticamente (no draft e na v1).
  2. `aprovado_preliminar` — passou pela revisão assistida automática.
  3. `aprovado` — confirmada por especialista humano (passo manual).
- O script também reporta quantas linhas do `rejected.csv` foram rejeitadas por `excedeu cap` (16), disponíveis para reincorporação manual.
- **Não chama Gemini, não chama Supabase, não apaga draft/v1/rejected, não lê `.env`.**
- **Próximo passo técnico:** implementar `test_retrieval.py` — comparação de busca vetorial pura, busca híbrida (FTS) e HyDE, usando `eval/evaluation_dataset.csv` como referência.

---

## 7. Configuração de ambiente

### Versão do Python

- **Usar Python 3.11 ou 3.12.**
- **Não usar Python 3.14** — `google-genai`/`pydantic` ainda não têm compatibilidade estável no Windows com 3.14 e o import trava na construção dos modelos Pydantic.

### Criar e ativar a venv (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se houver bloqueio de política de execução no PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Instalar dependências

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Validar imports

```powershell
python --version
python -c "from google import genai; from google.genai import types; print('google-genai OK')"
```

### Configurar `.env`

Copiar `.env.example` para `.env` e preencher as três chaves descritas na seção 8. **Nunca commitar `.env`.**

---

## 8. Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave de API do Google Gemini. Obtida em https://aistudio.google.com/app/apikey. |
| `SUPABASE_URL` | **Project URL pura** do Supabase. Formato: `https://seu-projeto.supabase.co`. |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key do Supabase (necessária para `insert` em `document_chunks`). |

### ⚠️ Formato correto do `SUPABASE_URL`

A pipeline valida o `SUPABASE_URL` antes de chamar o Gemini. Use apenas a **Project URL**:

```
✅ CORRETO:   https://seu-projeto.supabase.co
❌ ERRADO:    https://seu-projeto.supabase.co/rest/v1
❌ ERRADO:    https://seu-projeto.supabase.co/auth/v1
❌ ERRADO:    https://seu-projeto.supabase.co/qualquer/path
```

O bug `PGRST125 ("Invalid path specified in request URL")` que travou a primeira tentativa de carga foi causado exatamente por uma URL com path extra. Se aparecer `PGRST125`, **primeiro verifique o `SUPABASE_URL`**.

Da mesma forma, a chamada Python usa apenas o nome da tabela (sem prefixo de schema):

```
✅ CORRETO:   supabase.table("document_chunks")
❌ ERRADO:    supabase.table("public.document_chunks")
```

---

## 9. Supabase

### Tabela oficial

- **Use sempre `public.document_chunks`.**
- **NUNCA use `public.documentos`** como destino da pipeline. Ela é legado e não está alinhada ao schema atual.

### Schema resumido

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | `bigserial primary key` | |
| `content` | `text not null` | Texto do chunk. |
| `embedding` | `vector(768)` | Embedding Gemini. |
| `nome_arquivo` | `text not null` | Nome original do PDF. |
| `pagina` | `integer not null` | Número da página. |
| `tipo` | `text not null` | `condicoes_gerais` ou `resolucao_mestre`. |
| `seguradora` | `text` | `AXA` / `Essor` / `Excelsior` / `EZZE` / `Mapfre`. Nulo para SUSEP. |
| `orgao` | `text` | `CNSP_SUSEP` para resolução. Nulo para seguradoras. |
| `enquadramento` | `text` | `grandes_riscos_407_2021`. |
| `chunk_strategy` | `text not null` | Atualmente `"page"`. |
| `chunk_index` | `integer not null` | Índice do chunk dentro do documento. |
| `token_count` | `integer` | Estimativa via `tiktoken` (`cl100k_base`). |
| `metadata` | `jsonb not null default '{}'::jsonb` | Metadados herdados do staging. |
| `created_at` | `timestamptz not null default now()` | |

### Índices criados

- `document_chunks_embedding_idx` — `ivfflat (embedding vector_cosine_ops)` com `lists=100`.
- `document_chunks_metadata_idx` — `gin (metadata)`.
- `document_chunks_content_fts_idx` — `gin (to_tsvector('portuguese', content))` (preparado para busca híbrida).
- `document_chunks_tipo_idx`, `document_chunks_seguradora_idx`, `document_chunks_nome_arquivo_idx` — btree para filtros comuns.

### RPC oficial

`public.match_document_chunks(query_embedding vector(768), match_count int default 10, match_threshold float default 0.7)`.

Retorna os chunks ordenados por similaridade de cosseno, já filtrados pelo `match_threshold`. Esta RPC é o ponto de integração da busca vetorial.

### Scripts SQL disponíveis

- [supabase_schema.sql](./supabase_schema.sql) — schema completo (DROP + CREATE da tabela, índices e RPC).
- [supabase_diagnostics.sql](./supabase_diagnostics.sql) — queries de validação (colunas, índices, RPC, contagem).
- [supabase_add_unique_constraint.sql](./supabase_add_unique_constraint.sql) — **opcional**. Aplicar manualmente apenas depois de confirmar **0 duplicidades**.

### Como rodar diagnóstico

No **SQL Editor** do Supabase, abrir e executar [supabase_diagnostics.sql](./supabase_diagnostics.sql).

### Queries úteis

Contagem total:

```sql
select count(*) from public.document_chunks;
```

Amostra dos registros:

```sql
select id, nome_arquivo, pagina, tipo, seguradora, chunk_strategy, chunk_index, token_count
from public.document_chunks
order by id
limit 10;
```

Detecção de duplicidades (deve retornar 0 linhas):

```sql
select nome_arquivo, pagina, chunk_strategy, chunk_index, count(*) as total
from public.document_chunks
group by nome_arquivo, pagina, chunk_strategy, chunk_index
having count(*) > 1;
```

Distribuição por seguradora/órgão:

```sql
select coalesce(seguradora, orgao) as fonte, count(*) as chunks
from public.document_chunks
group by 1
order by 2 desc;
```

---

## 10. Pipeline de embeddings (`create_embeddings.py`)

Características relevantes para quem retomar:

- **SDK**: `google-genai` (não usar `google-generativeai` legado).
- **Modelo**: `gemini-embedding-001`.
- **Dimensão**: `output_dimensionality=768`.
- **task_type**: `"RETRIEVAL_DOCUMENT"` para documentos. Para consultas futuras, **usar `"RETRIEVAL_QUERY"`**.
- **chunk_strategy**: atualmente `"page"` (um chunk por página válida). Evolução prevista para chunking por **artigo/cláusula** (Estratégia A do `spec.md`).
- **Filtro de página curta**: `MIN_CHARS_FOR_EMBEDDING = 30`. A página 57 da Essor cai nesse filtro e é ignorada.
- **Cache local**: `.cache/gemini_embeddings_cache.jsonl`. Chave: `sha256(model + dim + content)`. Cada linha é um JSON. **Não versionar e não apagar entre execuções** — é o que economiza quota em retentativas.
- **Retry e backoff**: exponential backoff com jitter para erro `429 RESOURCE_EXHAUSTED` (`INITIAL_RETRY_DELAY_SECONDS=30`, `MAX_RETRIES=5`).
- **Pausa**: `SLEEP_BETWEEN_EMBEDDINGS_SECONDS=5` entre chamadas reais (não dorme em DRY_RUN nem em cache hit).
- **`MAX_RECORDS`**: limita quantos chunks vão para Gemini + Supabase numa execução. Use para **escalonar a carga em blocos**. `None` libera carga completa.
- **`DRY_RUN`**: quando `True`, **não** chama Gemini e **não** insere no Supabase. Padrão de segurança.
- **Idempotência**: antes de chamar Gemini, `chunk_already_exists()` consulta `(nome_arquivo, pagina, chunk_strategy, chunk_index)` na tabela. Se o chunk já existe, é pulado.
- **Ordem de validação**: o cliente Gemini só é instanciado **depois** de validar a conexão Supabase. Isso evita queimar quota se a carga estiver quebrada.

---

## 11. Como rodar os próximos comandos

Ordem segura recomendada. Sempre com a venv ativada.

### 1. Testar conexão com o Supabase

```powershell
.\.venv\Scripts\python test_supabase_connection.py
```

Saída esperada: `Conexão bem-sucedida`. Se der `PGRST125`, revisar `SUPABASE_URL` no `.env` (ver seção 8).

### 2. Rodar a pipeline em `DRY_RUN` para revalidar o chunking

Confirmar no topo de `create_embeddings.py`:

```python
DRY_RUN = True
```

E rodar:

```powershell
.\.venv\Scripts\python create_embeddings.py
```

Saída esperada: 273 chunks preparados, 1 página ignorada, **0 chamadas Gemini, 0 inserções**.

### 3. Carga real limitada (próximo bloco)

Editar `create_embeddings.py`:

```python
DRY_RUN = False
MAX_RECORDS = 20
```

Rodar:

```powershell
.\.venv\Scripts\python create_embeddings.py
```

Conferir relatório final: chamadas Gemini, inserções, cache hits, chunks já existentes, falhas 429.

### 4. Escalonar gradualmente

Após sucesso do bloco de 20, aumentar:

```python
MAX_RECORDS = 50
```

E depois:

```python
MAX_RECORDS = 100
```

Por fim, apenas se a quota Gemini permitir:

```python
MAX_RECORDS = None
```

> Entre execuções, **não apague `.cache/`**. Em uma re-execução, embeddings em cache não consomem quota.

### 5. Validar no Supabase

Após cada bloco, rodar as queries da seção 9 (contagem total, duplicidades, distribuição).

### 6. (Opcional, depois de 0 duplicidades) aplicar a UNIQUE constraint

No SQL Editor do Supabase, executar [supabase_add_unique_constraint.sql](./supabase_add_unique_constraint.sql). Reforça idempotência em nível de banco.

---

## 12. Riscos e cuidados

- **Quota Gemini (`429 RESOURCE_EXHAUSTED`)**. Em plano gratuito, `gemini-embedding-001` tem RPM/RPD baixos. Mesmo com pausa de 5s entre chamadas, 273 chunks podem estourar o limite diário. **Nunca rodar carga completa sem antes validar blocos menores.**
- **Nunca rodar `MAX_RECORDS=None` direto**. Sempre escalonar (20 → 50 → 100 → None).
- **`SUPABASE_URL` deve ser a Project URL pura**, sem `/rest/v1`, `/auth/v1`, `/storage/v1`, `/functions/v1` ou qualquer path extra.
- **Não duplicar chunks**: a idempotência protege via `chunk_already_exists()`, e a constraint opcional reforça em nível de banco. Antes de aplicar a constraint, **verificar duplicidades existentes** (query da seção 9).
- **Não usar `public.documentos`** — é tabela legado.
- **Não expor `.env`**. Está no `.gitignore`, mas verifique antes de qualquer commit.
- **Não versionar `.cache/`**. Está coberto pelo `.gitignore`. Ele é local e essencial para economizar quota — não apague entre execuções.
- **Não usar Python 3.14**. Quebra `google-genai`/`pydantic` no Windows. Use 3.11 ou 3.12.
- **Não rodar `drop table`, `truncate` ou `delete` em massa** no Supabase sem antes confirmar com o time. A carga atual representa quota gasta e tempo investido.
- **Não alterar a lógica funcional** dos scripts (`parse_pdf.py`, `validate_staging.py`, `create_embeddings.py`, `test_supabase_connection.py`) a menos que tenha encontrado um bug evidente e documente a alteração.

---

## 13. Próximo passo técnico imediato

**Completar a carga de embeddings em blocos controlados** até atingir os 273 chunks esperados em `public.document_chunks`.

Sequência prática:

1. Rodar `test_supabase_connection.py`.
2. Rodar `create_embeddings.py` em `DRY_RUN=True` para confirmar 273 chunks preparados.
3. Carregar em blocos: `MAX_RECORDS=20` → validar → `50` → validar → `100` → validar → `None` se a quota permitir.
4. A cada bloco, rodar contagem e detecção de duplicidades (seção 9).
5. (Opcional) aplicar `supabase_add_unique_constraint.sql` manualmente após 0 duplicidades.

---

## 14. Próximas etapas depois da carga completa

Depois de atingir 273 chunks com 0 duplicidades:

1. **Implementar `test_match.py`** — script de busca vetorial básica usando a RPC `match_document_chunks`. Deve gerar embedding da pergunta com `task_type="RETRIEVAL_QUERY"` (não `RETRIEVAL_DOCUMENT`) e imprimir os top-k resultados com `nome_arquivo`, `pagina`, `seguradora`, `similarity`.
2. **Validar retorno** por fonte, página, seguradora e similaridade em pelo menos 5 perguntas-piloto (ex.: "qual a franquia mínima?", "o que é coberto sob danos materiais?", "qual seguradora exclui ataque cibernético?").
3. **Evoluir o chunking** para a Estratégia A do `spec.md`: agrupar parágrafos/incisos de um mesmo Artigo (SUSEP) ou Cláusula (CGs) num único chunk, preservando contexto de exclusões secundárias. Definir nova `chunk_strategy` (ex.: `"clause"`) para coexistir com `"page"`.
4. **Implementar busca híbrida** (vetorial + Full-Text Search em português). O índice GIN `document_chunks_content_fts_idx` já existe; falta a função SQL e o caller Python.
5. **Implementar HyDE** (Hypothetical Document Embeddings) como estratégia C de avaliação.
6. **Criar `dados/testes/dataset_testes.csv`** com perguntas, respostas ideais e regras esperadas para cada cenário.
7. **Implementar `test_retrieval.py`** — comparação das 3 modalidades de busca usando *LLM as a Judge* (nota de 0 a 1 + `TRUE/FALSE`), conforme `spec.md`.
8. **Implementar `agent.py`** — agente final com a estratégia campeã exposta como Tool, threshold inicial `0.7` e lógica de segunda tentativa autônoma (reescreve a query com sinônimos do mercado securitário, ex.: "ataque hacker" → "riscos cibernéticos", e baixa o threshold para `0.6`).

---

## 15. Definition of Done do próximo marco

Para fechar o marco **"carga vetorial completa + busca básica funcional"**:

- [ ] `public.document_chunks` com **273 registros** (ou número final validado e justificado).
- [ ] **0 duplicidades** segundo a query de detecção da seção 9.
- [ ] Distribuição por seguradora/órgão bate com o relatório do `DRY_RUN`: AXA 90 / EZZE 59 / Essor 56 / Mapfre 37 / Excelsior 25 / SUSEP 6.
- [ ] `test_match.py` criado e retornando resultados relevantes para pelo menos 5 perguntas-piloto.
- [ ] Pergunta usa `task_type="RETRIEVAL_QUERY"` (e **não** `RETRIEVAL_DOCUMENT`).
- [ ] Cada resultado traz metadados corretos: `nome_arquivo`, `pagina`, `tipo`, `seguradora`/`orgao`, `enquadramento`, `similarity`.
- [ ] (Opcional) constraint `UNIQUE (nome_arquivo, pagina, chunk_strategy, chunk_index)` aplicada via [supabase_add_unique_constraint.sql](./supabase_add_unique_constraint.sql).

---

## Apêndice — Documentos relacionados

- [spec.md](./spec.md) — especificação técnica original (SSOT dos 4 passos do projeto).
- [walkthrough.md](./walkthrough.md) — diário técnico dos passos 2A, 2B e 2C com sintomas, diagnóstico e correções.
- [task.md](./task.md) — checklist incremental com status por subitem.
