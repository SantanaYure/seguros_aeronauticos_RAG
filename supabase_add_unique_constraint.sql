-- ============================================================
-- supabase_add_unique_constraint.sql
-- ============================================================
-- OPCIONAL. NÃO é executado automaticamente pelo pipeline.
--
-- Adiciona uma constraint UNIQUE em public.document_chunks para a
-- chave lógica (nome_arquivo, pagina, chunk_strategy, chunk_index).
--
-- Benefício:
-- - Reforça idempotência no nível do banco, complementando a
--   verificação prévia feita por create_embeddings.py.
-- - Evita duplicidade mesmo em execuções concorrentes.
--
-- Risco:
-- - Se já existirem registros duplicados (mesma combinação dos
--   quatro campos), a criação falhará. Nesse caso será necessário
--   limpar duplicidades antes de aplicar a constraint.
--
-- Antes de aplicar, verifique duplicidades existentes:
-- ============================================================
-- select
--   nome_arquivo,
--   pagina,
--   chunk_strategy,
--   chunk_index,
--   count(*) as ocorrencias
-- from public.document_chunks
-- group by nome_arquivo, pagina, chunk_strategy, chunk_index
-- having count(*) > 1
-- order by ocorrencias desc;
-- ============================================================

-- Criar a constraint UNIQUE somente após confirmar 0 duplicidades:
alter table public.document_chunks
add constraint document_chunks_unique_chunk
unique (nome_arquivo, pagina, chunk_strategy, chunk_index);
