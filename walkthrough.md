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

### Próximos Passos
- Revisar os chunks e a estimativa de tokens do relatório
- Alterar `DRY_RUN=False` no script para executar a carga real no Supabase
- Validar os registros inseridos com `supabase_diagnostics.sql`
