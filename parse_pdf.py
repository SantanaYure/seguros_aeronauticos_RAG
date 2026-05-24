#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de ETL e Ingestão (Passo 1)
-----------------------------------
Este script lê os arquivos PDF originais da pasta `dados/raw/` (a Resolução SUSEP 407/2021
e as 5 apólices de seguros das companhias AXA, Essor, Excelsior, EZZE e Mapfre),
extrai o texto página por página, limpa o conteúdo aplicando normalizações
e mapeia rigidamente os metadados. As páginas processadas são salvas individualmente
como arquivos JSON na pasta `staging/`.

Autor: Engenheiro de IA Sênior
Data: Maio de 2026
"""

import json
import logging
import os
import re
from pathlib import Path
from pypdf import PdfReader

# Configuração de logging detalhado para o terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def limpar_texto(texto: str) -> str:
    """
    Aplica uma limpeza básica de string no texto extraído:
    - Normaliza quebras de linha e remove retornos de carro (\r).
    - Corrige palavras hifenizadas no fim de linha (ex: "aero-\nnáutico" -> "aeronáutico").
    - Une linhas órfãs (linhas que não terminam com pontuação de fim de sentença ou de item
      como '.', '!', '?', ':', ';'), garantindo que tabelas e cláusulas de exclusão 
      (ex: AVN38B, AVN46B, AVN48B) fiquem em formato corrido legível.
    - Une múltiplos espaços em branco consecutivos em um único espaço.

    Args:
        texto (str): Texto bruto extraído do PDF.

    Returns:
        str: Texto limpo e normalizado.
    """
    if not texto:
        return ""
    
    # 1. Normalizar finais de linha e remover carriage returns (\r)
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. Corrigir hifenações de quebra de linha (junta sílabas separadas por hífen e nova linha)
    texto = re.sub(r'(\w+)-\n\s*(\w+)', r'\1\2', texto)
    
    # 3. Remover quebras de linha órfãs que quebram frases no meio
    linhas = texto.split('\n')
    linhas_limpas = []
    
    # Caracteres que indicam o término natural de uma frase, cláusula ou item estrutural
    pontuacoes_fim = ('.', '!', '?', ':', ';')
    
    for linha in linhas:
        linha_tr = linha.strip()
        if not linha_tr:
            continue
        
        if linhas_limpas:
            linha_anterior = linhas_limpas[-1]
            # Se a linha anterior NÃO termina com pontuação de fim de frase, junta-se com a atual
            if not linha_anterior.endswith(pontuacoes_fim):
                linhas_limpas[-1] = f"{linha_anterior} {linha_tr}"
                continue
                
        linhas_limpas.append(linha_tr)
        
    # 4. Unir linhas limpas por quebra de linha real (parágrafos remanescentes)
    texto_corrido = "\n".join(linhas_limpas)
    
    # 5. Normalizar espaçamentos horizontais (tabs e múltiplos espaços -> único espaço)
    texto_corrido = re.sub(r'[ \t]+', ' ', texto_corrido)
    
    return texto_corrido.strip()


def obter_metadados(nome_arquivo: str, pagina: int) -> dict:
    """
    Injeta e mapeia rigidamente os metadados com base no nome do arquivo original.
    
    Args:
        nome_arquivo (str): Nome do arquivo PDF (ex: 'SUSEP 407_2021.pdf').
        pagina (int): Número da página do PDF (1-indexada).

    Returns:
        dict: Dicionário contendo os metadados estritos mapeados.
    """
    nome_upper = nome_arquivo.upper()
    
    # Metadados padrões obrigatórios comuns
    metadata = {
        "enquadramento": "grandes_riscos_407_2021",
        "pagina": pagina
    }
    
    # Caso 1: Resolução CNSP/SUSEP 407/2021 (Resolução mestre)
    if "SUSEP" in nome_upper or "407_2021" in nome_upper:
        metadata["tipo"] = "resolucao_mestre"
        metadata["orgao"] = "CNSP_SUSEP"
        
    # Caso 2: Apólices das Seguradoras (Condições Gerais)
    else:
        metadata["tipo"] = "condicoes_gerais"
        
        # Mapeamento do nome da seguradora
        if "AXA" in nome_upper:
            metadata["seguradora"] = "AXA"
        elif "ESSOR" in nome_upper:
            metadata["seguradora"] = "Essor"
        elif "EXCELSIOR" in nome_upper:
            metadata["seguradora"] = "Excelsior"
        elif "EZZE" in nome_upper:
            metadata["seguradora"] = "EZZE"
        elif "MAPFRE" in nome_upper:
            metadata["seguradora"] = "Mapfre"
        else:
            metadata["seguradora"] = "Desconhecida"
            logger.warning(f"Seguradora não identificada no nome do arquivo: {nome_arquivo}")
            
    return metadata


def sanitizar_nome_json(nome_arquivo_pdf: str, pagina: int) -> str:
    """
    Gera um nome de arquivo JSON padronizado e sanitizado baseado na página e no nome do PDF.

    Args:
        nome_arquivo_pdf (str): Nome original do PDF.
        pagina (int): Número da página.

    Returns:
        str: Nome do arquivo JSON correspondente.
    """
    nome_base = Path(nome_arquivo_pdf).stem
    # Remove caracteres especiais e espaços, substituindo por underscores
    nome_sanitizado = re.sub(r'[^a-zA-Z0-9_]', '_', nome_base.replace(' ', '_'))
    nome_sanitizado = re.sub(r'_+', '_', nome_sanitizado).strip('_')
    return f"{nome_sanitizado}_pagina_{pagina}.json"


def processar_pdf(caminho_pdf: Path, caminho_destino: Path) -> None:
    """
    Lê um arquivo PDF página por página, extrai, limpa o texto, gera os metadados correspondentes
    e salva cada página como um arquivo JSON individual no diretório de destino.

    Args:
        caminho_pdf (Path): Caminho completo para o arquivo PDF bruto.
        caminho_destino (Path): Diretório onde os arquivos JSON serão salvos.
    """
    nome_arquivo = caminho_pdf.name
    logger.info(f"Iniciando processamento do arquivo: {nome_arquivo}")
    
    try:
        reader = PdfReader(caminho_pdf)
        total_paginas = len(reader.pages)
        logger.info(f"Arquivo '{nome_arquivo}' carregado com sucesso. Total de páginas: {total_paginas}")
        
        for i in range(total_paginas):
            pagina_numero = i + 1  # 1-indexado
            logger.info(f"Processando {caminho_pdf.stem} - Página {pagina_numero}/{total_paginas}...")
            
            try:
                # Extração de texto bruto da página
                pagina = reader.pages[i]
                texto_bruto = pagina.extract_text()
                
                # Se não houver texto extraído (ex: imagem ou digitalização sem OCR), registrar aviso
                if not texto_bruto:
                    logger.warning(f"Nenhum texto extraído de '{nome_arquivo}' na página {pagina_numero}.")
                    texto_bruto = ""
                
                # Limpeza e normalização do texto
                texto_limpo = limpar_texto(texto_bruto)
                
                # Geração de metadados rígidos
                metadados = obter_metadados(nome_arquivo, pagina_numero)
                
                # Estrutura final do JSON conforme especificação técnica
                json_saida = {
                    "nome_arquivo": nome_arquivo,
                    "pagina": pagina_numero,
                    "texto": texto_limpo,
                    "metadata": metadados
                }
                
                # Nome do arquivo JSON de destino
                nome_json = sanitizar_nome_json(nome_arquivo, pagina_numero)
                caminho_json = caminho_destino / nome_json
                
                # Salvando o arquivo JSON
                with open(caminho_json, 'w', encoding='utf-8') as f:
                    json.dump(json_saida, f, ensure_ascii=False, indent=2)
                    
            except Exception as page_err:
                logger.error(
                    f"Erro ao processar página {pagina_numero} do arquivo '{nome_arquivo}': {page_err}",
                    exc_info=True
                )
                
        logger.info(f"Concluído com sucesso o processamento de: {nome_arquivo}\n")
        
    except Exception as err:
        logger.error(
            f"Erro crítico ao abrir ou processar o PDF '{nome_arquivo}': {err}",
            exc_info=True
        )


def main():
    """
    Função principal que orquestra o ETL:
    - Define os diretórios de origem (dados/raw/) e destino (staging/).
    - Varre o diretório em busca dos 6 PDFs esperados.
    - Cria o diretório staging se necessário.
    - Executa o pipeline para cada documento encontrado.
    """
    # Caminhos relativos a partir da raiz do projeto
    diretorio_origem = Path("dados/raw")
    diretorio_destino = Path("staging")
    
    logger.info("Iniciando pipeline de ETL (Passo 1)...")
    
    # Criar pasta staging caso não exista
    if not diretorio_destino.exists():
        logger.info(f"Criando diretório de destino: {diretorio_destino.resolve()}")
        diretorio_destino.mkdir(parents=True, exist_ok=True)
    
    # Validar se o diretório de dados existe
    if not diretorio_origem.exists() or not diretorio_origem.is_dir():
        logger.critical(f"Diretório de origem '{diretorio_origem.resolve()}' não encontrado!")
        return

    # Buscar todos os arquivos PDF no diretório de origem
    arquivos_pdf = list(diretorio_origem.glob("*.pdf"))
    
    if not arquivos_pdf:
        logger.warning(f"Nenhum arquivo PDF encontrado em '{diretorio_origem.resolve()}'")
        return
        
    logger.info(f"Encontrados {len(arquivos_pdf)} arquivos PDF para processar.")
    
    # Processar cada PDF encontrado
    for caminho_pdf in arquivos_pdf:
        processar_pdf(caminho_pdf, diretorio_destino)
        
    logger.info("Pipeline de ETL concluído.")


if __name__ == "__main__":
    main()
