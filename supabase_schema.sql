create extension if not exists vector;

drop table if exists public.document_chunks;

create table public.document_chunks (
  id bigserial primary key,

  content text not null,
  embedding vector(768),

  nome_arquivo text not null,
  pagina integer not null,

  tipo text not null,
  seguradora text,
  orgao text,
  enquadramento text,

  chunk_strategy text not null,
  chunk_index integer not null,
  token_count integer,

  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now()
);

create index document_chunks_embedding_idx
on public.document_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create index document_chunks_metadata_idx
on public.document_chunks
using gin (metadata);

create index document_chunks_content_fts_idx
on public.document_chunks
using gin (to_tsvector('portuguese', content));

create index document_chunks_tipo_idx
on public.document_chunks (tipo);

create index document_chunks_seguradora_idx
on public.document_chunks (seguradora);

create index document_chunks_nome_arquivo_idx
on public.document_chunks (nome_arquivo);

create or replace function public.match_document_chunks (
  query_embedding vector(768),
  match_count int default 10,
  match_threshold float default 0.7
)
returns table (
  id bigint,
  content text,
  nome_arquivo text,
  pagina integer,
  tipo text,
  seguradora text,
  orgao text,
  enquadramento text,
  chunk_strategy text,
  chunk_index integer,
  token_count integer,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.content,
    dc.nome_arquivo,
    dc.pagina,
    dc.tipo,
    dc.seguradora,
    dc.orgao,
    dc.enquadramento,
    dc.chunk_strategy,
    dc.chunk_index,
    dc.token_count,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  where 1 - (dc.embedding <=> query_embedding) >= match_threshold
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;
