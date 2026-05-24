from pathlib import Path
import json
from collections import Counter


STAGING_DIR = Path("staging")

REQUIRED_TOP_LEVEL_FIELDS = {
    "nome_arquivo",
    "pagina",
    "texto",
    "metadata",
}

VALID_TIPOS = {
    "resolucao_mestre",
    "condicoes_gerais",
}

VALID_ORGAOS = {
    "CNSP_SUSEP",
}

VALID_ENQUADRAMENTOS = {
    "grandes_riscos",
    "grandes_riscos_407_2021",
}

VALID_SEGURADORAS = {
    "AXA",
    "Essor",
    "Excelsior",
    "EZZE",
    "Mapfre",
}


def validate_file(path: Path) -> list[str]:
    errors = []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return [f"JSON inválido: {exc}"]

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            errors.append(f"Campo obrigatório ausente no nível raiz: {field}")

    nome_arquivo = data.get("nome_arquivo")
    if nome_arquivo is not None and not isinstance(nome_arquivo, str):
        errors.append("nome_arquivo deve ser string")

    pagina = data.get("pagina")
    if pagina is not None:
        if not isinstance(pagina, int):
            errors.append("pagina deve ser inteiro")
        elif pagina <= 0:
            errors.append("pagina deve ser maior que zero")

    texto = data.get("texto")
    if texto is not None:
        if not isinstance(texto, str):
            errors.append("texto deve ser string")
        elif not texto.strip():
            errors.append("texto está vazio")

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata deve ser objeto")
        return errors

    tipo = metadata.get("tipo")
    if not tipo:
        errors.append("metadata.tipo é obrigatório")
    elif tipo not in VALID_TIPOS:
        errors.append(f"metadata.tipo inválido: {tipo}")

    if tipo == "resolucao_mestre":
        orgao = metadata.get("orgao")
        enquadramento = metadata.get("enquadramento")

        if orgao not in VALID_ORGAOS:
            errors.append(f"metadata.orgao inválido para resolução mestre: {orgao}")

        if enquadramento not in VALID_ENQUADRAMENTOS:
            errors.append(
                f"metadata.enquadramento inválido para resolução mestre: {enquadramento}"
            )

        if metadata.get("seguradora"):
            errors.append("resolucao_mestre não deve ter metadata.seguradora")

    elif tipo == "condicoes_gerais":
        seguradora = metadata.get("seguradora")

        if not seguradora:
            errors.append("metadata.seguradora é obrigatório para condicoes_gerais")
        elif seguradora not in VALID_SEGURADORAS:
            errors.append(f"metadata.seguradora inválida: {seguradora}")

    return errors


def main() -> None:
    if not STAGING_DIR.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {STAGING_DIR}")

    json_files = sorted(STAGING_DIR.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"Nenhum JSON encontrado em {STAGING_DIR}")

    errors_by_file = {}
    pages_by_tipo = Counter()
    pages_by_seguradora = Counter()
    pages_by_nome_arquivo = Counter()
    short_text_files = []
    empty_text_files = []

    for path in json_files:
        errors = validate_file(path)

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            texto = data.get("texto", "")

            pages_by_tipo[metadata.get("tipo", "UNKNOWN")] += 1
            pages_by_nome_arquivo[data.get("nome_arquivo", "UNKNOWN")] += 1

            if metadata.get("tipo") == "condicoes_gerais":
                pages_by_seguradora[metadata.get("seguradora", "UNKNOWN")] += 1

            if isinstance(texto, str):
                stripped_text = texto.strip()

                if not stripped_text:
                    empty_text_files.append(path.name)
                elif len(stripped_text) < 30:
                    short_text_files.append(path.name)

        except Exception:
            pass

        if errors:
            errors_by_file[path.name] = errors

    print("\nVALIDAÇÃO DO STAGING")
    print("=" * 60)

    print(f"Arquivos JSON encontrados: {len(json_files)}")
    print(f"Arquivos com erro: {len(errors_by_file)}")

    print("\nPáginas por tipo:")
    for tipo, count in pages_by_tipo.most_common():
        print(f"  - {tipo}: {count}")

    print("\nPáginas por seguradora:")
    for seguradora, count in pages_by_seguradora.most_common():
        print(f"  - {seguradora}: {count}")

    print("\nPáginas por nome_arquivo:")
    for nome_arquivo, count in pages_by_nome_arquivo.most_common():
        print(f"  - {nome_arquivo}: {count}")

    if short_text_files:
        print("\nAviso: arquivos com texto muito curto:")
        for filename in short_text_files:
            print(f"  - {filename}")

    if empty_text_files:
        print("\nAviso: arquivos com texto vazio:")
        for filename in empty_text_files:
            print(f"  - {filename}")

    if errors_by_file:
        print("\nERROS ENCONTRADOS")
        print("=" * 60)

        for filename, errors in errors_by_file.items():
            print(f"\n{filename}")
            for error in errors:
                print(f"  - {error}")

        raise SystemExit(1)

    print("\nStaging validado com sucesso. Nenhum erro crítico encontrado.")

    if short_text_files or empty_text_files:
        print(
            "\nObservação: existem avisos de conteúdo curto ou vazio. "
            "Revise manualmente esses arquivos antes de gerar embeddings."
        )


if __name__ == "__main__":
    main()