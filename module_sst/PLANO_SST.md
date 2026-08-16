# PLANO DE EXECUÇÃO: AUTOMAÇÃO DO DASHBOARD SST

Este documento define a estratégia, arquitetura e o mapeamento de dados (De/Para) necessários para substituir o fluxo manual de upload de PDFs/planilhas do Dashboard SST por um fluxo 100% autônomo, consumindo os relatórios gerados via sistema e salvos no Google Drive.

---

## 1. Mapeamento de Dados (De/Para)

Os relatórios extraídos do sistema (CSV/Excel) possuem linhas de cabeçalho "sujas" (título da empresa, datas de filtro) nas primeiras linhas. A extração vai ignorar essas linhas (skiprows) e processar os cabeçalhos reais.

### A. Atestados (`Atestados.CSV`)
- **Origem (CSV):** Relatório de Atestados de Saúde (ignorar linhas 1-3)
- **Campos Esperados no CSV:** Matrícula/Nome (Colaborador), Setor, CID, Dias de Atestado.
- **Destino (HTML):** Array interno de Atestados.
- **Uso no HTML:** Gráficos de Saúde (Top CIDs, Atestados por Setor) e listagens de custo/saúde (Cálculo INSS se > 15 dias).

### B. Afastados (`Afastados .CSV`)
- **Origem (CSV):** Histórico de Afastamentos (ignorar linhas 1-3)
- **Campos Esperados no CSV:** Matrícula, Colaborador, Setor, Motivo (B31, B91, etc).
- **Destino (HTML):** Array interno de Afastados.
- **Uso no HTML:** Cards de "Afastados Previdenciários" e métricas de Taxa de Retorno / Absenteísmo.

### C. Acidentes (`Relatório de acidente.CSV`)
- **Origem (CSV):** Relação de Acidentes por Espécie (ignorar linhas 1-3)
- **Campos Esperados no CSV:** Data do Acidente, Nome, Setor, Tipo (Típico/Trajeto), Causa, Parte do Corpo, Lesão.
- **Destino (HTML):** Array interno de Acidentes.
- **Uso no HTML:** Matriz de Risco, Acidentes por Parte do Corpo, Pirâmide de Bird, Evolução Mensal.

### D. Métricas Agregadas (`Dias Perdidos.xlsx` e `FREQUÊNCIA DE ACIDENTES.xlsx`)
- **Origem (XLSX):** Tabela resumo contendo `MÊS` e `QUANTIDADES`.
- **Destino (HTML):** Gráficos de barra/linha de métricas agregadas (Dias Perdidos Anuais, Frequência Mensal de Acidentes).

---

## 2. Arquitetura Sugerida

A solução será dividida em duas camadas para manter a performance do dashboard no navegador do usuário e garantir a autonomia e distribuição dos dados (100% Nuvem).

### A. Backend Autônomo (Python / Data Pipeline 100% Cloud)
1. **Script de Sincronização (`sst_sync.py`):** 
   - Um script Python que utilizará a API do Google Drive (através das credenciais `core/token.json`).
   - Fará o download silencioso e em memória dos 5 arquivos na pasta alvo (`1JkjIm64E-uXmyzMoRmKMPXtXh3Btx84l` e subpastas).
   - Utilizará `pandas` para ler os arquivos, aplicando `skiprows` adequadamente para pular os cabeçalhos do ERP.
   - Fará a sanitização, padronização (tratamento de nulos, datas, etc.) e o agrupamento/JOIN tudo **na memória**.
   - **Upload Direto:** O arquivo consolidado (`sst_data.json`) não será salvo localmente. Ele será enviado (upload) diretamente para a pasta remota no Google Drive: `1MMZ363U1ErFlZR-xGI5uDRgzSjUrWM1E`.

### B. Frontend (HTML/JS)
1. **Modificação do `dashboard_sst_v4_regra_inss.html`:**
   - Remoção/Ocultação dos botões de "Upload Manual".
   - Substituição da lógica de parsing de planilhas por uma lógica de requisição (`fetch`) que consumirá o arquivo `sst_data.json` servido pelo backend a partir do Google Drive.
   - O objeto JSON recebido já terá a estrutura perfeita para popular os gráficos e tabelas instantaneamente.

---

## 3. Passo a Passo de Execução (Roadmap de Migração)

**ETAPA 1: O Script de Extração & Transformação (ETL)**
1. Criar o script de sincronização no `module_sst`.
2. Mapear o `skiprows` exato e o nome das colunas reais para cada um dos 5 relatórios do Drive.
3. Testar a transformação (DataFrame -> JSON) validando a conversão de caracteres e integridade de dados (validação de CIDs, Setores, etc).

**ETAPA 2: A Injeção no Front-End**
1. Clonar/versionar o `dashboard_sst_v4_regra_inss.html` para não quebrar a versão atual até a migração estar homologada.
2. Inserir um script de `fetch` no HTML para consumir o novo `sst_data.json`.
3. Ajustar as funções de `rebuildSeguranca()`, `rebuildSaude()` e `rebuildFinanceiro()` para mapearem os nós do JSON, desativando a antiga leitura via array global alimentada por planilhas.

**ETAPA 3: Teste e Descomissionamento Manual**
1. Atualizar o dashboard localmente para validar a transição dos gráficos.
2. Integrar a chamada do `sst_sync.py` ao fluxo de atualização automática (podendo usar `schedule`, cronjob ou ser chamado na abertura do App).
3. Homologação final e remoção da interface legada de upload.
