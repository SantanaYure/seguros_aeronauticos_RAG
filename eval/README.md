# Dataset de Avaliação — `eval/`

Este diretório contém o **dataset de avaliação** do RAG especialista em
seguros aeronáuticos. **Não é dataset de treino.** Ele será usado para
medir a qualidade da busca vetorial, da busca híbrida, do HyDE e do
agente RAG final.

> **Importante:** todos os arquivos aqui são *drafts*. Eles foram
> gerados automaticamente a partir dos JSONs em `staging/` e
> **precisam de revisão humana** antes de virarem dataset oficial.

---

## Arquivos

| Arquivo | O que é | Origem |
|---|---|---|
| `evaluation_dataset_draft.csv` | **Rascunho bruto.** 80 perguntas (5 manuais + 75 automáticas) extraídas por gatilhos lexicais nas páginas. Tem boas perguntas, mas também várias originadas de capa, sumário, índice ou trechos com ruído de extração. | `generate_eval_dataset.py` |
| `evaluation_dataset_v1.csv` | **Versão filtrada para revisão humana.** Até 30 linhas, vindas do draft após uma curadoria automática que remove respostas curtas, vazias, com pontos de índice, termos de capa/contato/registro e linhas que não trazem sinal forte para o próprio tipo. | `curate_eval_dataset.py` |
| `evaluation_dataset_rejected.csv` | **Linhas rejeitadas** pela curadoria, com a coluna `motivo_rejeicao` explicando o motivo. Útil para auditoria e para recuperar manualmente alguma linha boa que tenha caído fora. | `curate_eval_dataset.py` |
| `evaluation_dataset.csv` | **Dataset oficial preliminar.** Versão da v1 após revisão assistida (sem LLM): espaços normalizados, `status_revisao = aprovado_preliminar` e coluna nova `revisao_observacao` com alertas automáticos por linha. Ainda passível de refinamento humano. | `review_eval_dataset.py` |
| `evaluation_dataset_review.md` | **Versão Markdown** do dataset oficial preliminar, legível em uma passagem. Útil para revisão humana sem abrir planilha. Edições devem ser feitas no CSV, não aqui. | `review_eval_dataset.py` |

---

## Estrutura do CSV

Todos os CSVs deste diretório seguem a mesma ordem de colunas:

| Coluna | Descrição |
|---|---|
| `id` | Identificador único. Manuais: `Q_manual_001`..`Q_manual_005`. Automáticas: `Q001`, `Q002`, ... |
| `pergunta` | Pergunta a ser feita ao retrieval / RAG. |
| `tipo` | `conceitual`, `cobertura`, `exclusao`, `sinistro`, `obrigacao`, `regulatorio`, `comparacao`. |
| `escopo` | `seguradora`, `regulatorio`, `geral`, `comparativo`. |
| `seguradora` | `AXA`, `Essor`, `Excelsior`, `EZZE`, `Mapfre`, `CNSP_SUSEP` ou `TODAS`. |
| `documento_esperado` | Nome do PDF que originou a pergunta (`nome_arquivo` do JSON). Vazio nas manuais. |
| `pagina_esperada` | Página que originou a pergunta. Vazio nas manuais. |
| `termos_esperados` | 3 a 8 termos-chave separados por `;`. |
| `resposta_ideal_draft` | Resposta inicial conservadora, baseada no trecho da página. Até 600 caracteres. |
| `criterio_sucesso` | Critério para considerar a busca/resposta como aprovada. |
| `nivel_dificuldade` | `facil`, `medio`, `dificil`. |
| `status_revisao` | `pendente_revisao` no draft e na v1. Vira `aprovado_preliminar` em `evaluation_dataset.csv` (passou pela revisão automática). O revisor humano deve trocá-lo para `aprovado` quando confirmar a linha. |
| `observacoes` | Anotações sobre origem e cuidados. |
| `revisao_observacao` | (Só em `evaluation_dataset.csv`.) Alertas automáticos por linha, separados por ` \| ` (ex.: `resposta ideal curta`, `possível ruído de capa ou contato`, `resposta pode não conter exclusão substantiva`). `ok para avaliação preliminar` quando nenhum alerta dispara. |

O arquivo `evaluation_dataset_rejected.csv` adiciona a coluna
`motivo_rejeicao` ao final. O arquivo `evaluation_dataset.csv`
adiciona a coluna `revisao_observacao` ao final.

### Estados de `status_revisao`

| Valor | Significa |
|---|---|
| `pendente_revisao` | Linha gerada automaticamente, ainda não passou por nenhuma revisão. |
| `aprovado_preliminar` | Linha passou pela revisão assistida automática (`review_eval_dataset.py`). É segura para avaliação preliminar, mas ainda pode ser refinada. |
| `aprovado` | Linha foi revisada por um especialista humano. É a versão final usada nas avaliações oficiais. |

---

## Como revisar a v1

Para cada linha de `evaluation_dataset_v1.csv`:

1. **Verificar a pergunta.** Está bem formada? Faz sentido para a
   seguradora indicada? Reformular se necessário.
2. **Conferir `documento_esperado` e `pagina_esperada`.** Abrir o JSON
   correspondente em `staging/<nome_arquivo>_pagina_<N>.json` e
   confirmar que a página realmente contém a melhor fonte para
   responder. Se houver uma página melhor, ajustar.
3. **Reescrever `resposta_ideal_draft`.** O draft é uma extração crua
   do trecho da página, então frequentemente começa em meio de palavra
   ou contém ruído de PDF. A versão final deve ser:
   - curta (recomendado < 400 caracteres);
   - conservadora;
   - fiel à fonte;
   - sem texto institucional, sem rodapé, sem índice.
4. **Validar `termos_esperados`.** Eles devem refletir o que esperamos
   que apareça nos chunks recuperados pelo retrieval.
5. **Validar `criterio_sucesso`.** Está coerente com o `tipo`?
6. **Atualizar `status_revisao`.** Trocar de `pendente_revisao` para
   `aprovado` apenas quando estiver tudo conferido.
7. **Atualizar `observacoes`.** Pode trocar a observação automática
   ("Selecionado automaticamente para revisão v1...") por uma nota
   real ("Aprovado em DD/MM por <revisor>", por exemplo).

### Olhando para a lista de rejeitadas

Antes de fechar a v1, dar uma passada em
`evaluation_dataset_rejected.csv`. O filtro automático é conservador e
pode ter descartado linhas que, com uma resposta_ideal_draft
reescrita à mão, virariam linhas excelentes. Em particular, vale
recuperar:

- linhas marcadas como `aprovada nos filtros, mas excedeu cap de 30
  linhas` (são linhas tecnicamente boas, só não couberam);
- linhas marcadas como `não possui sinal forte para o tipo da pergunta`
  cujo trecho, mesmo assim, traz uma resposta útil.

---

## Como promover para dataset oficial

O fluxo recomendado é:

1. Rodar `curate_eval_dataset.py` para gerar `evaluation_dataset_v1.csv`.
2. Rodar `review_eval_dataset.py` para gerar
   `evaluation_dataset.csv` (oficial preliminar) e
   `evaluation_dataset_review.md` (versão legível).
3. Revisar cada linha em `evaluation_dataset.csv`:
   - Ler `revisao_observacao` para entender o que ficou suspeito.
   - Ajustar `resposta_ideal_draft`, `documento_esperado`,
     `pagina_esperada` quando necessário, consultando o JSON
     correspondente em `staging/`.
   - Quando estiver satisfeito, trocar `status_revisao` de
     `aprovado_preliminar` para `aprovado`.
4. (Opcional) reincorporar manualmente linhas da
   `evaluation_dataset_rejected.csv` cujo `motivo_rejeicao` seja
   `excedeu cap de 30 linhas`. São tecnicamente boas, só não couberam.
5. Versionar `evaluation_dataset.csv` (sem dados sensíveis — são
   apenas apólices públicas e a Resolução SUSEP).

Esse arquivo `evaluation_dataset.csv` será o input dos próximos
scripts:

- `test_retrieval.py` (comparação de modalidades de busca: vetorial
  pura, híbrida com FTS e HyDE).
- Avaliação do agente final (`agent.py`), com *LLM as a Judge*.

---

## Perguntas manuais (Q_manual_001..005)

As cinco perguntas manuais vêm do `test_match.py` e foram incluídas
de propósito porque servem para testar **comportamento seguro do
agente** em casos limítrofes:

- `Q_manual_001` "O que é casco aeronáutico?" — pode estar fora do
  escopo de RC Hangar; o agente deve reconhecer a ausência de base.
- `Q_manual_002` "O seguro cobre pane seca?" — termo coloquial;
  exige busca híbrida ou expansão de sinônimos.
- `Q_manual_003` "O que significa exclusão operacional?" — expressão
  que pode não aparecer literalmente; testa mapeamento de
  equivalentes.
- `Q_manual_004` "O que é responsabilidade civil no seguro
  aeronáutico?" — deve funcionar bem.
- `Q_manual_005` "Quando a seguradora pode negar indenização?" —
  exige cobertura ampla (recusa, perda de direito, fraude,
  agravamento, exclusões, obrigações).

**Mantenha estas perguntas mesmo se forem aparentemente "ruins" para
o retrieval atual.** Elas são parte do teste de robustez do agente.

---

## Reprodutibilidade

Para regenerar do zero:

```powershell
# 1. Gerar o draft a partir dos JSONs em staging/
.\.venv\Scripts\python generate_eval_dataset.py

# 2. Curar o draft (gera v1 + rejected)
.\.venv\Scripts\python curate_eval_dataset.py

# 3. Revisão assistida da v1 (gera evaluation_dataset.csv + .md)
.\.venv\Scripts\python review_eval_dataset.py
```

Os três scripts são puramente locais: **não chamam Gemini, não
chamam Supabase, não tocam em `staging/` e não leem chaves do
`.env`**.
