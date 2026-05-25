"""
review_eval_dataset.py

Revisão assistida (sem LLM) do dataset v1.

Entrada:
    eval/evaluation_dataset_v1.csv  (gerado por curate_eval_dataset.py)

Saídas:
    eval/evaluation_dataset.csv         (dataset oficial preliminar)
    eval/evaluation_dataset_review.md   (versão legível para revisão humana)

O que faz:
- Lê a v1.
- Valida colunas obrigatórias.
- Normaliza espaços em todas as colunas textuais.
- Troca status_revisao de "pendente_revisao" para "aprovado_preliminar".
- Adiciona a coluna `revisao_observacao` ao final, com alertas
  automáticos detectados a partir do conteúdo de cada linha.
- Gera a versão Markdown legível.
- Imprime um relatório com a distribuição e a lista de ids com alerta.
- Conta linhas em `eval/evaluation_dataset_rejected.csv` que foram
  rejeitadas por "excedeu cap", para apoiar reincorporações manuais.

O que NÃO faz:
- Não chama Gemini.
- Não chama Supabase.
- Não toca em staging/.
- Não lê chaves do .env.
- Não apaga draft, v1 ou rejected.
- Não faz commit.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


INPUT_PATH = Path("eval/evaluation_dataset_v1.csv")
OUTPUT_CSV_PATH = Path("eval/evaluation_dataset.csv")
OUTPUT_MD_PATH = Path("eval/evaluation_dataset_review.md")
REJECTED_PATH = Path("eval/evaluation_dataset_rejected.csv")

REQUIRED_COLUMNS = [
    "id",
    "pergunta",
    "tipo",
    "escopo",
    "seguradora",
    "documento_esperado",
    "pagina_esperada",
    "termos_esperados",
    "resposta_ideal_draft",
    "criterio_sucesso",
    "nivel_dificuldade",
    "status_revisao",
    "observacoes",
]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + ["revisao_observacao"]

MANUAL_ID_PREFIX = "Q_manual_"
MIN_RESPOSTA_CHARS = 120

NOISE_TERMS = [
    "www.",
    "telefone",
    "cep:",
    "endereço",
    "whatsapp",
    "sac",
]

RC_TERMS = ["danos", "terceiros", "reparação", "responsabilidade", "indenização"]

TIPO_REQUIRED_TERMS = {
    "exclusao": [
        "excluído",
        "excluídos",
        "exclusão",
        "exclusões",
        "não estão garant",
        "não garante",
    ],
    "sinistro": [
        "sinistro",
        "indenização",
        "recusa",
        "perda de direito",
        "fraude",
        "agravamento",
        "liquidação",
    ],
    "cobertura": [
        "cobertura",
        "garantia",
        "limite",
        "franquia",
        "indenização",
        "âmbito geográfico",
    ],
    "regulatorio": [
        "cnsp",
        "susep",
        "resolução",
        "grandes riscos",
        "contrato",
        "seguros de danos",
    ],
}

TIPO_ALERT_MSG = {
    "exclusao": "resposta pode não conter exclusão substantiva",
    "sinistro": "resposta pode não conter fundamento de sinistro",
    "cobertura": "resposta pode não conter fundamento de cobertura",
    "regulatorio": "resposta pode não conter fundamento regulatório",
}


# ----------------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------------

def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def is_manual(row: dict) -> bool:
    return row.get("id", "").startswith(MANUAL_ID_PREFIX)


def has_noise_term(text_lower: str) -> bool:
    for term in NOISE_TERMS:
        if term == "sac":
            if re.search(r"\bsac\b", text_lower):
                return True
        else:
            if term in text_lower:
                return True
    return False


def contains_any(text_lower: str, terms: list[str]) -> bool:
    return any(t in text_lower for t in terms)


# ----------------------------------------------------------------------
# Alertas por linha
# ----------------------------------------------------------------------

def gerar_alertas(row: dict) -> list[str]:
    alertas: list[str] = []
    manual = is_manual(row)

    documento = (row.get("documento_esperado") or "").strip()
    pagina = (row.get("pagina_esperada") or "").strip()
    resposta = collapse_whitespace(row.get("resposta_ideal_draft", ""))
    pergunta = collapse_whitespace(row.get("pergunta", ""))
    tipo = (row.get("tipo") or "").strip().lower()

    resposta_lower = resposta.lower()
    pergunta_lower = pergunta.lower()

    if not manual and not documento:
        alertas.append("documento_esperado vazio")

    if not manual and not pagina:
        alertas.append("pagina_esperada vazia")

    if resposta.lower().startswith("revisar manualmente"):
        alertas.append("resposta ideal ainda é instrução de revisão")

    if len(resposta) < MIN_RESPOSTA_CHARS:
        alertas.append("resposta ideal curta")

    if has_noise_term(resposta_lower):
        alertas.append("possível ruído de capa ou contato")

    if "responsabilidade civil" in pergunta_lower:
        if not contains_any(resposta_lower, RC_TERMS):
            alertas.append("resposta pode não explicar responsabilidade civil")

    required = TIPO_REQUIRED_TERMS.get(tipo)
    if required is not None:
        if not contains_any(resposta_lower, required):
            alertas.append(TIPO_ALERT_MSG[tipo])

    return alertas


# ----------------------------------------------------------------------
# Normalização da linha
# ----------------------------------------------------------------------

def normalizar_linha(row: dict) -> dict:
    out = dict(row)
    for col in REQUIRED_COLUMNS:
        out[col] = collapse_whitespace(out.get(col, ""))
    out["status_revisao"] = "aprovado_preliminar"
    return out


# ----------------------------------------------------------------------
# Leitura/escrita
# ----------------------------------------------------------------------

def ler_v1(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"Arquivo de entrada não encontrado: {path}. "
            f"Rode curate_eval_dataset.py antes."
        )
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        faltando = [c for c in REQUIRED_COLUMNS if c not in cols]
        if faltando:
            raise SystemExit(
                f"v1 está faltando colunas obrigatórias: {faltando}. "
                f"Esperado: {REQUIRED_COLUMNS}"
            )
        return list(reader)


def escrever_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for row in rows:
            normalized = {k: row.get(k, "") for k in OUTPUT_COLUMNS}
            writer.writerow(normalized)


def escrever_markdown(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    linhas: list[str] = []
    linhas.append("# Dataset oficial preliminar — revisão humana")
    linhas.append("")
    linhas.append(
        "Versão legível de `eval/evaluation_dataset.csv`. "
        "Cada entrada abaixo corresponde a uma linha do CSV."
    )
    linhas.append("")
    linhas.append(
        "Use este arquivo para uma leitura rápida durante a revisão. "
        "As edições devem ser feitas no CSV oficial, não aqui."
    )
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    for row in rows:
        fonte = row.get("documento_esperado", "") or "—"
        pagina = row.get("pagina_esperada", "") or "—"
        fonte_linha = f"{fonte}, página {pagina}" if fonte != "—" else "—"

        linhas.append(f"## {row.get('id', '')}")
        linhas.append("")
        linhas.append("**Pergunta:**")
        linhas.append("")
        linhas.append(row.get("pergunta", "") or "—")
        linhas.append("")
        linhas.append("**Tipo:**")
        linhas.append("")
        linhas.append(row.get("tipo", "") or "—")
        linhas.append("")
        linhas.append("**Escopo:**")
        linhas.append("")
        linhas.append(row.get("escopo", "") or "—")
        linhas.append("")
        linhas.append("**Seguradora / órgão:**")
        linhas.append("")
        linhas.append(row.get("seguradora", "") or "—")
        linhas.append("")
        linhas.append("**Fonte esperada:**")
        linhas.append("")
        linhas.append(fonte_linha)
        linhas.append("")
        linhas.append("**Termos esperados:**")
        linhas.append("")
        linhas.append(row.get("termos_esperados", "") or "—")
        linhas.append("")
        linhas.append("**Resposta ideal draft:**")
        linhas.append("")
        linhas.append(row.get("resposta_ideal_draft", "") or "—")
        linhas.append("")
        linhas.append("**Critério de sucesso:**")
        linhas.append("")
        linhas.append(row.get("criterio_sucesso", "") or "—")
        linhas.append("")
        linhas.append("**Nível de dificuldade:**")
        linhas.append("")
        linhas.append(row.get("nivel_dificuldade", "") or "—")
        linhas.append("")
        linhas.append("**Status:**")
        linhas.append("")
        linhas.append(row.get("status_revisao", "") or "—")
        linhas.append("")
        linhas.append("**Observações:**")
        linhas.append("")
        linhas.append(row.get("observacoes", "") or "—")
        linhas.append("")
        linhas.append("**Observações de revisão:**")
        linhas.append("")
        linhas.append(row.get("revisao_observacao", "") or "—")
        linhas.append("")
        linhas.append("---")
        linhas.append("")

    path.write_text("\n".join(linhas), encoding="utf-8")


def contar_rejeitadas_excedeu_cap(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "motivo_rejeicao" not in (reader.fieldnames or []):
            return 0
        return sum(
            1 for r in reader if "excedeu cap" in (r.get("motivo_rejeicao") or "")
        )


# ----------------------------------------------------------------------
# Pipeline + relatório
# ----------------------------------------------------------------------

def review() -> dict:
    rows = ler_v1(INPUT_PATH)
    total_lidas = len(rows)

    saidas: list[dict] = []
    com_alerta: list[tuple[str, list[str]]] = []
    sem_alerta = 0
    dist_tipo: dict[str, int] = defaultdict(int)
    dist_seg: dict[str, int] = defaultdict(int)

    for row in rows:
        norm = normalizar_linha(row)
        alertas = gerar_alertas(norm)
        if alertas:
            norm["revisao_observacao"] = " | ".join(alertas)
            com_alerta.append((norm["id"], alertas))
        else:
            norm["revisao_observacao"] = "ok para avaliação preliminar"
            sem_alerta += 1
        saidas.append(norm)
        dist_tipo[norm.get("tipo", "?")] += 1
        dist_seg[norm.get("seguradora", "?")] += 1

    escrever_csv(OUTPUT_CSV_PATH, saidas)
    escrever_markdown(OUTPUT_MD_PATH, saidas)

    rejeitadas_cap = contar_rejeitadas_excedeu_cap(REJECTED_PATH)

    return {
        "total_lidas": total_lidas,
        "total_salvas": len(saidas),
        "sem_alerta": sem_alerta,
        "com_alerta": com_alerta,
        "dist_tipo": dict(dist_tipo),
        "dist_seg": dict(dist_seg),
        "rejeitadas_cap": rejeitadas_cap,
    }


def imprimir_relatorio(stats: dict) -> None:
    print("=" * 60)
    print("REVISÃO ASSISTIDA — review_eval_dataset.py")
    print("=" * 60)
    print(f"Arquivo de entrada:        {INPUT_PATH}")
    print(f"Arquivo de saída (CSV):    {OUTPUT_CSV_PATH}")
    print(f"Arquivo de saída (MD):     {OUTPUT_MD_PATH}")
    print(f"Linhas lidas:              {stats['total_lidas']}")
    print(f"Linhas salvas:             {stats['total_salvas']}")
    print(f"Linhas sem alerta:         {stats['sem_alerta']}")
    print(f"Linhas com alerta:         {len(stats['com_alerta'])}")

    print("\nDistribuição por tipo:")
    for tipo, n in sorted(stats["dist_tipo"].items(), key=lambda x: -x[1]):
        print(f"  {tipo:<14} {n}")

    print("\nDistribuição por seguradora/órgão:")
    for seg, n in sorted(stats["dist_seg"].items(), key=lambda x: -x[1]):
        print(f"  {seg:<14} {n}")

    if stats["com_alerta"]:
        print("\nLinhas com alerta:")
        for id_, alertas in stats["com_alerta"]:
            print(f"  {id_}:")
            for a in alertas:
                print(f"    - {a}")
    else:
        print("\nNenhuma linha com alerta.")

    if stats["rejeitadas_cap"] > 0:
        print(
            f"\nExistem {stats['rejeitadas_cap']} linhas boas rejeitadas "
            f"por limite em {REJECTED_PATH}. "
            f"Elas podem ser reincorporadas manualmente se necessário."
        )
    else:
        print(
            f"\nNenhuma linha do rejected está marcada como "
            f"'excedeu cap' (ou {REJECTED_PATH} ausente)."
        )

    print(
        "\nPróximo passo: revisão humana. Ajustar `revisao_observacao` "
        "e trocar `status_revisao` para `aprovado` nas linhas validadas."
    )
    print(
        "Depois da revisão humana, o próximo script do projeto será "
        "`test_retrieval.py` (comparar busca vetorial, híbrida e HyDE)."
    )


def main() -> None:
    stats = review()
    imprimir_relatorio(stats)


if __name__ == "__main__":
    main()
