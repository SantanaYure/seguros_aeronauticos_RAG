"""
test_match.py

Testa SOMENTE o Retrieval do RAG (o "R" de RAG).

Faz:
- Carrega .env
- Valida variáveis obrigatórias (GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
- Valida SUPABASE_URL (Project URL pura)
- Cria cliente Supabase e valida conexão com document_chunks (SELECT seguro)
- Cria cliente Gemini
- Para cada pergunta:
    * Gera embedding com gemini-embedding-001 / 768d / task_type=RETRIEVAL_QUERY
    * Chama a RPC match_document_chunks no Supabase
    * Imprime os chunks recuperados com fonte, página, similaridade e trecho

Não faz:
- Não chama LLM para gerar resposta final
- Não insere, atualiza, apaga ou altera dados
- Não imprime chaves nem segredos
- Não usa public.documentos

Uso:
    # Rodar a lista padrão de perguntas (TEST_QUESTIONS):
    python test_match.py

    # Rodar uma única pergunta ad-hoc:
    python test_match.py --question "O que é responsabilidade civil no seguro aeronáutico?"
"""

import argparse
import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client


# =====================================================================
# CONFIGURAÇÕES
# =====================================================================

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768
TABLE_NAME = "document_chunks"
RPC_NAME = "match_document_chunks"
MATCH_COUNT = 8
MATCH_THRESHOLD = 0.5
SHOW_CONTENT_CHARS = 900

TEST_QUESTIONS = [
    "O que é casco aeronáutico?",
    "O seguro cobre pane seca?",
    "O que significa exclusão operacional?",
    "O que é responsabilidade civil no seguro aeronáutico?",
    "Quando a seguradora pode negar indenização?",
]


# =====================================================================
# VALIDAÇÃO DE URL DO SUPABASE (mesma lógica do create_embeddings.py)
# =====================================================================

class SupabaseUrlError(ValueError):
    pass


def validate_supabase_url(raw_url: str) -> str:
    """
    Valida e normaliza a SUPABASE_URL.

    Regras:
    - Deve começar com https://
    - Deve ser uma Project URL: https://<projeto>.supabase.co
    - Não pode conter /rest/v1, /auth/v1, /storage/v1, /functions/v1
    - Remove barra final
    """
    if not raw_url or not isinstance(raw_url, str):
        raise SupabaseUrlError(
            "SUPABASE_URL ausente. Defina no .env como "
            "https://seu-projeto.supabase.co"
        )

    url = raw_url.strip().rstrip("/")

    if not url.startswith("https://"):
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Use apenas a Project URL do Supabase, "
            "no formato https://seu-projeto.supabase.co. "
            "Não use URL com /rest/v1."
        )

    parsed = urlparse(url)
    host = parsed.netloc or ""
    path = parsed.path or ""

    if path not in ("", "/"):
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Use apenas a Project URL do Supabase, "
            "no formato https://seu-projeto.supabase.co. "
            "Não use URL com /rest/v1."
        )

    forbidden = ("/rest/v1", "/auth/v1", "/storage/v1", "/functions/v1")
    if any(token in url for token in forbidden):
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Use apenas a Project URL do Supabase, "
            "no formato https://seu-projeto.supabase.co. "
            "Não use URL com /rest/v1."
        )

    if not host or "." not in host:
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Host não reconhecido."
        )

    return url


def validate_supabase_connection(supabase: Client) -> None:
    """
    SELECT seguro em document_chunks. Não insere, não altera, não apaga.
    Interrompe a execução ANTES de chamar Gemini se a conexão falhar.
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
        print(f"  - Existência da tabela public.{TABLE_NAME}")
        print(f"  - TABLE_NAME no script: deve ser \"{TABLE_NAME}\"")
        print("  Pipeline interrompida ANTES de qualquer chamada ao Gemini.")
        sys.exit(1)

    total = getattr(response, "count", None)
    if total is None:
        total = "?"
    print(f"  [OK] Conexão com Supabase validada. Registros em "
          f"public.{TABLE_NAME}: {total}")


# =====================================================================
# EMBEDDING DA PERGUNTA (task_type = RETRIEVAL_QUERY)
# =====================================================================

def get_query_embedding(question: str, client: genai.Client) -> list[float]:
    """
    Gera o embedding de uma pergunta usando task_type=RETRIEVAL_QUERY.
    Valida que o vetor tem EMBEDDING_DIMENSION dimensões.
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSION,
        ),
    )

    if not result.embeddings or not result.embeddings[0].values:
        raise ValueError(
            "Resposta do Gemini sem embedding válido para a pergunta."
        )

    embedding = result.embeddings[0].values
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Dimensão incorreta do embedding. "
            f"Esperado: {EMBEDDING_DIMENSION}, obtido: {len(embedding)}"
        )

    return list(embedding)


# =====================================================================
# CHAMADA DA RPC match_document_chunks
# =====================================================================

def match_documents(
    supabase: Client, query_embedding: list[float]
) -> list[dict]:
    """
    Chama a RPC match_document_chunks no Supabase.

    Retorna a lista de chunks (response.data) ou [] em caso de falha.
    Em caso de erro, imprime diagnóstico claro.
    """
    try:
        response = supabase.rpc(
            RPC_NAME,
            {
                "query_embedding": query_embedding,
                "match_count": MATCH_COUNT,
                "match_threshold": MATCH_THRESHOLD,
            },
        ).execute()
    except Exception as exc:
        print(f"  [ERROR] Falha ao chamar a RPC {RPC_NAME}: {exc}")
        print("  Verifique:")
        print(f"  - Se a RPC public.{RPC_NAME} existe no Supabase")
        print(f"    (rode supabase_diagnostics.sql para conferir)")
        print(f"  - Se a dimensão do embedding é {EMBEDDING_DIMENSION}")
        print(f"  - Se a tabela public.{TABLE_NAME} está populada")
        print("  - SUPABASE_URL (sem /rest/v1) e SUPABASE_SERVICE_ROLE_KEY")
        return []

    data = getattr(response, "data", None)
    if data is None:
        return []
    return list(data)


# =====================================================================
# IMPRESSÃO DOS RESULTADOS
# =====================================================================

def print_question_header(question: str) -> None:
    print("\n" + "=" * 60)
    print("PERGUNTA")
    print("=" * 60)
    print(question)


def print_chunk_result(rank: int, chunk: dict) -> None:
    similarity = chunk.get("similarity")
    try:
        sim_fmt = f"{float(similarity):.4f}"
    except (TypeError, ValueError):
        sim_fmt = "?"

    nome_arquivo = chunk.get("nome_arquivo", "?")
    pagina = chunk.get("pagina", "?")
    tipo = chunk.get("tipo", "?")
    seguradora = chunk.get("seguradora")
    orgao = chunk.get("orgao")
    fonte_extra = (
        f"seguradora={seguradora}"
        if seguradora
        else (f"orgao={orgao}" if orgao else "fonte=?")
    )

    chunk_strategy = chunk.get("chunk_strategy", "?")
    chunk_index = chunk.get("chunk_index", "?")
    token_count = chunk.get("token_count", "?")
    chunk_id = chunk.get("id", "?")

    content = chunk.get("content", "") or ""
    trecho = content[:SHOW_CONTENT_CHARS].rstrip()
    truncated_marker = "..." if len(content) > SHOW_CONTENT_CHARS else ""

    print(f"\n[{rank}] similarity={sim_fmt}  id={chunk_id}")
    print(
        f"Fonte: {nome_arquivo} | página {pagina} | tipo={tipo} | {fonte_extra}"
    )
    print(
        f"Chunk: strategy={chunk_strategy} | index={chunk_index} | "
        f"tokens={token_count}"
    )
    print("Trecho:")
    print(f"\"{trecho}{truncated_marker}\"")


def print_results(question: str, results: list[dict]) -> None:
    print_question_header(question)
    n = len(results)
    print(f"\nResultados encontrados: {n}")

    if n == 0:
        print(
            "Nenhum resultado acima do threshold. "
            "Tente reduzir MATCH_THRESHOLD ou revisar os embeddings."
        )
    else:
        for i, chunk in enumerate(results, start=1):
            print_chunk_result(i, chunk)

    print("\nAvaliação manual: [ ] OK  [ ] PARCIAL  [ ] RUIM  [ ] NÃO ENCONTRADO")
    print("Observações:")


# =====================================================================
# RELATÓRIO FINAL
# =====================================================================

def print_final_report(
    total_questions: int, with_results: int, without_results: int
) -> None:
    print("\n" + "=" * 60)
    print("RELATÓRIO FINAL — Retrieval")
    print("=" * 60)
    print(f"Perguntas testadas: {total_questions}")
    print(f"Perguntas com resultados: {with_results}")
    print(f"Perguntas sem resultados: {without_results}")
    print(f"MATCH_THRESHOLD: {MATCH_THRESHOLD}")
    print(f"MATCH_COUNT: {MATCH_COUNT}")
    print(f"Modelo de embedding: {EMBEDDING_MODEL} "
          f"(dim={EMBEDDING_DIMENSION}, task=RETRIEVAL_QUERY)")
    print(f"Tabela: public.{TABLE_NAME}  |  RPC: public.{RPC_NAME}")
    print(
        "\nOBS: Este script testa SOMENTE Retrieval. "
        "Nenhuma geração de resposta com LLM foi executada."
    )


# =====================================================================
# CLI
# =====================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Testa Retrieval do RAG: gera embedding de pergunta(s) com "
            "Gemini e busca chunks via RPC match_document_chunks. "
            "Não gera resposta final."
        )
    )
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help=(
            "Pergunta única a ser testada. Se omitido, roda a lista "
            "padrão TEST_QUESTIONS."
        ),
    )
    return parser.parse_args()


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:
    args = parse_args()
    questions = [args.question] if args.question else list(TEST_QUESTIONS)

    print("=" * 60)
    print("TESTE DE RETRIEVAL (somente busca vetorial — sem LLM)")
    print("=" * 60)
    print(f"Perguntas a testar: {len(questions)}")
    print(
        f"Modelo: {EMBEDDING_MODEL} | dim={EMBEDDING_DIMENSION} | "
        f"task_type=RETRIEVAL_QUERY"
    )
    print(
        f"RPC: public.{RPC_NAME} | match_count={MATCH_COUNT} | "
        f"match_threshold={MATCH_THRESHOLD}"
    )

    # 1. Carregar .env
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

    # 3. Validar SUPABASE_URL
    try:
        supabase_url = validate_supabase_url(supabase_url_raw)
    except SupabaseUrlError as exc:
        print(f"[CRITICAL ERROR] {exc}")
        sys.exit(1)

    print(
        f"  [OK] SUPABASE_URL validada "
        f"(host={urlparse(supabase_url).netloc})."
    )

    # 4. Criar cliente Supabase
    try:
        supabase: Client = create_client(
            supabase_url, supabase_service_role_key
        )
    except Exception as exc:
        print(f"[CRITICAL ERROR] Falha ao criar cliente Supabase: {exc}")
        sys.exit(1)

    # 5. Validar conexão ANTES de chamar Gemini
    print("Validando conexão com Supabase...")
    validate_supabase_connection(supabase)

    # 6. Criar cliente Gemini SOMENTE após validar Supabase
    try:
        gemini_client = genai.Client(api_key=gemini_api_key)
    except Exception as exc:
        print(f"[CRITICAL ERROR] Falha ao criar cliente Gemini: {exc}")
        sys.exit(1)
    print("  [OK] Cliente Gemini inicializado.")

    # 7. Rodar perguntas
    with_results = 0
    without_results = 0

    for question in questions:
        try:
            query_embedding = get_query_embedding(question, gemini_client)
        except Exception as exc:
            print_question_header(question)
            print(f"  [ERROR] Falha ao gerar embedding da pergunta: {exc}")
            print(
                "\nAvaliação manual: [ ] OK  [ ] PARCIAL  [ ] RUIM  "
                "[ ] NÃO ENCONTRADO"
            )
            print("Observações:")
            without_results += 1
            continue

        results = match_documents(supabase, query_embedding)
        print_results(question, results)

        if results:
            with_results += 1
        else:
            without_results += 1

    # 8. Relatório final
    print_final_report(
        total_questions=len(questions),
        with_results=with_results,
        without_results=without_results,
    )


if __name__ == "__main__":
    main()
