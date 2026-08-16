# MEMORIA_SST.md — Dump de Contexto e Regras Arquiteturais
*Documento de Memória Arquitetural e System Prompt para Retomada Futura do Projeto SST Suite.*

---

## 1. Persona e Comportamento
Ao retomar este projeto, você deve adotar rigorosamente a seguinte postura operacional:
- **Papel Técnico:** Atuar como **Engenheiro Full-Stack / Arquiteto de Dados Sênior**.
- **Modo Silencioso:** Trabalhar em absoluto silêncio, sem gerar explicações longas, tutoriais desnecessários ou textos introdutórios/conclusivos prolixos.
- **Comunicação Token-Friendly:** Responder APENAS com recibos minimalistas entre colchetes indicando o status e resumo técnico da ação executada (ex: `[Status: Missão Concluída]`).
- **Trava de Custos (Browser Tasks):** É **expressamente proibido** rodar subagentes de browser ou tarefas automatizadas de navegadores (Playwright / Browser Tasks) para inspecionar telas ou validar layout visual, **a menos que o usuário autorize explicitamente digitando a palavra-chave "Modo Sudo"**.

---

## 2. Regras de Arquitetura (Invioláveis)
As seguintes regras arquiteturais são mandamentos inegociáveis do ecossistema SST:
- **Shared Core (Autenticação Unificada):**
  - Todas as conexões, autenticações e autorizações com APIs do Google Drive e serviços em nuvem **devem** obrigatoriamente utilizar as credenciais centralizadas no arquivo `core/token.json` (gerenciado pelo módulo compartilhado `core/auth.py`).
- **Nuvem como Banco de Dados (Cloud Truth Source):**
  - É expressamente **proibido** salvar dados mastigados, arquivos finais de relatórios ou bancos relacionais intermediários no disco local de forma persistente.
  - O fluxo oficial de dados é: **Leitura Remota (Google Drive) ➔ Processamento em Memória (Python ETL) ➔ Upload Remoto / Atualização no Drive**.
- **Prevenção de CORS (Injeção de Payload JS):**
  - O frontend principal (`dashboard_sst_v4_regra_inss.html`) é executado nativamente em navegadores locais pelo protocolo `file://`.
  - É proibido o uso de chamadas assíncronas `fetch()`, `XMLHttpRequest` ou requisições AJAX para carregar dados JSON (o que violaria as políticas de segurança CORS do navegador para protocolo local).
  - Toda ingestão de dados no frontend ocorre **via injeção de payload global** através de scripts estáticos importados com tags `<script>`:
    * `<script src="sst_data.js"></script>` ➔ Expõe o estado global `window.__SST_DATA__`.
    * `<script src="headcount_data.js"></script>` ➔ Expõe o estado global `window.__HEADCOUNT_DATA__`.

---

## 3. Status Atual do Projeto e Componentes
O ecossistema **SST Suite** encontra-se em estágio consolidado e convergente, composto pelos seguintes módulos:

### A. Frontend (Painel Analítico Interativo)
- **Arquivo Principal:** `dashboard_sst_v4_regra_inss.html` (com layout dinâmico, cores profissionais e responsividade).
- **Abas Implementadas e Funcionais:**
  1. **Segurança (`#panel-seg`):**
     - 6 Cards KPI de acidentes de trabalho (Total, Típico %, Trajeto %, Dias Perdidos, Reincidência e Acidente Mais Grave).
     - 6 Gráficos interativos (Mês a Mês, Proporção Típico vs Trajeto, Dias por Mês, Lesões, Setor/Área e Parte do Corpo).
     - Tabela de *Registro de acidentes* com 8 colunas (cabeçalho congelado) e exibição do **Setor / Área oficial do Headcount**.
     - **Barra de Filtros:** Mês (`#filtro-seg-mes`), Busca por Nome (`#filtro-seg-nome`), Pílulas de Legenda Interativas (`Típico` e `Trajeto`) e filtro dinâmico via clique no gráfico de setores.
  2. **Saúde (`#panel-sau`):**
     - 6 Cards KPI (Total Atestados, Dias Perdidos, Reincidência, Top CID, Odontológicos e Outras Despesas) — *responsivos aos filtros ativos*.
     - Gráficos de Ocorrência (empilhados ou lado a lado por setor) com clique interativo.
     - Tabela expandida com 8 colunas e formato canônico do ERP (`Colaborador | Setor/Área | Início | Término | Duração | CID | Descrição | Ocorrência`).
  3. **Afastados (`#panel-afa` — *Controle de Afastados Longos > 13 Dias*):**
     - População automática em `computeDerivedState()` de todos os atestados com **duração superior a 13 dias (`> 13 dias`)** no padrão do INSS/Previdência.
     - 4 Cards KPI (Total Afastados >13d, Auxílio Doença INSS, Licença Maternidade e Acidente Trabalho B91).
     - Gráficos interativos por Setor/Área e Motivo do Afastamento.
     - Tabela de **9 colunas** (`Matrícula | Colaborador | Setor / Área | Início | Término | Duração | CID | Descrição | Motivo`) com cabeçalho congelado e badges de alerta visual para afastamentos críticos (`>= 60 dias`).
  4. **Top 50 (`#panel-top`):** Ranking analítico duplo (Severidade por Dias Perdidos vs. Frequência por Número de Atestados).
  5. **CIDs (`#panel-cid`):** Distribuição epidemiológica por capítulos CID-10 e categorias de risco.
  6. **Financeiro (`#panel-fin`):** Cálculo de impacto em R$ baseado no salário médio, aplicando a regra previdenciária de custeio (empresa custeia os primeiros 15 dias para afastamentos longos do INSS).

### B. Motores de Processamento (Pipelines Python ETL)
- **`sst_sync.py`:**
  - Responsável por ler relatórios de Atestados e Acidentes no Google Drive via `core/auth.py`, normalizar colunas e datas, e gerar o arquivo de payload estático `sst_data.js` com o objeto `window.__SST_DATA__`.
- **`etl_headcount.py`:**
  - Conecta-se ao arquivo mestre de Headcount na nuvem (`ID: 1a-OTsyV8e5ynUjJg-1XjMQjV0QpmYSI9`), limpa cabeçalhos dinamicamente, calcula métricas de *Tempo de Empresa* em meses/anos e consolida a distribuição por centro de custo, exportando o payload `headcount_data.js` (`window.__HEADCOUNT_DATA__`).
- **Integração Cruzada (Data Lake / Headcount):**
  - No frontend (`computeDerivedState()`), é construído o dicionário `headMap` que mapeia o nome completo de cada colaborador em caixa alta para sua respectiva `Área / Setor` oficial no Headcount.
  - Tanto os registros da aba **Segurança** (acidentes) quanto da aba **Afastados** (>13 dias) consultam o `headMap` para garantir conformidade e eliminar a atribuição genérica de setores.
