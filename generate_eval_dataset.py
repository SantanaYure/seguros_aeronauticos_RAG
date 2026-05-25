"""
generate_eval_dataset.py

Gera um dataset DRAFT de avaliação (CSV) a partir dos JSONs de staging/.

Este dataset NÃO é para treino. Será usado para avaliar Retrieval, Busca
Híbrida, HyDE e o agente RAG futuro. Toda linha gerada automaticamente sai
com status_revisao="pendente_revisao" e precisa de curadoria humana antes
de ser promovida para o dataset oficial.

Não faz:
- Não chama Gemini.
- Não chama Supabase.
- Não lê .env nem usa chaves.
- Não gera embeddings.
- Não altera os JSONs em staging/.
- Não faz commit.

Uso:
    python generate_eval_dataset.py

Saída:
    eval/evaluation_dataset_draft.csv
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional


STAGING_DIR = Path("staging")
EVAL_DIR = Path("eval")
CSV_PATH = EVAL_DIR / "evaluation_dataset_draft.csv"

MIN_CHARS_PARA_GERAR = 30
MAX_TOTAL = 80
MAX_AUTO_POR_GATILHO_POR_FONTE = 3
MAX_GATILHOS_POR_PAGINA = 2
RESPOSTA_MAX_CHARS = 600
WINDOW_CHARS_BEFORE = 120
WINDOW_CHARS_AFTER = 520

CSV_HEADERS = [
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

CRITERIO_POR_TIPO = {
    "exclusao": (
        "Passa se recuperar trecho de riscos excluídos ou situação "
        "expressamente não garantida."
    ),
    "sinistro": (
        "Passa se recuperar trecho sobre recusa, perda de direito, "
        "liquidação, fraude, agravamento de risco ou obrigações em sinistro."
    ),
    "cobertura": (
        "Passa se recuperar trecho que descreva cobertura, limite, "
        "franquia ou alcance da garantia."
    ),
    "conceitual": (
        "Passa se recuperar definição ou descrição contratual "
        "suficiente do conceito."
    ),
    "regulatorio": (
        "Passa se recuperar trecho da Resolução CNSP/SUSEP 407/2021 "
        "relacionado ao tema."
    ),
    "obrigacao": (
        "Passa se recuperar trecho com deveres ou obrigações do segurado."
    ),
}


# ----------------------------------------------------------------------
# Definição dos gatilhos
#
# priority menor = mais importante. Quando uma página dispara mais de um
# gatilho, escolhemos até MAX_GATILHOS_POR_PAGINA respeitando essa ordem.
#
# templates_seg: usados em páginas de Condições Gerais (uma seguradora).
# templates_susep: usados em páginas da Resolução SUSEP 407/2021.
# ----------------------------------------------------------------------
TRIGGERS = [
    {
        "priority": 1,
        "key": "riscos_excluidos",
        "patterns": ["riscos excluídos", "riscos excluidos"],
        "tipo": "exclusao",
        "escopo": "seguradora",
        "templates_seg": [
            "Quais são os riscos excluídos na seguradora {seguradora}?",
            "O que não está garantido pelo seguro da {seguradora}?",
            "Quais exclusões aparecem nas condições gerais da {seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "riscos excluídos",
            "não garantidos",
            "segurado",
            "danos",
            "operação",
        ],
        "dificuldade": "facil",
    },
    {
        "priority": 2,
        "key": "perda_de_direito",
        "patterns": ["perda de direito", "perda do direito"],
        "tipo": "sinistro",
        "escopo": "seguradora",
        "templates_seg": [
            "Quando o segurado perde o direito à indenização na {seguradora}?",
            "Quais condutas podem causar perda de direito no seguro da "
            "{seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "perda de direito",
            "indenização",
            "segurado",
            "conduta",
            "agravamento",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 3,
        "key": "recusa_de_sinistro",
        "patterns": ["recusa de sinistro", "recusa do sinistro"],
        "tipo": "sinistro",
        "escopo": "seguradora",
        "templates_seg": [
            "Quando a seguradora {seguradora} pode recusar um sinistro?",
            "Como a {seguradora} deve comunicar a recusa de sinistro?",
        ],
        "templates_susep": [],
        "termos": [
            "recusa",
            "sinistro",
            "indenização",
            "comunicação",
            "seguradora",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 4,
        "key": "responsabilidade_civil",
        "patterns": ["responsabilidade civil"],
        "tipo": "conceitual",
        "escopo": "seguradora",
        "templates_seg": [
            "O que cobre a responsabilidade civil na seguradora {seguradora}?",
            "Quais danos de responsabilidade civil são tratados pela "
            "{seguradora}?",
            "O que é responsabilidade civil no seguro aeronáutico segundo "
            "a {seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "responsabilidade civil",
            "danos",
            "terceiros",
            "cobertura",
            "segurado",
        ],
        "dificuldade": "facil",
    },
    {
        "priority": 5,
        "key": "obrigacoes_segurado",
        "patterns": [
            "obrigações do segurado",
            "obrigacoes do segurado",
            "deveres do segurado",
        ],
        "tipo": "obrigacao",
        "escopo": "seguradora",
        "templates_seg": [
            "Quais são as principais obrigações do segurado na "
            "{seguradora}?",
            "O que o segurado deve fazer em caso de sinistro segundo a "
            "{seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "obrigações",
            "segurado",
            "deveres",
            "sinistro",
            "comunicação",
        ],
        "dificuldade": "facil",
    },
    {
        "priority": 6,
        "key": "limite_maximo_indenizacao",
        "patterns": [
            "limite máximo de indenização",
            "limite maximo de indenizacao",
            "limite máximo de garantia",
            "limite maximo de garantia",
        ],
        "tipo": "cobertura",
        "escopo": "seguradora",
        "templates_seg": [
            "O que é o limite máximo de indenização nas condições da "
            "{seguradora}?",
            "Como o limite máximo de indenização afeta o pagamento do "
            "sinistro na {seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "limite máximo",
            "indenização",
            "garantia",
            "cobertura",
            "valor",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 7,
        "key": "liquidacao_sinistros",
        "patterns": [
            "liquidação de sinistros",
            "liquidacao de sinistros",
            "liquidação do sinistro",
            "liquidacao do sinistro",
        ],
        "tipo": "sinistro",
        "escopo": "seguradora",
        "templates_seg": [
            "Como funciona a liquidação de sinistros na {seguradora}?",
            "Quais documentos são exigidos para liquidação de sinistro "
            "na {seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "liquidação",
            "sinistro",
            "documentos",
            "indenização",
            "prazo",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 8,
        "key": "franquia",
        "patterns": ["franquia"],
        "tipo": "cobertura",
        "escopo": "seguradora",
        "templates_seg": [
            "Como a franquia é tratada nas condições da {seguradora}?",
        ],
        "templates_susep": [],
        "termos": ["franquia", "indenização", "valor", "cobertura", "sinistro"],
        "dificuldade": "facil",
    },
    {
        "priority": 9,
        "key": "ambito_geografico",
        "patterns": ["âmbito geográfico", "ambito geografico"],
        "tipo": "cobertura",
        "escopo": "seguradora",
        "templates_seg": [
            "Qual é o âmbito geográfico da cobertura na {seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "âmbito geográfico",
            "território",
            "cobertura",
            "Brasil",
            "seguro",
        ],
        "dificuldade": "facil",
    },
    {
        "priority": 10,
        "key": "grandes_riscos",
        "patterns": ["grandes riscos"],
        "tipo": "regulatorio",
        "escopo": "regulatorio",
        "templates_seg": [],
        "templates_susep": [
            "O que a Resolução CNSP/SUSEP 407/2021 trata sobre grandes "
            "riscos?",
            "Como a norma de grandes riscos se relaciona com estes seguros "
            "aeronáuticos?",
        ],
        "termos": [
            "grandes riscos",
            "Resolução 407",
            "SUSEP",
            "CNSP",
            "enquadramento",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 10,
        "key": "cnsp_susep",
        "patterns": ["cnsp", "susep"],
        "tipo": "regulatorio",
        "escopo": "regulatorio",
        "templates_seg": [],
        "templates_susep": [
            "Qual é o papel da Resolução CNSP/SUSEP 407/2021 no "
            "enquadramento do seguro?",
        ],
        "termos": [
            "CNSP",
            "SUSEP",
            "regulação",
            "enquadramento",
            "grandes riscos",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 11,
        "key": "agravamento_de_risco",
        "patterns": ["agravamento de risco", "agravamento do risco"],
        "tipo": "sinistro",
        "escopo": "seguradora",
        "templates_seg": [
            "O que acontece se houver agravamento de risco pelo segurado "
            "na {seguradora}?",
            "O agravamento intencional do risco pode afetar a indenização "
            "na {seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "agravamento",
            "risco",
            "segurado",
            "indenização",
            "intencional",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 12,
        "key": "fraude",
        "patterns": ["fraude"],
        "tipo": "sinistro",
        "escopo": "seguradora",
        "templates_seg": [
            "Como a fraude pode afetar o direito à indenização na "
            "{seguradora}?",
            "Em quais situações a fraude pode levar à negativa de "
            "indenização na {seguradora}?",
        ],
        "templates_susep": [],
        "termos": ["fraude", "indenização", "negativa", "segurado", "perda"],
        "dificuldade": "dificil",
    },
    {
        "priority": 13,
        "key": "nao_estao_garantidas",
        "patterns": ["não estão garantidas", "nao estao garantidas"],
        "tipo": "exclusao",
        "escopo": "seguradora",
        "templates_seg": [
            "Quais situações não estão garantidas pelo seguro da "
            "{seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "não garantidas",
            "exclusão",
            "segurado",
            "seguro",
            "danos",
        ],
        "dificuldade": "medio",
    },
    {
        "priority": 14,
        "key": "exclusoes",
        "patterns": ["exclusões", "exclusoes"],
        "tipo": "exclusao",
        "escopo": "seguradora",
        "templates_seg": [
            "Quais exclusões são previstas nas condições gerais da "
            "{seguradora}?",
        ],
        "templates_susep": [],
        "termos": [
            "exclusões",
            "condições gerais",
            "seguradora",
            "riscos",
            "segurado",
        ],
        "dificuldade": "facil",
    },
]


# ----------------------------------------------------------------------
# Perguntas manuais (fixas, vindas do test_match.py + observação curatorial)
# ----------------------------------------------------------------------
MANUAL_QUESTIONS = [
    {
        "id": "Q_manual_001",
        "pergunta": "O que é casco aeronáutico?",
        "tipo": "conceitual",
        "escopo": "geral",
        "seguradora": "TODAS",
        "documento_esperado": "",
        "pagina_esperada": "",
        "termos_esperados": (
            "casco aeronáutico; aeronave; cobertura; danos materiais; "
            "responsabilidade"
        ),
        "resposta_ideal_draft": (
            "Revisar manualmente: casco aeronáutico é tipicamente coberto "
            "em apólice de Casco, não em RC Hangar. A resposta ideal deve "
            "reconhecer ausência de base nesta coleção e sugerir o produto "
            "correto."
        ),
        "criterio_sucesso": (
            "Passa se o agente reconhecer ausência de base suficiente "
            "nestes documentos e responder com cautela."
        ),
        "nivel_dificuldade": "dificil",
        "status_revisao": "pendente_revisao",
        "observacoes": (
            "Pergunta manual reutilizada do test_match.py. Pode estar fora "
            "do escopo de RC Hangar; serve para testar comportamento "
            "seguro do agente."
        ),
    },
    {
        "id": "Q_manual_002",
        "pergunta": "O seguro cobre pane seca?",
        "tipo": "exclusao",
        "escopo": "geral",
        "seguradora": "TODAS",
        "documento_esperado": "",
        "pagina_esperada": "",
        "termos_esperados": (
            "pane seca; falta de combustível; operação irregular; "
            "inobservância de normas; agravamento de risco"
        ),
        "resposta_ideal_draft": (
            "Revisar manualmente: termo coloquial. A resposta ideal deve "
            "verificar se há exclusão expressa ou se a situação cai em "
            "operação irregular, falta de combustível, agravamento de "
            "risco ou inobservância de normas aeronáuticas."
        ),
        "criterio_sucesso": (
            "Passa se recuperar exclusões/cláusulas que tratem de falta "
            "de combustível, operação irregular ou agravamento de risco."
        ),
        "nivel_dificuldade": "dificil",
        "status_revisao": "pendente_revisao",
        "observacoes": (
            "Pergunta manual. Pode exigir busca híbrida ou expansão de "
            "query (sinônimos do mercado securitário)."
        ),
    },
    {
        "id": "Q_manual_003",
        "pergunta": "O que significa exclusão operacional?",
        "tipo": "exclusao",
        "escopo": "geral",
        "seguradora": "TODAS",
        "documento_esperado": "",
        "pagina_esperada": "",
        "termos_esperados": (
            "exclusão; operacional; riscos excluídos; autorização; "
            "licença; normas"
        ),
        "resposta_ideal_draft": (
            "Revisar manualmente: a expressão pode não aparecer "
            "literalmente. A resposta ideal deve mapear equivalentes "
            "ligados a riscos excluídos, autorização, licença e normas "
            "operacionais."
        ),
        "criterio_sucesso": (
            "Passa se recuperar trechos de riscos excluídos vinculados a "
            "operação irregular, falta de licença ou inobservância de "
            "normas."
        ),
        "nivel_dificuldade": "dificil",
        "status_revisao": "pendente_revisao",
        "observacoes": (
            "Pergunta manual. Boa para validar capacidade do agente de "
            "encontrar equivalentes lexicais."
        ),
    },
    {
        "id": "Q_manual_004",
        "pergunta": "O que é responsabilidade civil no seguro aeronáutico?",
        "tipo": "conceitual",
        "escopo": "geral",
        "seguradora": "TODAS",
        "documento_esperado": "",
        "pagina_esperada": "",
        "termos_esperados": (
            "responsabilidade civil; danos; terceiros; cobertura; "
            "segurado; aeronáutico"
        ),
        "resposta_ideal_draft": (
            "Revisar manualmente: definir RC com base nas Condições "
            "Gerais das seguradoras e, quando cabível, na Resolução "
            "CNSP/SUSEP 407/2021. Resposta deve citar danos a terceiros "
            "e fonte específica."
        ),
        "criterio_sucesso": (
            "Passa se recuperar definição ou descrição contratual de "
            "responsabilidade civil em ao menos uma fonte."
        ),
        "nivel_dificuldade": "facil",
        "status_revisao": "pendente_revisao",
        "observacoes": (
            "Pergunta manual. Deve funcionar bem na base atual."
        ),
    },
    {
        "id": "Q_manual_005",
        "pergunta": "Quando a seguradora pode negar indenização?",
        "tipo": "sinistro",
        "escopo": "geral",
        "seguradora": "TODAS",
        "documento_esperado": "",
        "pagina_esperada": "",
        "termos_esperados": (
            "negativa; indenização; recusa; perda de direito; fraude; "
            "agravamento de risco; exclusões; obrigações do segurado"
        ),
        "resposta_ideal_draft": (
            "Revisar manualmente: a resposta ideal deve enumerar hipóteses "
            "de recusa, perda de direito, fraude, agravamento de risco, "
            "exclusões expressas e descumprimento de obrigações do "
            "segurado, citando fonte específica."
        ),
        "criterio_sucesso": (
            "Passa se recuperar trechos cobrindo recusa de sinistro, "
            "perda de direito, fraude, agravamento de risco, exclusões "
            "ou obrigações do segurado."
        ),
        "nivel_dificuldade": "medio",
        "status_revisao": "pendente_revisao",
        "observacoes": (
            "Pergunta manual. Verifica capacidade de cobertura ampla "
            "sobre razões de negativa."
        ),
    },
]


# ----------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------

def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_trigger_window(
    text: str, pattern: str, before: int, after: int
) -> str:
    lower = text.lower()
    idx = lower.find(pattern.lower())
    if idx < 0:
        return text[: before + after]
    start = max(0, idx - before)
    end = min(len(text), idx + len(pattern) + after)
    return text[start:end]


def build_resposta_draft(window: str, max_chars: int) -> str:
    cleaned = collapse_whitespace(window)
    if len(cleaned) < 40:
        return (
            "Revisar manualmente: o trecho indica o tema, mas a resposta "
            "ideal precisa ser validada."
        )
    if len(cleaned) > max_chars:
        truncated = cleaned[:max_chars]
        last_space = truncated.rfind(" ")
        if last_space > max_chars * 0.5:
            truncated = truncated[:last_space]
        cleaned = truncated.rstrip() + "..."
    return cleaned


def detect_triggers_on_page(text: str) -> list[dict]:
    """Retorna os gatilhos encontrados, ordenados por priority."""
    lower = text.lower()
    matched = []
    for trig in TRIGGERS:
        for pat in trig["patterns"]:
            if pat.lower() in lower:
                matched.append(trig)
                break
    matched.sort(key=lambda t: t["priority"])
    return matched


def load_staging_files() -> list[dict]:
    files = sorted(STAGING_DIR.glob("*.json"))
    pages = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARN] Falha ao ler {path.name}: {exc}")
            continue
        pages.append(data)
    return pages


def fonte_da_pagina(page: dict) -> tuple[str, str]:
    """
    Retorna (label_seguradora_ou_orgao, escopo_default).
    """
    meta = page.get("metadata", {}) or {}
    seg = meta.get("seguradora")
    orgao = meta.get("orgao")
    if seg:
        return seg, "seguradora"
    if orgao:
        return orgao, "regulatorio"
    return "DESCONHECIDO", "geral"


# ----------------------------------------------------------------------
# Geração
# ----------------------------------------------------------------------

def ordenar_paginas_round_robin(pages: list[dict]) -> list[dict]:
    """
    Agrupa páginas por fonte (seguradora/órgão) e intercala em
    round-robin. Garante que todas as fontes apareçam antes do cap
    global ser atingido.
    """
    por_fonte: dict[str, list[dict]] = defaultdict(list)
    for page in pages:
        fonte_label, _ = fonte_da_pagina(page)
        por_fonte[fonte_label].append(page)

    fontes = sorted(por_fonte.keys())
    max_len = max((len(v) for v in por_fonte.values()), default=0)

    ordered: list[dict] = []
    for i in range(max_len):
        for fonte in fontes:
            bucket = por_fonte[fonte]
            if i < len(bucket):
                ordered.append(bucket[i])
    return ordered


def gerar_dataset() -> tuple[list[dict], dict]:
    pages = load_staging_files()
    total_json = len(pages)
    ignoradas_curtas = 0

    template_counter: dict[tuple[str, str], int] = defaultdict(int)
    count_gatilho_fonte: dict[tuple[str, str], int] = defaultdict(int)
    perguntas_seen: set[str] = set()

    # Pré-popula com as perguntas manuais para evitar duplicidade exata.
    for m in MANUAL_QUESTIONS:
        perguntas_seen.add(m["pergunta"].strip().lower())

    auto_limit = max(0, MAX_TOTAL - len(MANUAL_QUESTIONS))
    rows_auto: list[dict] = []
    next_id = 1

    ordered_pages = ordenar_paginas_round_robin(pages)

    for page in ordered_pages:
        texto = page.get("texto") or ""
        if len(texto.strip()) < MIN_CHARS_PARA_GERAR:
            ignoradas_curtas += 1
            continue

        if len(rows_auto) >= auto_limit:
            break

        nome_arquivo = page.get("nome_arquivo", "")
        pagina = page.get("pagina", "")
        fonte_label, escopo_default = fonte_da_pagina(page)
        is_susep = escopo_default == "regulatorio"

        triggers_on_page = detect_triggers_on_page(texto)
        if not triggers_on_page:
            continue

        used_on_page = 0
        for trig in triggers_on_page:
            if used_on_page >= MAX_GATILHOS_POR_PAGINA:
                break
            if len(rows_auto) >= auto_limit:
                break

            templates = (
                trig["templates_susep"] if is_susep else trig["templates_seg"]
            )
            if not templates:
                continue

            counter_key = (trig["key"], fonte_label)
            if (
                count_gatilho_fonte[counter_key]
                >= MAX_AUTO_POR_GATILHO_POR_FONTE
            ):
                continue

            # Escolhe template ainda não usado (rotaciona).
            pergunta_text = None
            for _ in range(len(templates)):
                idx = template_counter[counter_key] % len(templates)
                template_counter[counter_key] += 1
                candidate = templates[idx].format(seguradora=fonte_label)
                candidate_norm = candidate.strip().lower()
                if candidate_norm not in perguntas_seen:
                    pergunta_text = candidate
                    break
            if pergunta_text is None:
                continue

            perguntas_seen.add(pergunta_text.strip().lower())
            count_gatilho_fonte[counter_key] += 1
            used_on_page += 1

            window = find_trigger_window(
                texto,
                trig["patterns"][0],
                WINDOW_CHARS_BEFORE,
                WINDOW_CHARS_AFTER,
            )
            resposta = build_resposta_draft(window, RESPOSTA_MAX_CHARS)

            seguradora_col = (
                "CNSP_SUSEP" if is_susep else fonte_label
            )
            escopo_col = "regulatorio" if is_susep else "seguradora"

            termos = list(trig["termos"])
            for pat in trig["patterns"][:1]:
                if pat not in termos:
                    termos.insert(0, pat)
            termos_str = "; ".join(termos[:8])

            row = {
                "id": f"Q{next_id:03d}",
                "pergunta": pergunta_text,
                "tipo": trig["tipo"],
                "escopo": escopo_col,
                "seguradora": seguradora_col,
                "documento_esperado": nome_arquivo,
                "pagina_esperada": pagina,
                "termos_esperados": termos_str,
                "resposta_ideal_draft": resposta,
                "criterio_sucesso": CRITERIO_POR_TIPO[trig["tipo"]],
                "nivel_dificuldade": trig["dificuldade"],
                "status_revisao": "pendente_revisao",
                "observacoes": (
                    f"Pergunta gerada automaticamente a partir do gatilho "
                    f"'{trig['patterns'][0]}'. Revisar pergunta, resposta "
                    f"e termos antes de aprovar."
                ),
            }
            rows_auto.append(row)
            next_id += 1

    stats = {
        "total_json": total_json,
        "ignoradas_curtas": ignoradas_curtas,
        "auto_geradas": len(rows_auto),
        "manuais": len(MANUAL_QUESTIONS),
        "total_csv": len(rows_auto) + len(MANUAL_QUESTIONS),
    }
    return rows_auto, stats


# ----------------------------------------------------------------------
# Escrita do CSV + resumo
# ----------------------------------------------------------------------

def escrever_csv(rows_auto: list[dict]) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(MANUAL_QUESTIONS) + rows_auto

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=CSV_HEADERS, quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for row in rows:
            normalized = {k: row.get(k, "") for k in CSV_HEADERS}
            writer.writerow(normalized)


def imprimir_resumo(rows_auto: list[dict], stats: dict) -> None:
    todas = list(MANUAL_QUESTIONS) + rows_auto

    dist_tipo: dict[str, int] = defaultdict(int)
    dist_seg: dict[str, int] = defaultdict(int)
    for r in todas:
        dist_tipo[r.get("tipo", "?")] += 1
        dist_seg[r.get("seguradora", "?")] += 1

    print("=" * 60)
    print("RESUMO — generate_eval_dataset.py")
    print("=" * 60)
    print(f"Total de JSONs lidos:                 {stats['total_json']}")
    print(
        f"Páginas ignoradas (texto < "
        f"{MIN_CHARS_PARA_GERAR} chars): {stats['ignoradas_curtas']}"
    )
    print(f"Perguntas automáticas geradas:        {stats['auto_geradas']}")
    print(f"Perguntas manuais adicionadas:        {stats['manuais']}")
    print(f"Total final de linhas no CSV:         {stats['total_csv']}")
    print(f"Limite global definido:               {MAX_TOTAL}")

    print("\nDistribuição por tipo:")
    for tipo, n in sorted(dist_tipo.items(), key=lambda x: -x[1]):
        print(f"  {tipo:<14} {n}")

    print("\nDistribuição por seguradora/órgão:")
    for seg, n in sorted(dist_seg.items(), key=lambda x: -x[1]):
        print(f"  {seg:<14} {n}")

    print(f"\nArquivo gerado: {CSV_PATH}")
    print(
        "\nLembrete: este CSV é DRAFT. Cada linha precisa de revisão "
        "humana (ver eval/README.md)."
    )


def main() -> None:
    if not STAGING_DIR.is_dir():
        raise SystemExit(
            f"Diretório {STAGING_DIR}/ não encontrado. "
            f"Rode parse_pdf.py antes."
        )

    rows_auto, stats = gerar_dataset()
    escrever_csv(rows_auto)
    imprimir_resumo(rows_auto, stats)


if __name__ == "__main__":
    main()
