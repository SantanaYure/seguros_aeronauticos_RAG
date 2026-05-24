# Walkthrough - Passo 2A: Schema Supabase para Gemini

## Passo 2A: Schema Supabase para Gemini

### Visão Geral do Modelo e Embedding
- **Integração com Gemini**: O projeto foi configurado para utilizar as APIs do Gemini, e não da OpenAI.
- **Modelo de Embedding**: O modelo planejado para a vetorização é o `models/text-embedding-004`.
- **Dimensão de Embedding**: O modelo `models/text-embedding-004` gera vetores de **768 dimensões**. Por esta razão, a coluna `embedding` na tabela do banco de dados usa a definição `vector(768)`.

### Banco de Dados (Supabase)
- **Tabela Oficial**: A tabela oficial para armazenar os fragmentos e vetores do RAG é `public.document_chunks`.
- **Tabela Antiga**: A tabela antiga `public.documentos` não deve ser utilizada ou modificada nesta etapa.
- **Script do Schema**: O arquivo [supabase_schema.sql](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/supabase_schema.sql) foi criado e deve ser executado no SQL Editor do Supabase para inicializar a extensão vetorial, criar a tabela `document_chunks`, criar os índices de busca e registrar a função RPC `match_document_chunks`.
- **Verificação e Diagnóstico**: O arquivo [supabase_diagnostics.sql](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/supabase_diagnostics.sql) foi criado com queries SQL prontas para validar se a estrutura da tabela, índices e a função RPC foram criados perfeitamente no Supabase.

### Dependências e Instalação
- As dependências necessárias para a vetorização com Gemini e interação com o Supabase foram mapeadas e adicionadas ao arquivo [requirements.txt](file:///d:/OneDrive/%C3%81rea%20de%20Trabalho/Projetos/seguros_aeronauticos_RAG/requirements.txt).
- **Ajuste Técnico**: O pacote `supabase` foi pinado como `supabase<2.26.0` para evitar a dependência transitiva do `pyiceberg` (introduzida na versão 2.26.0 pelo `storage3`). Sob o Python 3.14 no Windows, o `pyiceberg` não possui wheels pré-compilados e falharia na compilação do compilador C. Pinando para `<2.26.0` removemos completamente o `pyiceberg` da árvore de dependências.
- O comando sugerido para instalar todas as dependências é:
  ```bash
  pip install -r requirements.txt
  ```


### Próximos Passos
- Na próxima etapa, implementaremos o script `create_embeddings.py` que lerá os arquivos em `staging/`, fragmentará os textos de forma semântica (conforme as estratégias A e B descritas na especificação), gerará os embeddings e fará a carga no Supabase. O script contará com um modo `DRY_RUN` para validação local antes da carga real no banco de dados.
