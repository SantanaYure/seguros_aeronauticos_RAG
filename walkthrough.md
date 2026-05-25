> **Para onboarding e retomada do projeto, comece por [HANDOFF.md](./HANDOFF.md).**
> Este `walkthrough.md` é o diário técnico (decisões, sintomas, correções). O `HANDOFF.md` é o documento único de continuidade.

# Walkthrough - Passo 2A: Schema Supabase para Gemini

## Passo 2A: Schema Supabase para Gemini

### Visão Geral do Modelo e Embedding
- **Integração com Gemini**: O projeto foi configurado para utilizar as APIs do Gemini, e não da OpenAI.
- **Modelo de Embedding**: O modelo planejado para a vetorização é o `gemini-embedding-001`.
- **Dimensão de Embedding**: O modelo `gemini-embedding-001` gera vetores de **768 dimensões**. Por esta razão, a coluna `embedding` na tabela do banco de dados usa a definição `vector(768)`.

### Banco de Dados (Supabase)
- **Tabela Oficial**: A tabela oficial para armazenar os fragmentos e vetores do RAG é `public.document_chunks`.
- **Tabela Antiga**: A tabela antiga `public.documentos` não deve ser utilizada ou modificada nesta etapa.
- **Script do Schema**: O arquivo [supabase_schema.sql](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/supabase_schema.sql) foi criado e deve ser executado no SQL Editor do Supabase para inicializar a extensão vetorial, criar a tabela `document_chunks`, criar os índices de busca e registrar a função RPC `match_document_chunks`.
- **Verificação e Diagnóstico**: O arquivo [supabase_diagnostics.sql](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/supabase_diagnostics.sql) foi criado com queries SQL prontas para validar se a estrutura da tabela, índices e a função RPC foram criados perfeitamente no Supabase.

### Dependências e Instalação
- As dependências necessárias para a vetorização com Gemini e interação com o Supabase foram mapeadas e adicionadas ao arquivo [requirements.txt](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/requirements.txt).
- **Ajuste Técnico**: O pacote `supabase` foi pinado como `supabase<2.26.0` para evitar a dependência transitiva do `pyiceberg` (introduzida na versão 2.26.0 pelo `storage3`). Sob o Python 3.14 no Windows, o `pyiceberg` não possui wheels pré-compilados e falharia na compilação do compilador C. Pinando para `<2.26.0` removemos completamente o `pyiceberg` da árvore de dependências.
- O comando sugerido para instalar todas as dependências é:
  ```bash
  pip install -r requirements.txt
  ```


### Próximos Passos
- Na próxima etapa, implementaremos o script `create_embeddings.py` que lerá os arquivos em `staging/`, fragmentará os textos de forma semântica (conforme as estratégias A e B descritas na especificação), gerará os embeddings e fará a carga no Supabase. O script contará com um modo `DRY_RUN` para validação local antes da carga real no banco de dados.

---

## Passo 2B: create_embeddings.py em DRY_RUN

### Visão Geral
O script [`create_embeddings.py`](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/create_embeddings.py) foi implementado para gerar embeddings dos documentos em `staging/` e fazer a carga no Supabase. Por padrão, opera em modo seguro com `DRY_RUN=True`.

### Modelo e Dimensão
- **Biblioteca**: `google-genai` (nova API — `google.generativeai` foi descontinuado)
- **Modelo de embedding**: `gemini-embedding-001`
- **Dimensão**: `vector(768)` — validada explicitamente na função `get_gemini_embedding()`
- **task_type**: `RETRIEVAL_DOCUMENT` (otimizado para recuperação semântica)

### Estratégia de Chunking
- **`chunk_strategy = "page"`**: um chunk por página válida
- **`chunk_index`**: calculado por documento, ordenado por número de página (0-indexed)
- **Filtro mínimo**: páginas com menos de 30 caracteres de texto limpo são ignoradas
- **Contagem de tokens**: estimada via `tiktoken` com encoding `cl100k_base`

### Modo DRY_RUN
- Com `DRY_RUN=True` (padrão): nenhuma chamada ao Gemini, nenhuma inserção no Supabase
- Com `DRY_RUN=False`: gera embeddings reais, insere em lotes de `BATCH_SIZE=20`, com fallback para inserção individual em caso de falha de lote

### Resultados do DRY_RUN (validação local)
| Métrica | Valor |
|---|---|
| Arquivos JSON em `staging/` | 274 |
| Páginas válidas processadas | 273 |
| Páginas ignoradas (< 30 chars) | 1 |
| Chunks criados | 273 |
| Chunks `condicoes_gerais` | 267 |
| Chunks `resolucao_mestre` | 6 |

**Página ignorada**: `CG_Essor_RC_Hangar_pagina_57.json` — contém apenas `"essor.com.br"` (12 caracteres).

**Distribuição por seguradora**:
- AXA: 90 chunks
- EZZE: 59 chunks
- Essor: 56 chunks (57 páginas menos a ignorada)
- Mapfre: 37 chunks
- Excelsior: 25 chunks
- SUSEP/CNSP (resolução mestre): 6 chunks

### Dependências Atualizadas
O [`requirements.txt`](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/requirements.txt) foi atualizado:
- `google-generativeai` → **`google-genai`** (nova biblioteca oficial)
- **`h2>=3,<5`** adicionado (suporte HTTP/2 para o cliente Supabase via `httpx`)

### Versão do Python — IMPORTANTE
Use **Python 3.11** ou **3.12** neste projeto. **Evite Python 3.14**: o `google-genai` (e dependências como `pydantic`) ainda não são compatíveis com 3.14 no Windows, e o import trava durante a construção dos modelos Pydantic.

Comandos recomendados para recriar o ambiente do zero:

```powershell
# Apagar venv antigo (se existir)
Remove-Item -Recurse -Force .venv

# Criar venv com Python 3.11
py -3.11 -m venv .venv

# Ativar (PowerShell)
.\.venv\Scripts\Activate.ps1
# Se houver bloqueio de política:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\.venv\Scripts\Activate.ps1

# Instalar dependências
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Validar
python --version                                    # deve mostrar 3.11.x ou 3.12.x
python -c "from google import genai; from google.genai import types; print('google-genai OK')"

# Rodar pipeline em modo seguro
python create_embeddings.py                         # com DRY_RUN=True
```

### Próximos Passos
- Revisar os chunks e a estimativa de tokens do relatório
- Alterar `DRY_RUN=False` no script para executar a carga real no Supabase
- Validar os registros inseridos com `supabase_diagnostics.sql`

---

## Correção Passo 2C: quota Gemini e PGRST125 Supabase

### Sintomas observados na primeira carga real
Ao alterar `DRY_RUN=False` em [`create_embeddings.py`](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/create_embeddings.py) e tentar a carga real, dois erros ocorreram:

1. **Gemini `429 RESOURCE_EXHAUSTED`** ("You exceeded your current quota").
   - 87 chunks geraram embedding; 186 falharam por quota antes mesmo de tentar inserção.
2. **Supabase `PGRST125`** ("Invalid path specified in request URL").
   - Todos os 87 chunks preparados falharam na inserção (0 inseridos, 87 com falha).

### Diagnóstico
- **`429`**: A versão anterior do script não tinha pausa entre chamadas, retry com backoff, nem cache local. Isso enviou rajada de requisições e estourou a quota do Gemini imediatamente. Além disso, o erro **só foi descoberto depois** de chamar Gemini, desperdiçando quota.
- **`PGRST125`**: O PostgREST (camada que o `supabase-py` chama por baixo) responde `PGRST125` quando o path da request é inválido. As causas comuns são:
  - `SUPABASE_URL` contendo `/rest/v1` (deve ser apenas a Project URL).
  - `SUPABASE_URL` com path extra (por exemplo `https://x.supabase.co/db`).
  - Nome de tabela qualificado com schema na chamada Python (`supabase.table("public.document_chunks")` — deve ser apenas `"document_chunks"`).
- Tudo isso só foi descoberto **depois** que a pipeline já tinha gasto quota.

### Correções aplicadas em `create_embeddings.py`
- `DRY_RUN = True` por padrão.
- `MAX_RECORDS = 3` por padrão, para teste real limitado.
- `TABLE_NAME = "document_chunks"` (sem prefixo `public.`).
- Função `validate_supabase_url()`:
  - Exige `https://`.
  - Bloqueia paths como `/rest/v1`, `/auth/v1`, `/storage/v1`, `/functions/v1` e qualquer path extra.
  - Remove barra final.
  - Mensagem: *"SUPABASE_URL inválida. Use apenas a Project URL do Supabase, no formato https://seu-projeto.supabase.co. Não use URL com /rest/v1."*
- Função `validate_supabase_connection()`:
  - Executa `select id, count="exact" limit 1` em `document_chunks` antes de **qualquer** chamada Gemini.
  - Se a conexão falhar, interrompe o pipeline com diagnóstico claro.
- Retry com **exponential backoff** + jitter para `429 RESOURCE_EXHAUSTED` (`INITIAL_RETRY_DELAY_SECONDS=30`, `MAX_RETRIES=5`).
- Pausa de `SLEEP_BETWEEN_EMBEDDINGS_SECONDS=5` entre chamadas reais ao Gemini (não dorme em DRY_RUN nem em cache hit).
- **Cache local** em `.cache/gemini_embeddings_cache.jsonl` (chave `sha256(model + dim + content)`).
- **Idempotência** via `chunk_already_exists()` — verifica `(nome_arquivo, pagina, chunk_strategy, chunk_index)` antes de chamar Gemini, evitando regerar embedding de chunks que já estão no banco.
- Cliente Gemini só é instanciado **depois** de validar Supabase, para não gastar quota se a carga falhar.
- Relatório expandido (cache hits, chamadas Gemini, falhas 429, chunks já existentes, etc.).

### Novo script auxiliar
[`test_supabase_connection.py`](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/test_supabase_connection.py): testa conexão com `document_chunks` sem chamar Gemini e sem inserir nada. Deve ser executado **antes** de qualquer carga real.

### SQL opcional (não executado automaticamente)
[`supabase_add_unique_constraint.sql`](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/supabase_add_unique_constraint.sql): adiciona constraint `UNIQUE (nome_arquivo, pagina, chunk_strategy, chunk_index)` em `public.document_chunks`. Apenas executar manualmente após verificar ausência de duplicidades (query incluída no arquivo).

### Ordem segura para retomar a carga
1. Confirmar `.env` com `SUPABASE_URL` apenas no formato `https://seu-projeto.supabase.co` (sem `/rest/v1`).
2. Rodar `python test_supabase_connection.py` — deve imprimir "Conexão bem-sucedida".
3. Confirmar `DRY_RUN=True` em `create_embeddings.py` e rodar `python create_embeddings.py` — deve gerar 273 chunks sem chamar Gemini.
4. Para teste real limitado: `DRY_RUN=False` e `MAX_RECORDS=3`. Rodar `python create_embeddings.py` e confirmar 3 inserções.
5. Somente após sucesso do teste limitado, aumentar `MAX_RECORDS` (ou usar `None` para carga completa) — sempre respeitando o tempo de pausa para não estourar quota.

### Notas sobre quota Gemini
- Em conta com plano gratuito, `gemini-embedding-001` tem limites baixos de RPM/RPD. Mesmo com `SLEEP_BETWEEN_EMBEDDINGS_SECONDS=5`, uma carga de 273 chunks pode atingir o limite diário.
- O cache local garante que retentativas posteriores **não regenerem** os embeddings já obtidos, economizando quota.
- A idempotência garante que retentativas **não duplicam** dados no Supabase.
