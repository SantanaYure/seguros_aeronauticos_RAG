"""
curate_eval_dataset.py

Curadoria automática do dataset de avaliação.

Entrada:
    eval/evaluation_dataset_draft.csv  (gerado por generate_eval_dataset.py)

Saídas:
    eval/evaluation_dataset_v1.csv         (até 30 linhas, filtradas)
    eval/evaluation_dataset_rejected.csv   (linhas removidas + motivo)

Regras:
- Mantém sempre as 5 perguntas manuais (Q_manual_001..005).
- Rejeita linhas automáticas com resposta_ideal_draft vazia, curta,
  contendo ruído de capa/sumário/índice/contato ou começando com
  fragmento de palavra (típico de quebra na extração do PDF).
- Rejeita linhas automáticas que não trazem sinal forte para o próprio
  tipo (ex.: pergunta de exclusão cuja resposta não fala de riscos
  excluídos ou cláusula equivalente).
- Prioriza tipos sinistro > exclusao > cobertura > obrigacao >
  regulatorio > conceitual > comparacao.
- Dentro de cada tipo, distribui entre seguradoras e prefere páginas > 2.
- Limpa resposta (espaços, quebra), trunca a 600 caracteres, e mantém
  status_revisao = "pendente_revisao".

Não faz:
- Não chama Gemini.
- Não chama Supabase.
- Não toca em staging/.
- Não toca em .env.
- Não apaga o draft.
- Não faz commit.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path


INPUT_PATH = Path("eval/evaluation_dataset_draft.csv")
V1_PATH = Path("eval/evaluation_dataset_v1.csv")
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
REJECTED_COLUMNS = REQUIRED_COLUMNS + ["motivo_rejeicao"]

MAX_V1_ROWS = 30
MIN_RESPOSTA_CHARS = 80
RESPOSTA_MAX_CHARS = 600
CONSECUTIVE_DOTS_THRESHOLD = 16
MANUAL_ID_PREFIX = "Q_manual_"

OBSERVACAO_APROVADA = (
    "Selecionado automaticamente para revisão v1. "
    "Confirmar fonte, página e resposta ideal antes de aprovar."
)

TIPO_PRIORITY = [
    "sinistro",
    "exclusao",
    "cobertura",
    "obrigacao",
    "regulatorio",
    "conceitual",
    "comparacao",
]

NOISE_SUBSTRINGS = [
    "sumário",
    "cláusula página",
    "página cláusula",
    "www.",
    "telefone",
    "cep:",
    "endereço:",
    "central de atendimento",
    "sac",
    "whatsapp",
    "processo mapfre",
    "processo ezze",
    "nº interno axa",
    "registro deste plano",
    "condições contratuais versão",
]

NOISE_PREFIXES = [
    "usula",
    "ico",
    "dar ",
    "r vila",
    "ão ",
    "ara ",
    "gações",
    "enova",
    "ontrole",
    "ções ",
    "uer ",
    "rtuárias",
    "omicílio",
]

STRONG_SIGNALS = {
    "exclusao": [
        "riscos excluídos",
        "não estão garantidos",
        "não estão garantidas",
        "este seguro não garante",
        "exclui",
        "exclusões",
    ],
    "sinistro": [
        "recusa de sinistro",
        "perda de direito",
        "liquidação de sinistros",
        "regulação de sinistros",
        "fraude",
        "agravamento do risco",
        "agravamento de risco",
        "direito à indenização",
    ],
    "cobertura": [
        "riscos cobertos",
        "limite máximo de indenização",
        "franquia",
        "âmbito geográfico",
        "cobertura",
        "garantia",
    ],
    "obrigacao": [
        "obrigações do segurado",
        "segurado se obriga",
        "comunicar",
        "deveres",
        "em caso de sinistro",
    ],
    "regulatorio": [
        "grandes riscos",
        "cnsp",
        "susep",
        "resolução",
        "liberdade negocial",
        "transparência",
    ],
    "conceitual": [
        "responsabilidade civil",
        "danos corporais",
        "danos materiais",
        "terceiros",
        "reparações",
        "riscos cobertos",
    ],
}


# ----------------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------------

def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def is_manual(row: dict) -> bool:
    return row.get("id", "").startswith(MANUAL_ID_PREFIX)


def has_consecutive_dots(text: str, threshold: int) -> bool:
    return "." * threshold in text


def has_noise_substring(text_lower: str) -> bool:
    for token in NOISE_SUBSTRINGS:
        if token == "sac":
            if re.search(r"\bsac\b", text_lower):
                return True
        else:
            if token in text_lower:
                return True
    return False


def starts_with_noise(text_lower: str) -> bool:
    head = text_lower[:40]
    return any(head.startswith(prefix) for prefix in NOISE_PREFIXES)


def has_strong_signal(text_lower: str, tipo: str) -> bool:
    signals = STRONG_SIGNALS.get(tipo)
    if not signals:
        return True  # tipo sem sinais definidos não bloqueia
    return any(sig in text_lower for sig in signals)


def parse_pagina(raw) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return 0


# ----------------------------------------------------------------------
# Avaliação por linha
# ----------------------------------------------------------------------

def avaliar_linha(row: dict) -> tuple[bool, str]:
    """
    Retorna (aprovada, motivo_rejeicao).
    Linhas manuais sempre passam direto.
    """
    if is_manual(row):
        return True, ""

    resposta = row.get("resposta_ideal_draft", "") or ""
    resposta_clean = collapse_whitespace(resposta)
    lower = resposta_clean.lower()

    if not resposta_clean:
        return False, "resposta_ideal_draft vazia"

    if len(resposta_clean) < MIN_RESPOSTA_CHARS:
        return False, (
            f"resposta_ideal_draft muito curta "
            f"(<{MIN_RESPOSTA_CHARS} chars)"
        )

    if has_consecutive_dots(resposta_clean, CONSECUTIVE_DOTS_THRESHOLD):
        return False, (
            "resposta_ideal_draft contém pontos de índice/sumário"
        )

    if has_noise_substring(lower):
        return False, (
            "resposta_ideal_draft contém termos de "
            "capa/sumário/contato/registro"
        )

    if starts_with_noise(lower):
        return False, (
            "resposta_ideal_draft inicia com fragmento de palavra "
            "(ruído de extração do PDF)"
        )

    tipo = row.get("tipo", "")
    if not has_strong_signal(lower, tipo):
        return False, "não possui sinal forte para o tipo da pergunta"

    return True, ""


# ----------------------------------------------------------------------
# Seleção priorizada das linhas automáticas
# ----------------------------------------------------------------------

def selecionar_automaticas(
    aprovadas_auto: list[dict], max_slots: int
) -> list[dict]:
    """
    Distribui as linhas automáticas aprovadas por tipo (priorizado) e
    seguradora (rotação), preferindo páginas > 2.

    Round-robin: em cada rodada, percorre tipos na ordem de prioridade e
    pega 1 linha do tipo. Dentro do tipo, ordena pela menor contagem por
    seguradora e pelo page>2 primeiro.
    """
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in aprovadas_auto:
        buckets[row.get("tipo", "")].append(row)

    seguradora_count: dict[str, int] = defaultdict(int)
    escolhidas: list[dict] = []

    def sort_key(row: dict) -> tuple:
        page = parse_pagina(row.get("pagina_esperada"))
        return (
            seguradora_count[row.get("seguradora", "")],
            0 if page > 2 else 1,
            -page,  # entre páginas > 2, preferir as menores (mais
                    # estáveis); o sinal negativo faz o sort estável
                    # priorizar páginas substantivas próximas do início
                    # do corpo, mas após capa/sumário
        )

    while len(escolhidas) < max_slots:
        progresso = False
        for tipo in TIPO_PRIORITY:
            if len(escolhidas) >= max_slots:
                break
            bucket = buckets.get(tipo)
            if not bucket:
                continue
            bucket.sort(key=sort_key)
            row = bucket.pop(0)
            escolhidas.append(row)
            seguradora_count[row.get("seguradora", "")] += 1
            progresso = True

        # Pega também tipos fora da lista de prioridade (caso existam).
        for tipo, bucket in buckets.items():
            if tipo in TIPO_PRIORITY:
                continue
            if not bucket:
                continue
            if len(escolhidas) >= max_slots:
                break
            bucket.sort(key=sort_key)
            row = bucket.pop(0)
            escolhidas.append(row)
            seguradora_count[row.get("seguradora", "")] += 1
            progresso = True

        if not progresso:
            break

    return escolhidas


# ----------------------------------------------------------------------
# Limpeza + reescrita das linhas aprovadas
# ----------------------------------------------------------------------

def limpar_aprovada(row: dict, is_manual_row: bool) -> dict:
    out = dict(row)
    resposta_clean = collapse_whitespace(out.get("resposta_ideal_draft", ""))
    if len(resposta_clean) > RESPOSTA_MAX_CHARS:
        truncated = resposta_clean[:RESPOSTA_MAX_CHARS]
        last_space = truncated.rfind(" ")
        if last_space > RESPOSTA_MAX_CHARS * 0.5:
            truncated = truncated[:last_space]
        resposta_clean = truncated.rstrip() + "..."
    out["resposta_ideal_draft"] = resposta_clean

    out["pergunta"] = collapse_whitespace(out.get("pergunta", ""))
    out["termos_esperados"] = collapse_whitespace(
        out.get("termos_esperados", "")
    )
    out["criterio_sucesso"] = collapse_whitespace(
        out.get("criterio_sucesso", "")
    )
    out["status_revisao"] = "pendente_revisao"

    obs_original = collapse_whitespace(out.get("observacoes", ""))
    if is_manual_row:
        out["observacoes"] = obs_original
    else:
        separador = " " if obs_original else ""
        out["observacoes"] = f"{obs_original}{separador}{OBSERVACAO_APROVADA}"
    return out


# ----------------------------------------------------------------------
# Leitura/escrita
# ----------------------------------------------------------------------

def ler_draft(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"Arquivo de entrada não encontrado: {path}. "
            f"Rode generate_eval_dataset.py antes."
        )

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols_lidas = reader.fieldnames or []
        faltando = [c for c in REQUIRED_COLUMNS if c not in cols_lidas]
        if faltando:
            raise SystemExit(
                f"CSV de entrada está faltando colunas: {faltando}. "
                f"Esperado: {REQUIRED_COLUMNS}"
            )
        return list(reader)


def escrever_csv(
    path: Path, rows: list[dict], colunas: list[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=colunas, quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for row in rows:
            normalized = {k: row.get(k, "") for k in colunas}
            writer.writerow(normalized)


# ----------------------------------------------------------------------
# Pipeline principal
# ----------------------------------------------------------------------

def curate() -> dict:
    rows = ler_draft(INPUT_PATH)
    total = len(rows)

    manuais: list[dict] = []
    aprovadas_auto: list[dict] = []
    rejeitadas: list[dict] = []

    for row in rows:
        if is_manual(row):
            manuais.append(row)
            continue

        ok, motivo = avaliar_linha(row)
        if ok:
            aprovadas_auto.append(row)
        else:
            row_rej = dict(row)
            row_rej["motivo_rejeicao"] = motivo
            rejeitadas.append(row_rej)

    # Slots automáticos disponíveis = limite total - manuais.
    slots_auto = max(0, MAX_V1_ROWS - len(manuais))
    selecionadas_auto = selecionar_automaticas(aprovadas_auto, slots_auto)

    # Quaisquer aprovadas que não couberem vão para rejeitados com
    # motivo "excedeu cap de 30 linhas".
    ids_selecionadas = {r.get("id") for r in selecionadas_auto}
    for row in aprovadas_auto:
        if row.get("id") in ids_selecionadas:
            continue
        row_rej = dict(row)
        row_rej["motivo_rejeicao"] = (
            "aprovada nos filtros, mas excedeu cap de "
            f"{MAX_V1_ROWS} linhas da v1 (priorizar nas próximas versões)"
        )
        rejeitadas.append(row_rej)

    # Renumera as automáticas: Q001, Q002, ...
    renumeradas: list[dict] = []
    for i, row in enumerate(selecionadas_auto, start=1):
        cleaned = limpar_aprovada(row, is_manual_row=False)
        cleaned["id"] = f"Q{i:03d}"
        renumeradas.append(cleaned)

    manuais_limpas = [limpar_aprovada(r, is_manual_row=True) for r in manuais]

    v1_rows = manuais_limpas + renumeradas

    escrever_csv(V1_PATH, v1_rows, REQUIRED_COLUMNS)
    escrever_csv(REJECTED_PATH, rejeitadas, REJECTED_COLUMNS)

    return {
        "total_lidas": total,
        "manuais": len(manuais),
        "aprovadas_auto": len(selecionadas_auto),
        "rejeitadas": len(rejeitadas),
        "v1_rows": v1_rows,
    }


def imprimir_relatorio(stats: dict) -> None:
    v1_rows = stats["v1_rows"]
    dist_tipo: dict[str, int] = defaultdict(int)
    dist_seg: dict[str, int] = defaultdict(int)
    for r in v1_rows:
        dist_tipo[r.get("tipo", "?")] += 1
        dist_seg[r.get("seguradora", "?")] += 1

    print("=" * 60)
    print("CURADORIA — curate_eval_dataset.py")
    print("=" * 60)
    print(f"Arquivo de entrada:        {INPUT_PATH}")
    print(f"Linhas lidas:              {stats['total_lidas']}")
    print(f"  - Perguntas manuais:     {stats['manuais']}")
    print(f"  - Auto aprovadas (v1):   {stats['aprovadas_auto']}")
    print(f"  - Rejeitadas:            {stats['rejeitadas']}")
    print(f"Limite da v1:              {MAX_V1_ROWS}")
    print(f"Total final em v1:         {len(v1_rows)}")
    print(f"Arquivo v1:                {V1_PATH}")
    print(f"Arquivo rejeitadas:        {REJECTED_PATH}")

    print("\nDistribuição por tipo na v1:")
    for tipo, n in sorted(dist_tipo.items(), key=lambda x: -x[1]):
        print(f"  {tipo:<14} {n}")

    print("\nDistribuição por seguradora/órgão na v1:")
    for seg, n in sorted(dist_seg.items(), key=lambda x: -x[1]):
        print(f"  {seg:<14} {n}")

    print("\nPróximos passos de revisão humana:")
    print(
        "  1. Abrir eval/evaluation_dataset_v1.csv e revisar cada linha."
    )
    print(
        "  2. Ajustar resposta_ideal_draft, documento_esperado e "
        "pagina_esperada quando necessário."
    )
    print(
        "  3. Trocar status_revisao de 'pendente_revisao' para "
        "'aprovado' nas linhas validadas."
    )
    print(
        "  4. Olhar eval/evaluation_dataset_rejected.csv para "
        "recuperar manualmente qualquer linha boa que tenha caído fora."
    )
    print(
        "  5. Quando satisfeito, salvar como eval/evaluation_dataset.csv "
        "(dataset oficial)."
    )


def main() -> None:
    stats = curate()
    imprimir_relatorio(stats)


if __name__ == "__main__":
    main()
