- [x] Passo 1: ETL e Ingestão (`parse_pdf.py` e validação do `staging/`)
- [x] Passo 2A: Preparação do Schema Supabase para Gemini
  - [x] Criar/verificar arquivo de dependências `requirements.txt`
  - [x] Atualizar `.gitignore` para incluir `.env` e caches do Python
  - [x] Criar arquivo `.env.example`
  - [x] Criar `supabase_schema.sql` com o schema do Gemini (vector(768))
  - [x] Criar `supabase_diagnostics.sql` com as queries de validação
  - [x] Criar/atualizar documentação em `walkthrough.md`
- [x] Passo 2B: Chunking e Ingestão de Embeddings
  - [x] Implementar `create_embeddings.py` com `DRY_RUN=True` por padrão
  - [x] Script lê os 274 arquivos de `staging/` e ignora páginas com < 30 chars
  - [x] 273 chunks criados (estratégia `chunk_strategy="page"`)
  - [x] Relatório completo impresso no terminal (chunks por tipo, seguradora, arquivo)
  - [x] Migrar para `google-genai` com `gemini-embedding-001` (com output_dimensionality=768)
  - [x] `requirements.txt` atualizado com `google-genai` e `h2>=3,<5`
  - [x] `walkthrough.md` atualizado com resultados do DRY_RUN
  - [x] **Correção de ambiente**: `.venv` estava usando Python 3.14 (incompatível com `google-genai`/`pydantic`)
    - Ambiente recriado com **Python 3.11.9** (`py -3.11 -m venv .venv`)
    - `requirements.txt` revisado (sem `pyiceberg`, sem `google-generativeai` legado)
    - Import validado: `from google import genai; from google.genai import types` → OK
    - `create_embeddings.py` reexecutado em `DRY_RUN=True` com sucesso (273 chunks, 1 página ignorada)
  - [x] `.gitignore` expandido (cobertura completa para Python: `.venv/`, caches, IDE, OS, logs)
  - [x] Tentativa inicial de carga real com `DRY_RUN=False` — falhou com:
    - Erro Gemini `429 RESOURCE_EXHAUSTED` (quota esgotada após 87 embeddings)
    - Erro Supabase `PGRST125` ("Invalid path specified in request URL") em todas as 87 inserções
- [x] Passo 2C: correção de quota Gemini e PGRST125 Supabase
  - [x] `create_embeddings.py` refatorado:
    - `DRY_RUN=True` por padrão; `MAX_RECORDS=3` por padrão
    - Validação de `SUPABASE_URL` (bloqueia `/rest/v1` e paths extras)
    - Validação de conexão Supabase **antes** de qualquer chamada Gemini
    - Retry com exponential backoff + jitter para `429`
    - Pausa `SLEEP_BETWEEN_EMBEDDINGS_SECONDS=5` entre chamadas reais
    - Cache local `.cache/gemini_embeddings_cache.jsonl` (chave `sha256(model+dim+content)`)
    - Idempotência via `chunk_already_exists()` por `(nome_arquivo, pagina, chunk_strategy, chunk_index)`
    - Relatório final expandido (cache hits, falhas 429, chunks já existentes etc.)
  - [x] `test_supabase_connection.py` criado — testa conexão sem chamar Gemini e sem inserir
  - [x] `supabase_add_unique_constraint.sql` criado (opcional, não executado automaticamente)
  - [x] `.gitignore` já contém `.cache/`, `__pycache__/`, `*.pyc`, `.env` (sem alterações necessárias)
  - [x] `requirements.txt` já contém `google-genai`, `supabase<2.26.0`, `python-dotenv`, `tiktoken`, `h2>=3,<5` (sem `pyiceberg` e sem `google-generativeai`)
  - [x] `walkthrough.md` atualizado com seção "Correção Passo 2C"
  - [ ] **Próximo**: rodar `python test_supabase_connection.py` para confirmar conexão
  - [ ] **Próximo**: rodar `python create_embeddings.py` com `DRY_RUN=True` para revalidar chunking
  - [ ] **Próximo**: rodar `python create_embeddings.py` com `DRY_RUN=False` e `MAX_RECORDS=3` (teste real limitado)
  - [ ] **Próximo (após sucesso)**: aumentar `MAX_RECORDS` gradualmente; carga completa só após validar parciais
  - [ ] **Próximo (opcional)**: aplicar manualmente `supabase_add_unique_constraint.sql` no SQL Editor após confirmar 0 duplicidades

- [x] Documentação de handoff
  - [x] Criado `HANDOFF.md` como documento único de continuidade técnica (PT-BR)
  - Estrutura: visão geral, objetivo, base documental, arquitetura, estrutura de arquivos, estado atual (passos 1, 2A, 2B, 2C — incluindo a carga real validada com 3 chunks), configuração de ambiente (Python 3.11/3.12, PowerShell), variáveis de ambiente, Supabase (schema, RPC, queries úteis), pipeline de embeddings, comandos PowerShell em ordem segura, riscos e DoD do próximo marco.

## Estado atual resumido
- Passo 1 concluído (274 JSONs em `staging/`, 0 erros críticos).
- Passo 2A concluído (schema Supabase aplicado, `public.document_chunks` com `vector(768)` e RPC `match_document_chunks`).
- Passo 2B concluído (`create_embeddings.py` com `google-genai`, `gemini-embedding-001`, 768d, `chunk_strategy="page"`, 273 chunks em DRY_RUN).
- Passo 2C concluído (validação Supabase antes do Gemini, cache, retry/backoff, idempotência, `test_supabase_connection.py`).
- Carga real validada com `MAX_RECORDS=3` — 3 chunks inseridos no Supabase com sucesso (0 falhas).
- Faltam **270 chunks** para completar a carga.

## Próximo passo recomendado
- Continuar a carga em blocos controlados via `create_embeddings.py`:
  `MAX_RECORDS=20` → validar → `50` → validar → `100` → validar → `None` (somente se a quota Gemini permitir).
- Após cada bloco, rodar a query de contagem e a query de detecção de duplicidades (ver [HANDOFF.md](./HANDOFF.md#9-supabase)).
- Depois da carga completa, rodar `test_match.py` (já criado — ver Passo 2D abaixo).

- [x] Passo 2D: teste de busca vetorial básica (Retrieval)
  - [x] Criado `test_match.py` na raiz do projeto
  - [x] Testa SOMENTE o "R" do RAG (Retrieval). Não gera resposta com LLM.
  - [x] Usa SDK `google-genai` com `gemini-embedding-001`, `output_dimensionality=768`, `task_type="RETRIEVAL_QUERY"`
  - [x] Chama a RPC `public.match_document_chunks` (`match_count=8`, `match_threshold=0.5`)
  - [x] Valida Supabase ANTES de chamar Gemini (mesmo padrão de `create_embeddings.py`)
  - [x] Não insere, não altera, não apaga — apenas SELECT seguro e RPC de leitura
  - [x] Suporta CLI: `python test_match.py` roda `TEST_QUESTIONS`; `python test_match.py --question "..."` roda pergunta única
  - [x] Perguntas iniciais (`TEST_QUESTIONS`):
    1. "O que é casco aeronáutico?"
    2. "O seguro cobre pane seca?"
    3. "O que significa exclusão operacional?"
    4. "O que é responsabilidade civil no seguro aeronáutico?"
    5. "Quando a seguradora pode negar indenização?"
  - [x] Imprime, para cada chunk, `nome_arquivo`, `pagina`, `tipo`, `seguradora`/`orgao`, `chunk_strategy`, `chunk_index`, `token_count`, `similarity` (4 casas) e trecho do `content` (até 900 chars)
  - [x] Imprime linha de avaliação manual (`OK / PARCIAL / RUIM / NÃO ENCONTRADO`) após cada pergunta
  - [x] Relatório final com totais, threshold e aviso explícito de que **não** houve geração de resposta com LLM
  - [ ] **Próximo (avaliação)**: rodar `python test_match.py` e marcar manualmente cada pergunta como `OK / PARCIAL / RUIM / NÃO ENCONTRADO`
  - [ ] **Próximo (calibração)**: se necessário, ajustar `MATCH_THRESHOLD` (0.5 → 0.6 → 0.7) e/ou `MATCH_COUNT`
  - [ ] **Próximo (ampliação)**: ampliar `TEST_QUESTIONS` com perguntas específicas por seguradora e por artigo da SUSEP 407/2021
  - [ ] **Próximo (objetivo)**: avaliar qualitativamente a relevância dos chunks recuperados antes de evoluir para chunking por artigo/cláusula, busca híbrida e HyDE

- [x] Passo 2E: dataset DRAFT de avaliação (a partir de `staging/`)
  - [x] Criado `generate_eval_dataset.py` (lê os 274 JSONs e gera perguntas por gatilhos lexicais)
  - [x] Pasta `eval/` criada
  - [x] Gerado `eval/evaluation_dataset_draft.csv` com 80 linhas (5 perguntas manuais + 75 automáticas)
  - [x] Distribuição cobre AXA, Essor, EZZE, Excelsior, Mapfre, CNSP_SUSEP e TODAS (manuais)
  - [x] Distribuição por tipo: sinistro, exclusao, cobertura, conceitual, obrigacao, regulatorio
  - [x] CSV respeita: até 80 linhas, sem duplicidades, todas as linhas com `status_revisao = pendente_revisao`
  - [x] Páginas com texto < 30 caracteres são ignoradas
  - [x] Round-robin entre fontes garante representatividade de todas as seguradoras + SUSEP
  - [x] Criado `eval/README.md` explicando draft, v1, rejected e fluxo de revisão humana
  - [x] Não chama Gemini, não chama Supabase, não toca `staging/`, não lê `.env`
  - [ ] **Próximo**: revisão humana das linhas de `eval/evaluation_dataset_v1.csv` (preferível trabalhar a partir da v1, não do draft)

- [x] Passo 2F: curadoria automática do dataset DRAFT
  - [x] Criado `curate_eval_dataset.py` que filtra o draft e gera duas saídas:
    - `eval/evaluation_dataset_v1.csv` (até 30 linhas, manuais + automáticas filtradas e renumeradas)
    - `eval/evaluation_dataset_rejected.csv` (linhas removidas + coluna `motivo_rejeicao`)
  - [x] Filtros de rejeição: resposta vazia/curta, pontos de índice/sumário, termos de capa/contato/registro, fragmentos de palavra no início do trecho, e falta de sinal forte para o tipo da pergunta
  - [x] Priorização dos aprovados: sinistro > exclusao > cobertura > obrigacao > regulatorio > conceitual > comparacao, com distribuição entre seguradoras e preferência por páginas > 2
  - [x] Mantém as 5 perguntas manuais sempre na v1
  - [x] Limpeza: collapse de espaços, truncamento da resposta a 600 caracteres, `status_revisao` permanece `pendente_revisao`, observação enriquecida
  - [x] Renumeração: manuais permanecem `Q_manual_001..005`; automáticas viram `Q001..Qnn`
  - [x] Não chama Gemini, não chama Supabase, não apaga o draft, não lê `.env`
  - [x] Resultado da execução: 80 linhas lidas → 30 na v1 (5 manuais + 25 automáticas) e 50 rejeitadas

- [x] Passo 2G: revisão assistida + promoção ao dataset oficial preliminar
  - [x] Criado `review_eval_dataset.py` que lê `eval/evaluation_dataset_v1.csv` e gera:
    - `eval/evaluation_dataset.csv` (dataset oficial preliminar)
    - `eval/evaluation_dataset_review.md` (versão legível em Markdown para revisão humana)
  - [x] Normaliza espaços em todas as colunas textuais
  - [x] Troca `status_revisao` de `pendente_revisao` para `aprovado_preliminar` em todas as linhas
  - [x] Adiciona a coluna `revisao_observacao` com alertas automáticos por linha:
    - `documento_esperado vazio` / `pagina_esperada vazia` (apenas em perguntas automáticas)
    - `resposta ideal ainda é instrução de revisão`
    - `resposta ideal curta` (< 120 chars)
    - `possível ruído de capa ou contato`
    - `resposta pode não explicar responsabilidade civil`
    - `resposta pode não conter exclusão substantiva` / `fundamento de sinistro` / `fundamento de cobertura` / `fundamento regulatório`
    - `ok para avaliação preliminar` quando nenhum alerta dispara
  - [x] Reporta no terminal quantas linhas do `rejected.csv` foram rejeitadas por `excedeu cap` (16) — disponíveis para reincorporação manual
  - [x] Resultado da execução: 30 linhas lidas → 30 salvas, 25 sem alerta e 5 com alerta (as 5 manuais começam com "Revisar manualmente:")
  - [x] Não chama Gemini, não chama Supabase, não apaga draft/v1/rejected, não lê `.env`
  - [x] `eval/README.md`, `task.md` e `HANDOFF.md` atualizados com a nova etapa e os 3 estados de `status_revisao` (`pendente_revisao` → `aprovado_preliminar` → `aprovado`)
  - [ ] **Próximo**: revisão humana de cada linha do `eval/evaluation_dataset.csv` (consultar `eval/evaluation_dataset_review.md`, ler `revisao_observacao`, ajustar `resposta_ideal_draft`/`documento_esperado`/`pagina_esperada` quando necessário e trocar `status_revisao` para `aprovado`)
  - [ ] **Próximo**: opcionalmente reincorporar manualmente linhas boas do `rejected.csv` marcadas como `excedeu cap`
  - [ ] **Próximo (etapa 3)**: implementar `test_retrieval.py` — comparação de busca vetorial pura, busca híbrida (FTS) e HyDE, usando `evaluation_dataset.csv` como referência
