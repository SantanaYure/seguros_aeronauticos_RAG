"""
test_supabase_connection.py

Valida a conexão com o Supabase sem gastar quota do Gemini.

Faz:
- Carrega .env
- Valida SUPABASE_URL (formato Project URL)
- Cria cliente Supabase com SUPABASE_SERVICE_ROLE_KEY
- Executa um SELECT count seguro em public.document_chunks
- Imprime resumo do resultado

Não faz:
- Não chama Gemini
- Não imprime chaves
- Não insere, atualiza ou apaga nada no Supabase

Uso:
    python test_supabase_connection.py
"""

import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from supabase import create_client, Client


TABLE_NAME = "document_chunks"


class SupabaseUrlError(ValueError):
    pass


def validate_supabase_url(raw_url: str) -> str:
    """
    Mesmo validador usado por create_embeddings.py.
    Mantido aqui de forma local para que o teste seja autônomo.
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
            "no formato https://seu-projeto.supabase.co. Não use URL com /rest/v1."
        )

    parsed = urlparse(url)
    host = parsed.netloc or ""
    path = parsed.path or ""

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

    if not host or "." not in host:
        raise SupabaseUrlError(
            "SUPABASE_URL inválida. Host não reconhecido."
        )

    return url


def main() -> None:
    print("=" * 60)
    print("TESTE DE CONEXÃO COM SUPABASE")
    print("=" * 60)

    load_dotenv()
    supabase_url_raw = os.getenv("SUPABASE_URL")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    missing = []
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

    try:
        supabase_url = validate_supabase_url(supabase_url_raw)
    except SupabaseUrlError as exc:
        print(f"[CRITICAL ERROR] {exc}")
        sys.exit(1)

    host = urlparse(supabase_url).netloc
    print(f"  [OK] SUPABASE_URL validada (host={host})")

    try:
        supabase: Client = create_client(
            supabase_url, supabase_service_role_key
        )
    except Exception as exc:
        print(f"[CRITICAL ERROR] Falha ao criar cliente Supabase: {exc}")
        sys.exit(1)
    print("  [OK] Cliente Supabase criado.")

    print(f"  Consultando count em public.{TABLE_NAME} (SELECT seguro)...")
    try:
        response = (
            supabase.table(TABLE_NAME)
            .select("id", count="exact")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        print(f"[CRITICAL ERROR] Falha ao consultar {TABLE_NAME}: {exc}")
        print("  Possíveis causas:")
        print(f"  - Tabela public.{TABLE_NAME} não existe")
        print("  - SUPABASE_SERVICE_ROLE_KEY inválida ou expirada")
        print("  - SUPABASE_URL com path indevido (ex: /rest/v1)")
        print("  - Conectividade de rede")
        sys.exit(1)

    total = getattr(response, "count", None)
    if total is None:
        total = "?"

    print(f"  [OK] Conexão bem-sucedida.")
    print(f"  Registros em public.{TABLE_NAME}: {total}")
    print("\nResultado: Supabase pronto para receber a carga.")
    print(
        "Próximo passo seguro:\n"
        "  - Confirmar DRY_RUN=True em create_embeddings.py e rodar:\n"
        "      python create_embeddings.py\n"
        "  - Em seguida, DRY_RUN=False com MAX_RECORDS=3."
    )


if __name__ == "__main__":
    main()
