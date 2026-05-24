import os
import sys
import json
from pathlib import Path
from collections import Counter
import tiktoken
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client

# =====================================================================
# CONFIGURAÇÕES E PARÂMETROS
# =====================================================================
DRY_RUN = True

STAGING_DIR = Path("staging")
TABLE_NAME = "document_chunks"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768
MIN_CHARS_FOR_EMBEDDING = 30
BATCH_SIZE = 20

# =====================================================================
# FUNÇÕES DE SUPORTE E EMBEDDING
# =====================================================================

def get_gemini_embedding(text: str, client: genai.Client) -> list[float]:
    """
    Chama a API do Gemini (google.genai) para gerar o embedding do texto.
    Valida que o vetor retornado possui exatamente 768 dimensões.
    """
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSION,
        ),
    )
    
    if not result.embeddings or not result.embeddings[0].values:
        raise ValueError(f"Resposta do Gemini não contém embedding válido: {result}")
    
    embedding = result.embeddings[0].values
    
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Dimensão incorreta do embedding. Esperado: {EMBEDDING_DIMENSION}, Obtido: {len(embedding)}"
        )
    
    return embedding

def insert_chunks_to_supabase(supabase_client: Client, table_name: str, chunk_records: list[dict]) -> tuple[int, int]:
    """
    Insere os chunks no Supabase em lotes de BATCH_SIZE.
    Em caso de falha no lote, tenta inserção linha a linha (resiliente).
    Retorna o número de sucessos e falhas.
    """
    inserted_count = 0
    failed_count = 0
    
    for i in range(0, len(chunk_records), BATCH_SIZE):
        batch = chunk_records[i:i + BATCH_SIZE]
        try:
            supabase_client.table(table_name).insert(batch).execute()
            inserted_count += len(batch)
            print(f"  [Supabase] Inserido lote com {len(batch)} chunks (índices {i} a {i + len(batch) - 1})")
        except Exception as batch_error:
            print(f"  [WARNING] Erro ao inserir lote de {len(batch)} chunks: {batch_error}")
            print("  [Supabase] Tentando inserção individual para este lote...")
            # Fallback para inserção um a um neste lote
            for record in batch:
                try:
                    supabase_client.table(table_name).insert(record).execute()
                    inserted_count += 1
                except Exception as individual_error:
                    failed_count += 1
                    print(
                        f"    [ERROR] Falha ao inserir chunk individual (Arquivo: {record['nome_arquivo']}, "
                        f"Página: {record['pagina']}): {individual_error}"
                    )
                    
    return inserted_count, failed_count

# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================

def main():
    print("INICIALIZANDO PIPELINE DE EMBEDDINGS")
    print("=" * 60)
    
    # 1. Carregar variáveis de ambiente
    load_dotenv()
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # 2. Validar presença das variáveis obrigatórias
    missing_vars = []
    if not gemini_api_key:
        missing_vars.append("GEMINI_API_KEY")
    if not supabase_url:
        missing_vars.append("SUPABASE_URL")
    if not supabase_service_role_key:
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")
        
    if missing_vars:
        print(f"[CRITICAL ERROR] Variáveis de ambiente obrigatórias ausentes: {', '.join(missing_vars)}")
        print("Por favor, preencha o seu arquivo .env com base no .env.example.")
        sys.exit(1)
        
    # 3. Configurar cliente Gemini (nova API google.genai)
    gemini_client = genai.Client(api_key=gemini_api_key)
    
    # 4. Configurar cliente Supabase
    try:
        supabase_client = create_client(
            supabase_url,
            supabase_service_role_key,
        )
    except Exception as exc:
        print(f"[CRITICAL ERROR] Falha ao conectar ao Supabase: {exc}")
        sys.exit(1)
        
    # 5. Validar existência do diretório de staging
    if not STAGING_DIR.exists():
        print(f"[CRITICAL ERROR] Pasta de staging não encontrada em: {STAGING_DIR.resolve()}")
        sys.exit(1)
        
    json_files = list(STAGING_DIR.glob("*.json"))
    total_json_found = len(json_files)
    
    if total_json_found == 0:
        print(f"[CRITICAL ERROR] Nenhum arquivo JSON encontrado no diretório: {STAGING_DIR.resolve()}")
        sys.exit(1)
        
    print(f"Arquivos JSON encontrados em staging/: {total_json_found}")
    
    # 6. Carregar, validar e agrupar documentos
    ignored_pages = []
    raw_pages = []
    
    for path in json_files:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[WARNING] Falha ao carregar JSON {path.name}: {exc}")
            continue
            
        texto = data.get("texto", "")
        texto_limpo = texto.strip()
        
        # Filtro de caracteres mínimos
        if len(texto_limpo) < MIN_CHARS_FOR_EMBEDDING:
            ignored_pages.append({
                "filename": path.name,
                "nome_arquivo": data.get("nome_arquivo", "Desconhecido"),
                "pagina": data.get("pagina", 0),
                "chars": len(texto_limpo)
            })
            continue
            
        raw_pages.append(data)
        
    # Ordenar as páginas por nome_arquivo e depois pela página para calcular o chunk_index corretamente
    raw_pages.sort(key=lambda x: (x.get("nome_arquivo", ""), x.get("pagina", 0)))
    
    # Agrupar por documento para gerar índices de chunks sequenciais ordenados (0, 1, 2...)
    document_chunk_counters = Counter()
    
    # Carregar o codificador tiktoken para contagem de tokens
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.get_encoding("gpt-4")
        
    prepared_chunks = []
    failed_embeddings = []
    
    print("\nProcessando e preparando chunks...")
    
    for page_data in raw_pages:
        nome_arquivo = page_data["nome_arquivo"]
        pagina = page_data["pagina"]
        texto = page_data["texto"]
        metadata_original = page_data.get("metadata", {})
        
        # Obter metadados específicos
        tipo = metadata_original.get("tipo", "condicoes_gerais")
        seguradora = metadata_original.get("seguradora")
        orgao = metadata_original.get("orgao")
        enquadramento = metadata_original.get("enquadramento")
        
        # Incrementar o índice do chunk para este documento específico
        chunk_index = document_chunk_counters[nome_arquivo]
        document_chunk_counters[nome_arquivo] += 1
        
        # Contagem aproximada de tokens
        token_count = len(encoding.encode(texto))
        
        # Obter embedding
        embedding = None
        if not DRY_RUN:
            try:
                embedding = get_gemini_embedding(texto, gemini_client)
            except Exception as exc:
                print(f"  [ERROR] Falha ao gerar embedding para {nome_arquivo} pág. {pagina}: {exc}")
                failed_embeddings.append({
                    "nome_arquivo": nome_arquivo,
                    "pagina": pagina,
                    "erro": str(exc)
                })
                # Decrementamos o contador do documento pois este chunk falhou na raiz e não será criado
                document_chunk_counters[nome_arquivo] -= 1
                continue
        
        # Preparar registro final para inserção no banco
        chunk_record = {
            "content": texto,
            "embedding": embedding,
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
                "chunk_index": chunk_index
            }
        }
        
        prepared_chunks.append(chunk_record)
        
    # Inserção no Supabase se DRY_RUN for False
    inserted_count = 0
    failed_inserts_count = 0
    
    if not DRY_RUN and prepared_chunks:
        print(f"\nIniciando carga no Supabase ({len(prepared_chunks)} chunks)...")
        inserted_count, failed_inserts_count = insert_chunks_to_supabase(
            supabase_client, TABLE_NAME, prepared_chunks
        )
        
    # =====================================================================
    # EXIBIÇÃO DE RELATÓRIO FINAL
    # =====================================================================
    print("\n" + "=" * 60)
    print("RELATÓRIO DE EXECUÇÃO")
    print("=" * 60)
    
    print(f"Total de arquivos JSON encontrados em staging/: {total_json_found}")
    print(f"Total de páginas válidas processadas: {len(raw_pages)}")
    print(f"Total de páginas ignoradas por texto curto (< {MIN_CHARS_FOR_EMBEDDING} caracteres): {len(ignored_pages)}")
    print(f"Total de chunks criados: {len(prepared_chunks)}")
    
    # Estatísticas por tipo
    chunks_by_tipo = Counter(c["tipo"] for c in prepared_chunks)
    print("\nChunks por tipo:")
    for t, c in chunks_by_tipo.items():
        print(f"  - {t}: {c}")
        
    # Estatísticas por seguradora
    chunks_by_seguradora = Counter(c["seguradora"] for c in prepared_chunks if c["seguradora"] is not None)
    if chunks_by_seguradora:
        print("\nChunks por seguradora:")
        for s, c in chunks_by_seguradora.items():
            print(f"  - {s}: {c}")
            
    # Estatísticas por nome_arquivo
    chunks_by_arquivo = Counter(c["nome_arquivo"] for c in prepared_chunks)
    print("\nChunks por nome_arquivo:")
    for a, c in chunks_by_arquivo.items():
        print(f"  - {a}: {c}")
        
    # Páginas ignoradas
    if ignored_pages:
        print("\nPáginas ignoradas por texto muito curto:")
        for ip in ignored_pages:
            print(f"  - {ip['filename']} ({ip['nome_arquivo']}, pág. {ip['pagina']}): {ip['chars']} caracteres")
            
    # Exemplos dos 3 primeiros chunks
    print("\nExemplo dos 3 primeiros chunks gerados:")
    for idx, chunk in enumerate(prepared_chunks[:3]):
        print(f"\n--- Exemplo {idx + 1} ---")
        print(f"Nome do arquivo: {chunk['nome_arquivo']}")
        print(f"Página: {chunk['pagina']}")
        print(f"Tipo: {chunk['tipo']}")
        print(f"Seguradora/Órgão: {chunk['seguradora'] if chunk['seguradora'] else chunk['orgao']}")
        print(f"Token Count (Est.): {chunk['token_count']}")
        print(f"Conteúdo (primeiros 300 caracteres):")
        truncated_content = chunk['content'][:300].replace('\n', ' ')
        print(f"  \"{truncated_content}...\"")
        
    # Informações de falhas
    if not DRY_RUN:
        print("\nCarga de dados no Banco de Dados (Supabase):")
        print(f"  - Chunks preparados para envio: {len(prepared_chunks)}")
        print(f"  - Chunks inseridos com sucesso: {inserted_count}")
        print(f"  - Chunks que falharam na inserção: {failed_inserts_count}")
        if failed_embeddings:
            print(f"  - Chunks que falharam na geração de embedding: {len(failed_embeddings)}")
            for fe in failed_embeddings:
                print(f"    * {fe['nome_arquivo']} pág. {fe['pagina']}: {fe['erro']}")
    else:
        print("\n" + "!" * 60)
        print("AVISO: DRY_RUN=True, nenhuma chamada de embedding foi feita e nada foi inserido no Supabase.")
        print("!" * 60)

if __name__ == "__main__":
    main()
