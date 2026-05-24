# Lista de Tarefas - RAG Seguros Aeronáuticos

- [x] Passo 1: ETL e Ingestão (`parse_pdf.py` e validação do `staging/`)
- [x] Passo 2A: Preparação do Schema Supabase para Gemini
  - [x] Criar/verificar arquivo de dependências `requirements.txt`
  - [x] Atualizar `.gitignore` para incluir `.env` e caches do Python
  - [x] Criar arquivo `.env.example`
  - [x] Criar `supabase_schema.sql` com o schema do Gemini (vector(768))
  - [x] Criar `supabase_diagnostics.sql` com as queries de validação
  - [x] Criar/atualizar documentação em `walkthrough.md`
- [ ] Passo 2B: Chunking e Ingestão de Embeddings
  - [ ] Implementar `create_embeddings.py` (com suporte a DRY_RUN e estratégias A/B)
