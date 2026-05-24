import os
import sys
import json
import time
import random
import hashlib
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

import tiktoken
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client

# =====================================================================
# CONFIGURAÇÕES E PARÂMETROS
# =====================================================================

# Segurança: por padrão NÃO chama Gemini e NÃO insere no Supabase.
DRY_RUN = False

# Limita o número de chunks processados quando DRY_RUN=False.
# Use 3 para teste real limitado. Use None para carga completa
# (somente após validar o teste limitado).
MAX_RECORDS = None

# Caminhos e nomes
STAGING_DIR = Path("staging")
EMBEDDING_CACHE_PATH = Path(".cache/gemini_embeddings_cache.jsonl")
TABLE_NAME = "document_chunks"

# Configuração de embedding
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768
EMBEDDING_TASK_TYPE = "RETRIEVAL_DOCUMENT"
MIN_CHARS_FOR_EMBEDDING = 30

# Controle de quota / rate limit
SLEEP_BETWEEN_EMBEDDINGS_SECONDS = 5
MAX_RETRIES = 5
INITIAL_RETRY_DELAY_SECONDS = 30

# =====================================================================
# VALIDAÇÃO DE URL DO SUPABASE (prevenção do erro PGRST125)
# =====================================================================

class SupabaseUrlError(ValueError):
    pass


def validate_supabase_url(raw_url: str) -> str:
    """
    Valida e normaliza a SUPABASE_URL.

    Regras:
    - Deve começar com https://
    - Deve ser uma Project URL do Supabase: https://<projeto>.supabase.co
    - Não pode conter paths como /rest/v1, /auth/v1, /storage/v1, /functions/v1
    - Remove barra final, se houver
    """
    if not raw_url or not isinstance(raw_url, str):
        raise SupabaseUrlError(
            "SUPABASE_URL ausente. Defina no .env com o formato "
            "https://seu-projeto.supabase.co"
        )

    url = raw_url.strip().rstrip("/")

    if not url.startswith("https://"):
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Use apenas a Project URL do Supabase, "
            "no formato https://seu-projeto.supabase.co. Não use URL com /rest/v1."
        )

    parsed = urlparse(url)
    host = parsed.netloc or ""
    path = parsed.path or ""

    # Path deve ser vazio ou apenas "/"
    if path not in ("", "/"):
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Use apenas a Project URL do Supabase, "
            "no formato https://seu-projeto.supabase.co. Não use URL com /rest/v1."
        )

    forbidden = ("/rest/v1", "/auth/v1", "/storage/v1", "/functions/v1")
    if any(token in url for token in forbidden):
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Use apenas a Project URL do Supabase, "
            "no formato https://seu-projeto.supabase.co. Não use URL com /rest/v1."
        )

    # Domínio mínimo: deve terminar em .supabase.co (ou .supabase.in para alguns ambientes)
    # Não bloqueamos sufixos alternativos, apenas exigimos a presença do host.
    if not host or "." not in host:
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Use apenas a Project URL do Supabase, "
            "no formato https://seu-projeto.supabase.co."
        )

    return url


def validate_supabase_connection(supabase: Client) -> None:
    """
    Testa conexão com Supabase fazendo um SELECT seguro (sem inserir nada).
    Deve falhar com mensagem clara se a tabela document_chunks estiver
    inacessível.
    """
    try:
        response = (
            supabase.table(TABLE_NAME)
            .select("id", count="exact")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        print("[CRITICAL ERROR] Falha ao validar conexão com Supabase.")
        print(f"  Detalhes: {exc}")
        print("  Verifique:")
        print("  - SUPABASE_URL (apenas Project URL, sem /rest/v1)")
        print("  - SUPABASE_SERVICE_ROLE_KEY (correta e não expirada)")
        print(f"  - Existência da tabela {TABLE_NAME} no schema public")
        print(f"  - TABLE_NAME no script: deve ser \"{TABLE_NAME}\"")
        print("  Pipeline interrompida ANTES de qualquer chamada ao Gemini.")
        sys.exit(1)

    total = getattr(response, "count", None)
    if total is None:
        total = "?"
    print(f"  [OK] Conexão com Supabase validada. Registros existentes: {total}")


# =====================================================================
# CACHE LOCAL DE EMBEDDINGS
# =====================================================================

def compute_cache_key(model: str, dimension: int, content: str) -> str:
    """
    Gera chave determinística para um embedding.
    Inclui modelo + dimensão + conteúdo, para invalidar cache
    em caso de mudança de modelo ou dimensão.
    """
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"|")
    h.update(str(dimension).encode("utf-8"))
    h.update(b"|")
    h.update(content.encode("utf-8"))
    return h.hexdigest()


def load_embedding_cache(path: Path) -> dict:
    """
    Carrega o cache de embeddings em memória (mapping cache_key -> embedding).
    Linhas inválidas são ignoradas silenciosamente, sem corromper o cache.
    """
    cache: dict[str, list[float]] = {}
    if not path.exists():
        return cache

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = entry.get("cache_key")
                embedding = entry.get("embedding")
                if (
                    isinstance(key, str)
                    and isinstance(embedding, list)
                    and len(embedding) == EMBEDDING_DIMENSION
                ):
                    cache[key] = embedding
    except Exception as exc:
        print(f"  [WARNING] Falha ao ler cache existente: {exc}")
        return {}

    return cache


def append_embedding_to_cache(
    path: Path,
    cache_key: str,
    nome_arquivo: str,
    pagina: int,
    chunk_strategy: str,
    chunk_index: int,
    content_hash: str,
    embedding: list[float],
) -> None:
    """
    Persiste um único embedding no cache (append-only JSONL).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "cache_key": cache_key,
        "model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "content_hash": content_hash,
        "nome_arquivo": nome_arquivo,
        "pagina": pagina,
        "chunk_strategy": chunk_strategy,
        "chunk_index": chunk_index,
        "embedding": embedding,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# =====================================================================
# GEMINI: chamada com retry e backoff
# =====================================================================

def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    if "429" in msg:
        return True
    if "resource_exhausted" in msg or "resource exhausted" in msg:
        return True
    if "quota" in msg:
        return True
    if "rate limit" in msg or "rate-limit" in msg:
        return True
    return False


def get_gemini_embedding(text: str, client: genai.Client) -> list[float]:
    """
    Chama a API do Gemini para gerar embedding (sem retry).
    Valida que o vetor retornado possui EMBEDDING_DIMENSION dimensões.
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=EMBEDDING_TASK_TYPE,
            output_dimensionality=EMBEDDING_DIMENSION,
        ),
    )

    if not result.embeddings or not result.embeddings[0].values:
        raise ValueError(
            f"Resposta do Gemini sem embedding válido para texto de "
            f"{len(text)} caracteres."
        )

    embedding = result.embeddings[0].values
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Dimensão incorreta do embedding. "
            f"Esperado: {EMBEDDING_DIMENSION}, obtido: {len(embedding)}"
        )
    return embedding


def get_gemini_embedding_with_retry(
    text: str, client: genai.Client
) -> tuple[list[float] | None, str | None, bool]:
    """
    Chama o Gemini com retry + exponential backoff para erros 429.
    Retorna (embedding, erro, foi_rate_limit).

    - Se sucesso: (embedding, None, False)
    - Se falha não-quota: (None, mensagem, False)
    - Se falha por quota após esgotar retries: (None, mensagem, True)
    """
    delay = INITIAL_RETRY_DELAY_SECONDS
    last_error: str | None = None
    hit_rate_limit = False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            embedding = get_gemini_embedding(text, client)
            return embedding, None, hit_rate_limit
        except Exception as exc:
            last_error = str(exc)
            if _is_rate_limit_error(exc):
                hit_rate_limit = True
                if attempt >= MAX_RETRIES:
                    print(
                        f"    [ERROR] Quota Gemini esgotada após {MAX_RETRIES} "
                        f"tentativas. Abortando este chunk."
                    )
                    break
                jitter = random.uniform(0, min(5, delay * 0.1))
                wait = delay + jitter
                print(
                    f"    [WARN] 429 RESOURCE_EXHAUSTED na tentativa {attempt}/"
                    f"{MAX_RETRIES}. Aguardando {wait:.1f}s antes de retry."
                )
                time.sleep(wait)
                delay *= 2
                continue
            # Erro não-quota: não retentar
            print(
                f"    [ERROR] Falha não-quota ao chamar Gemini "
                f"(tentativa {attempt}): {exc}"
            )
            break

    return None, last_error, hit_rate_limit


# =====================================================================
# SUPABASE: idempotência e inserção
# =====================================================================

def chunk_already_exists(
    supabase: Client,
    nome_arquivo: str,
    pagina: int,
    chunk_strategy: str,
    chunk_index: int,
) -> bool:
    """
    Verifica se já existe um registro em document_chunks com
    a mesma chave lógica (nome_arquivo, pagina, chunk_strategy, chunk_index).
    """
    try:
        response = (
            supabase.table(TABLE_NAME)
            .select("id")
            .eq("nome_arquivo", nome_arquivo)
            .eq("pagina", pagina)
            .eq("chunk_strategy", chunk_strategy)
            .eq("chunk_index", chunk_index)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        print(
            f"    [WARN] Falha ao verificar duplicidade "
            f"({nome_arquivo} pág. {pagina}): {exc}"
        )
        # Em caso de falha, assumimos que NÃO existe para não bloquear,
        # mas a inserção pode falhar adiante e será reportada.
        return False

    data = getattr(response, "data", None) or []
    return len(data) > 0


def insert_chunk(supabase: Client, record: dict) -> tuple[bool, str | None]:
    """
    Insere um único chunk em document_chunks.
    Retorna (sucesso, erro).
    """
    try:
        supabase.table(TABLE_NAME).insert(record).execute()
        return True, None
    except Exception as exc:
        return False, str(exc)


# =====================================================================
# CHUNKING (sem embedding)
# =====================================================================

def build_chunk_records_from_staging(
    json_files: list[Path],
) -> tuple[list[dict], list[dict]]:
    """
    Lê staging/ e produz registros (sem embedding).
    Retorna (chunks_preparados, paginas_ignoradas).
    """
    ignored_pages: list[dict] = []
    raw_pages: list[dict] = []

    for path in json_files:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[WARNING] Falha ao carregar JSON {path.name}: {exc}")
            continue

        texto = data.get("texto", "")
        texto_limpo = texto.strip()

        if len(texto_limpo) < MIN_CHARS_FOR_EMBEDDING:
            ignored_pages.append(
                {
                    "filename": path.name,
                    "nome_arquivo": data.get("nome_arquivo", "Desconhecido"),
                    "pagina": data.get("pagina", 0),
                    "chars": len(texto_limpo),
                }
            )
            continue

        raw_pages.append(data)

    raw_pages.sort(
        key=lambda x: (x.get("nome_arquivo", ""), x.get("pagina", 0))
    )

    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.get_encoding("gpt-4")

    document_chunk_counters: Counter = Counter()
    prepared: list[dict] = []

    for page_data in raw_pages:
        nome_arquivo = page_data["nome_arquivo"]
        pagina = page_data["pagina"]
        texto = page_data["texto"]
        metadata_original = page_data.get("metadata", {})

        tipo = metadata_original.get("tipo", "condicoes_gerais")
        seguradora = metadata_original.get("seguradora")
        orgao = metadata_original.get("orgao")
        enquadramento = metadata_original.get("enquadramento")

        chunk_index = document_chunk_counters[nome_arquivo]
        document_chunk_counters[nome_arquivo] += 1

        token_count = len(encoding.encode(texto))

        record = {
            "content": texto,
            "embedding": None,
            "nome_arquivo": nome_arquivo,
            "pagina": pagina,
            "tipo": tipo,
            "seguradora": seguradora if seguradora else None,
            "orgao": orgao if orgao else None,
            "enquadramento": enquadramento if enquadramento else None,
            "chunk_strategy": "page",
            "chunk_index": chunk_index,
            "token_count": token_count,
            "metadata": {
                **metadata_original,
                "nome_arquivo": nome_arquivo,
                "pagina": pagina,
                "chunk_strategy": "page",
                "chunk_index": chunk_index,
            },
        }
        prepared.append(record)

    return prepared, ignored_pages


# =====================================================================
# RELATÓRIO
# =====================================================================

def print_dry_run_report(
    total_json_found: int,
    raw_pages_count: int,
    ignored_pages: list[dict],
    prepared_chunks: list[dict],
) -> None:
    print("\n" + "=" * 60)
    print("RELATÓRIO DE EXECUÇÃO (DRY_RUN)")
    print("=" * 60)
    print(f"DRY_RUN: True")
    print(f"MAX_RECORDS: {MAX_RECORDS}")
    print(f"Total de arquivos JSON em staging/: {total_json_found}")
    print(f"Páginas válidas processadas: {raw_pages_count}")
    print(
        f"Páginas ignoradas (< {MIN_CHARS_FOR_EMBEDDING} chars): "
        f"{len(ignored_pages)}"
    )
    print(f"Chunks criados: {len(prepared_chunks)}")

    chunks_by_tipo = Counter(c["tipo"] for c in prepared_chunks)
    if chunks_by_tipo:
        print("\nChunks por tipo:")
        for t, c in chunks_by_tipo.items():
            print(f"  - {t}: {c}")

    chunks_by_seg = Counter(
        c["seguradora"] for c in prepared_chunks if c["seguradora"]
    )
    if chunks_by_seg:
        print("\nChunks por seguradora:")
        for s, c in chunks_by_seg.items():
            print(f"  - {s}: {c}")

    if ignored_pages:
        print("\nPáginas ignoradas por texto muito curto:")
        for ip in ignored_pages:
            print(
                f"  - {ip['filename']} ({ip['nome_arquivo']}, "
                f"pág. {ip['pagina']}): {ip['chars']} caracteres"
            )

    print("\nExemplos dos 3 primeiros chunks:")
    for idx, chunk in enumerate(prepared_chunks[:3]):
        print(f"\n--- Exemplo {idx + 1} ---")
        print(f"Arquivo: {chunk['nome_arquivo']}")
        print(f"Página: {chunk['pagina']}")
        print(f"Tipo: {chunk['tipo']}")
        print(f"Seguradora/Órgão: {chunk['seguradora'] or chunk['orgao']}")
        print(f"Token Count: {chunk['token_count']}")
        truncated = chunk["content"][:300].replace("\n", " ")
        print(f"Conteúdo (primeiros 300 chars): \"{truncated}...\"")

    print("\n" + "!" * 60)
    print(
        "AVISO: DRY_RUN=True, nenhuma chamada de embedding foi feita "
        "e nada foi inserido no Supabase."
    )
    print("!" * 60)
    print(
        "\nPróximo passo sugerido:\n"
        "  1. python test_supabase_connection.py\n"
        "  2. Se OK, definir DRY_RUN=False e MAX_RECORDS=3 e rodar:\n"
        "     python create_embeddings.py\n"
        "  3. Validar inserção e SOMENTE depois ajustar MAX_RECORDS=None."
    )


def print_real_run_report(
    total_json_found: int,
    raw_pages_count: int,
    ignored_pages: list[dict],
    prepared_chunks: list[dict],
    considered_chunks: int,
    already_existing: int,
    cache_hits: int,
    gemini_calls: int,
    embedding_failures: int,
    rate_limit_failures: int,
    inserted: int,
    insert_failures: int,
    supabase_error_samples: list[str],
    gemini_error_samples: list[str],
) -> None:
    print("\n" + "=" * 60)
    print("RELATÓRIO DE EXECUÇÃO")
    print("=" * 60)
    print(f"DRY_RUN: False")
    print(f"MAX_RECORDS: {MAX_RECORDS}")
    print(f"Total de arquivos JSON em staging/: {total_json_found}")
    print(f"Páginas válidas processadas: {raw_pages_count}")
    print(
        f"Páginas ignoradas (< {MIN_CHARS_FOR_EMBEDDING} chars): "
        f"{len(ignored_pages)}"
    )
    print(f"Chunks criados: {len(prepared_chunks)}")
    print(f"Chunks considerados para carga real: {considered_chunks}")
    print(f"Chunks já existentes no Supabase (pulados): {already_existing}")
    print(f"Embeddings recuperados do cache: {cache_hits}")
    print(f"Chamadas reais ao Gemini: {gemini_calls}")
    print(f"Embeddings que falharam: {embedding_failures}")
    print(f"  - dos quais por 429/quota: {rate_limit_failures}")
    print(f"Chunks inseridos no Supabase: {inserted}")
    print(f"Chunks com falha de inserção: {insert_failures}")

    if supabase_error_samples:
        print("\nErros Supabase (amostra):")
        for e in supabase_error_samples[:5]:
            print(f"  - {e}")
    if gemini_error_samples:
        print("\nErros Gemini (amostra):")
        for e in gemini_error_samples[:5]:
            print(f"  - {e}")

    print("\nPróximos passos sugeridos:")
    if rate_limit_failures > 0:
        print(
            "  - Quota Gemini foi atingida. Aguarde reset, aumente "
            "SLEEP_BETWEEN_EMBEDDINGS_SECONDS ou revise plano de billing."
        )
    if insert_failures > 0:
        print(
            "  - Inspecione erros de inserção (PGRST*). Verifique "
            "SUPABASE_URL e nome da tabela."
        )
    if (
        rate_limit_failures == 0
        and insert_failures == 0
        and embedding_failures == 0
    ):
        print(
            "  - Carga limitada bem-sucedida. Para ampliar, ajuste "
            "MAX_RECORDS e rode novamente. NÃO use MAX_RECORDS=None "
            "sem antes confirmar a carga limitada."
        )


# =====================================================================
# PIPELINE PRINCIPAL
# =====================================================================

def main() -> None:
    print("INICIALIZANDO PIPELINE DE EMBEDDINGS")
    print("=" * 60)
    print(f"DRY_RUN={DRY_RUN}  MAX_RECORDS={MAX_RECORDS}")
    print(
        f"Modelo: {EMBEDDING_MODEL} | Dimensão: {EMBEDDING_DIMENSION} | "
        f"Task: {EMBEDDING_TASK_TYPE}"
    )
    print("=" * 60)

    # 1. Carregar variáveis de ambiente
    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    supabase_url_raw = os.getenv("SUPABASE_URL")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # 2. Validar variáveis obrigatórias
    missing = []
    if not gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not supabase_url_raw:
        missing.append("SUPABASE_URL")
    if not supabase_service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        print(
            f"[CRITICAL ERROR] Variáveis de ambiente ausentes: "
            f"{', '.join(missing)}"
        )
        print("Preencha o .env com base em .env.example.")
        sys.exit(1)

    # 3. Validar SUPABASE_URL (prevenção PGRST125)
    try:
        supabase_url = validate_supabase_url(supabase_url_raw)
    except SupabaseUrlError as exc:
        print(f"[CRITICAL ERROR] {exc}")
        print("Pipeline interrompida ANTES de qualquer chamada ao Gemini.")
        sys.exit(1)

    print(f"  [OK] SUPABASE_URL validada (host={urlparse(supabase_url).netloc}).")

    # 4. Criar cliente Supabase
    try:
        supabase: Client = create_client(
            supabase_url, supabase_service_role_key
        )
    except Exception as exc:
        print(f"[CRITICAL ERROR] Falha ao criar cliente Supabase: {exc}")
        sys.exit(1)

    # 5. Validar conexão Supabase ANTES de qualquer chamada Gemini
    print("Validando conexão com Supabase...")
    validate_supabase_connection(supabase)

    # 6. Ler staging/
    if not STAGING_DIR.exists():
        print(
            f"[CRITICAL ERROR] Pasta de staging não encontrada: "
            f"{STAGING_DIR.resolve()}"
        )
        sys.exit(1)

    json_files = sorted(STAGING_DIR.glob("*.json"))
    total_json_found = len(json_files)
    if total_json_found == 0:
        print(
            f"[CRITICAL ERROR] Nenhum JSON em {STAGING_DIR.resolve()}"
        )
        sys.exit(1)
    print(f"Arquivos JSON encontrados em staging/: {total_json_found}")

    # 7. Criar chunks (sem embeddings)
    prepared_chunks, ignored_pages = build_chunk_records_from_staging(json_files)
    raw_pages_count = len(prepared_chunks)
    print(f"Chunks preparados (sem embedding): {raw_pages_count}")

    # 8. DRY_RUN: relatório e fim
    if DRY_RUN:
        print_dry_run_report(
            total_json_found=total_json_found,
            raw_pages_count=raw_pages_count,
            ignored_pages=ignored_pages,
            prepared_chunks=prepared_chunks,
        )
        return

    # 9. Carga real: aplicar MAX_RECORDS
    if MAX_RECORDS is not None:
        if not isinstance(MAX_RECORDS, int) or MAX_RECORDS < 0:
            print(
                "[CRITICAL ERROR] MAX_RECORDS deve ser None ou inteiro >= 0."
            )
            sys.exit(1)
        chunks_to_process = prepared_chunks[:MAX_RECORDS]
        print(
            f"\n[REAL] Limitando carga real a {MAX_RECORDS} chunks "
            f"(de {len(prepared_chunks)} disponíveis)."
        )
    else:
        chunks_to_process = prepared_chunks
        print(
            f"\n[REAL] MAX_RECORDS=None: processando todos os "
            f"{len(prepared_chunks)} chunks."
        )

    # 10. Configurar cliente Gemini SOMENTE agora (após validar Supabase)
    print("Configurando cliente Gemini...")
    try:
        gemini_client = genai.Client(api_key=gemini_api_key)
    except Exception as exc:
        print(f"[CRITICAL ERROR] Falha ao criar cliente Gemini: {exc}")
        sys.exit(1)

    # 11. Carregar cache local de embeddings
    EMBEDDING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = load_embedding_cache(EMBEDDING_CACHE_PATH)
    print(f"Cache local de embeddings carregado: {len(cache)} entradas.")

    # 12. Processar chunk a chunk
    considered_chunks = len(chunks_to_process)
    already_existing = 0
    cache_hits = 0
    gemini_calls = 0
    embedding_failures = 0
    rate_limit_failures = 0
    inserted = 0
    insert_failures = 0
    supabase_error_samples: list[str] = []
    gemini_error_samples: list[str] = []

    print("\nIniciando processamento real...")
    for i, record in enumerate(chunks_to_process, start=1):
        nome_arquivo = record["nome_arquivo"]
        pagina = record["pagina"]
        chunk_strategy = record["chunk_strategy"]
        chunk_index = record["chunk_index"]

        print(
            f"\n[{i}/{considered_chunks}] {nome_arquivo} "
            f"pág. {pagina} idx {chunk_index}"
        )

        # 12.1 Idempotência: pular se já existe
        if chunk_already_exists(
            supabase, nome_arquivo, pagina, chunk_strategy, chunk_index
        ):
            print("    [SKIP] já existe no Supabase, pulando.")
            already_existing += 1
            continue

        # 12.2 Cache local
        content = record["content"]
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        cache_key = compute_cache_key(
            EMBEDDING_MODEL, EMBEDDING_DIMENSION, content
        )

        embedding = cache.get(cache_key)
        if embedding is not None:
            print("    [CACHE] embedding recuperado do cache local.")
            cache_hits += 1
        else:
            # 12.3 Chamar Gemini com retry/backoff
            embedding, err, hit_rl = get_gemini_embedding_with_retry(
                content, gemini_client
            )
            gemini_calls += 1
            if embedding is None:
                embedding_failures += 1
                if hit_rl:
                    rate_limit_failures += 1
                if err:
                    gemini_error_samples.append(
                        f"{nome_arquivo} pág. {pagina}: {err[:200]}"
                    )
                # Pausa breve mesmo em falha, para não martelar o serviço
                time.sleep(min(SLEEP_BETWEEN_EMBEDDINGS_SECONDS, 5))
                continue

            # Sucesso: salvar no cache
            try:
                append_embedding_to_cache(
                    EMBEDDING_CACHE_PATH,
                    cache_key=cache_key,
                    nome_arquivo=nome_arquivo,
                    pagina=pagina,
                    chunk_strategy=chunk_strategy,
                    chunk_index=chunk_index,
                    content_hash=content_hash,
                    embedding=embedding,
                )
                cache[cache_key] = embedding
            except Exception as exc:
                print(f"    [WARN] Falha ao salvar no cache local: {exc}")

            # Pausa entre chamadas reais ao Gemini
            time.sleep(SLEEP_BETWEEN_EMBEDDINGS_SECONDS)

        # 12.4 Inserir no Supabase
        record_to_insert = dict(record)
        record_to_insert["embedding"] = embedding

        ok, ins_err = insert_chunk(supabase, record_to_insert)
        if ok:
            print("    [OK] inserido no Supabase.")
            inserted += 1
        else:
            insert_failures += 1
            print(f"    [ERROR] falha ao inserir: {ins_err}")
            if ins_err:
                supabase_error_samples.append(
                    f"{nome_arquivo} pág. {pagina}: {ins_err[:200]}"
                )

    # 13. Relatório final
    print_real_run_report(
        total_json_found=total_json_found,
        raw_pages_count=raw_pages_count,
        ignored_pages=ignored_pages,
        prepared_chunks=prepared_chunks,
        considered_chunks=considered_chunks,
        already_existing=already_existing,
        cache_hits=cache_hits,
        gemini_calls=gemini_calls,
        embedding_failures=embedding_failures,
        rate_limit_failures=rate_limit_failures,
        inserted=inserted,
        insert_failures=insert_failures,
        supabase_error_samples=supabase_error_samples,
        gemini_error_samples=gemini_error_samples,
    )


if __name__ == "__main__":
    main()
