# Manifesto People Analytics

Este documento serve como o "Cérebro" de contexto para o Engenheiro de Dados Arquitetural, contendo o estado atual, a arquitetura e as regras de negócio consolidadas do projeto de People Analytics.

## 1. Visão Geral e Arquitetura

O projeto adota uma arquitetura de aplicação web desacoplada (SPA - Single Page Application), onde o Backend serve APIs RESTful e o Frontend consome os dados para renderização dinâmica de painéis executivos.

*   **Stack Principal:** Backend em Python (Flask) e Frontend em Vanilla HTML/CSS/JS (com Select2 e DataTables).
*   **Rotas da API (`app_absenteismo.py`):**
    *   `/api/absenteismo/resumo`: Retorna os KPIs macro e top colaboradores.
    *   `/api/absenteismo/evolucao`: Retorna a evolução temporal (YoY, MoM, diária).
    *   `/api/absenteismo/auditoria`: Retorna os dados completos linha a linha para a tabela de detalhamento e as chaves de sincronização.
    *   `/api/absenteismo/sync`: Força um recarregamento (Cold Start) buscando os arquivos mais recentes no Google Drive.
*   **Sistema de Cache em Memória (Singleton):** Para garantir extrema performance e fluidez na experiência do executivo, o sistema utiliza um modelo de cache estrito. Uma variável global (`CACHE`) armazena todo o processamento de dados na memória RAM do servidor. No "Cold Start", o servidor lê as planilhas pesadas, aplica todas as agregações do Pandas e salva o payload final no `CACHE`. Qualquer requisição subsequente do frontend é respondida a partir da RAM, resultando em tempos de resposta de milissegundos (`[RAM CACHE]`).

## 2. Fluxo e Processamento de Dados

O processamento é estruturado no padrão ETL (Extract, Transform, Load), liderado por scripts Python especializados:

*   **Extração:** Os relatórios são gerados pelo sistema Senior e atualizados no Google Drive. O sistema busca os arquivos de forma dinâmica, fazendo o download de `downloaded_abs.xls` (Absenteísmo) e `downloaded_headcount.xlsx` (Headcount).
*   **Transformação (`data_processor.py`):**
    *   Utiliza bibliotecas `pandas`, `openpyxl` e `xlrd` (com patches para contornar problemas de tipagem nativos das exportações do Senior).
    *   Realiza a limpeza de nomes, sanitização de chaves primárias (Matrícula) e o parsing complexo das strings de hora (ex: "8h48m") para decimais (ex: 8.8).
    *   Faz o *Merge* (`Left Join`) da base de Absenteísmo com a base de Headcount para trazer a coluna "Área", tratando inconsistências e dados nulos.
*   **Carga:** Todo o DataFrame processado é convertido para dicionários e empacotado em um payload JSON unificado entregue à interface via endpoints do Flask.
*   **Scripts Auxiliares:** `read_cols.py`, `parse_abs.py`, `calc_hours.py`, e `explore.py` serviram como ambiente de experimentação (discovery) para validar tipagens e encontrar padrões nos relatórios brutos.

## 3. Regras de Negócio (Business Logic)

As regras de Recursos Humanos (RH) já mapeadas e codificadas garantem que os dados brutos se tornem indicadores confiáveis:

*   **Faltas Integrais (Backend Logic):** O sistema isola automaticamente faltas parciais de faltas do dia inteiro. Se o código da situação for `"015"` e as horas decodificadas forem `>= 8.5` (englobando as clássicas 8h48m), a ocorrência é virtualmente renomeada para `"Faltas integrais"`, permitindo filtragem limpa e precisa pela gestão.
*   **Métricas de Frequência e Absenteísmo:**
    *   **Dias Devidos:** Baseado na conversão padronizada de 8h48m por dia.
    *   **MoM (Month-over-Month):** Cálculo de variação percentual do total de horas de ausência do mês atual versus o mês imediatamente anterior.
    *   **Proporção Seg/Sex:** Mapeamento do percentual de horas de absenteísmo que ocorrem especificamente às Segundas e Sextas-feiras, evidenciando o padrão de "prolongamento de fim de semana".
*   **População "Core" (4 a 84 meses) e Retenção:** Regra conceitual de negócio estabelecida como diretriz arquitetural para o cruzamento de Headcount e Turnover. O objetivo é isolar e acompanhar a saúde analítica do funcionário maduro e estável (acima da experiência e abaixo do risco de obsolescência/aposentadoria).

## 4. Estrutura de Diretórios (Disco D:)

A árvore atual do projeto no diretório principal `D:\Projeto geral\People analytics - GP\module_absenteismo_turnover`:

```text
module_absenteismo_turnover/
├── .agents/                      # Diretório de customização de IA (Regras e Manifesto local)
├── ui_references/                # Repositório oficial de imagens e modelos visuais aprovados para o dashboard
├── __pycache__/                  # Cache compilado do Python
├── app_absenteismo.py            # Entry point do Servidor Flask e definição de Rotas
├── dashboard_absenteismo.html    # Interface Front-End (Dashboard Executivo)
├── data_processor.py             # Core ETL, Regras de Negócio e Cálculos
├── downloaded_abs.xls            # Cache local da base de Absenteísmo (Drive)
├── downloaded_headcount.xlsx     # Cache local da base de Headcount (Drive)
├── sync_info.json                # Rastreabilidade das versões de arquivos sincronizados
└── (Scripts de Discovery):
    ├── calc_hours.py
    ├── data_discovery.py
    ├── explore.py
    ├── parse_abs.py
    ├── read_cols.py
    ├── test_drive_daniel.py
    └── test_read.py
```

## 5. Segurança e Servidores MCP

*   **Premissa Read-Only:** A arquitetura garante que não há conexão direta com permissão de escrita ao banco de dados do sistema Senior, isolando o ambiente analítico de transações de produção.
*   **Integração por Arquivos (Air Gap Lógico):** Os dados são lidos a partir de relatórios estáticos espelhados no Google Drive (baixados sob demanda), garantindo que quedas na API ou corrupções no Analytics nunca impactem o ERP de RH primário.

## 6. Status do Front-End (UX/UI)

O Frontend (HTML/JS/CSS) atingiu o padrão Executivo Minimalista e Premium, caracterizado por:
*   **Modo Claro/Escuro:** Adaptabilidade total de tema via CSS puro (`var(--bg-color)` e afins).
*   **UX Clean do Header:** A rastreabilidade técnica dos arquivos (datas de extração) foi movida para o cabeçalho superior, liberando espaço nas laterais.
*   **Resumo de Filtros Ativos:** Quando a torre de filtros lateral é ocultada para maximizar a área da tabela/gráficos, o sistema injeta dinamicamente "Badges" visuais no cabeçalho da tabela contendo o sumário exato dos filtros ativados.
*   **Agilidade e Interatividade:** O sistema Select2 foi configurado com `closeOnSelect: true` para que os menus suspensos se recolham instantaneamente após o clique.
*   **Indicadores de Top Level:** Os KPIs (Total de Horas, Dias Devidos, Registros) são atualizados em milissegundos reativamente quando o usuário filtra a tabela.
