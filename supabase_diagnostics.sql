-- 1. Verificar colunas da tabela:
select
  ordinal_position,
  column_name,
  data_type,
  udt_name,
  is_nullable,
  column_default
from information_schema.columns
where table_schema = 'public'
  and table_name = 'document_chunks'
order by ordinal_position;

-- 2. Verificar índices:
select
  indexname,
  indexdef
from pg_indexes
where schemaname = 'public'
  and tablename = 'document_chunks'
order by indexname;

-- 3. Verificar função RPC:
select
  routine_name,
  routine_type,
  data_type
from information_schema.routines
where routine_schema = 'public'
  and routine_name = 'match_document_chunks';

-- 4. Verificar quantidade de registros:
select count(*) as total_registros
from public.document_chunks;
