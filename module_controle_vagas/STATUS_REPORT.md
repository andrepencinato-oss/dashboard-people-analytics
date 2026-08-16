# STATUS REPORT TÉCNICO E EXECUTIVO — MÓDULO QUADRO DE VAGAS & AUDITORIA DE LOTAÇÃO

**Data de Referência:** Julho/2026  
**Módulo / Terreno de Jogo:** `D:\Projeto geral\People analytics - GP\module_controle_vagas`  
**Objetivo:** Raio-X completo da arquitetura técnico-funcional, integrações com Google Drive (Shared Core) e consolidação das regras de negócio e matemáticas da Auditoria de Lotação.

---

## 1. RESUMO EXECUTIVO

O módulo **Quadro de Vagas & Auditoria de Lotação** opera como uma **Single Page Application (SPA)** integrada a um back-end Python/Flask. A ferramenta unifica duas frentes críticas da gestão de pessoas da indústria:

1. **Cadastro e Monitoramento de Vagas:** Controle em tempo real do SLA de recrutamento, substituições por Centro de Custo, requisições abertas, em processo e finalizadas.
2. **Auditoria de Lotação (Headcount & Ocupação de Vagas):** Cruzamento analítico da folha de pagamento (Headcount Contábil) contra movimentações em aberto, afastamentos de risco, avisos prévios, rescisões pendentes e exceções trabalhistas (Aposentadorias por Invalidez e Reclusão).

A solução elimina dependências manuais de download de planilhas ao consumir automaticamente os relatórios em CSV direto do Google Drive através de um **Shared Core** centralizado de credenciais, garantindo governança, segurança de tokens e resiliência a falhas de codificação ou rede.

---

## 2. ARQUITETURA FRONT/BACK & SINGLE PAGE APPLICATION (SPA)

### 2.1 Configuração do Servidor Flask (`app.py`)
O servidor de aplicação é executado em Python (Flask 3.x) configurado com recarregamento dinâmico de templates (`TEMPLATES_AUTO_RELOAD = True`) no endereço `http://127.0.0.1:5000`. Ele atua primariamente como uma API RESTful de serviços de dados e orquestrador de arquivos locais/em nuvem:

```
+-----------------------------------------------------------------------------------+
|                            CAMADA BACK-END (app.py)                               |
+------------------------------------+----------------------------------------------+
| Rota / Endpoint                    | Função Principal                             |
+------------------------------------+----------------------------------------------+
| GET  /                             | Renderiza a estrutura da SPA (index.html)    |
| GET/POST /api/sync                 | Força sincronização manual com Google Drive  |
| GET  /api/dados_headcount          | Parseia o CSV ativo de Headcount para JSON   |
| GET  /api/dados_afastamento        | Parseia o CSV de Afastamentos para JSON      |
| GET  /api/dados_aviso_previo       | Parseia o CSV de Aviso Prévio para JSON      |
| GET  /api/dados_analytics          | Agrega HC, Afastamentos (Atual/Old) e Aviso  |
| GET/POST/PUT /api/dados_vagas      | Lê e persite dados locais em data/vagas.json |
+------------------------------------+----------------------------------------------+
```

#### Características Técnicas do Servidor:
- **Resiliência de Encoding (`read_local_file_by_pattern`):** Os arquivos exportados de sistemas de folha de pagamento frequentemente apresentam codificações mistas. O servidor testa sequencialmente as codificações `utf-8-sig`, `utf-8`, `latin-1` e `cp1252`.
- **Priorização de Bases Recentes:** Na busca por padrões de arquivo (`*headcount*`, `*afastam*`, `*aviso*`), o sistema prioriza arquivos que contenham o termo `'atual'` no nome de arquivo e, em critério de desempate, ordena por timestamp decrescente de modificação do sistema de arquivos (`-os.path.getmtime(x)`).
- **Sincronização no Cold Start:** No bloco inicializador (`if __name__ == '__main__':`), o servidor executa de forma silenciosa a função `sync_drive_to_local_data()` antes de abrir o listener HTTP, garantindo que o diretório `data/` esteja populado no momento da primeira requisição.

---

### 2.2 Dinâmica da Interface SPA (`templates/index.html`)
A interface foi projetada em **HTML5 / Vanilla JavaScript** de alta performance com design system baseado no **Google Material 3 / Tailwind CSS** e iconografia **Phosphor Icons / Material Symbols**, sem necessidade de *reload* do navegador.

#### Mecanismo de Transição de Módulos (`switchSPATab`)
A aplicação é conteinerizada dentro do invólucro `.spa-container`, dividindo-se em duas seções independentes no DOM:
- `<section id="sec-vagas">`: Painel de Recrutamento & Vagas.
- `<section id="sec-auditoria">`: Painel Analítico e Auditoria de Lotação.

A transição entre as duas visões é coordenada pela função `switchSPATab(tab)`:
1. **Ativação da Aba de Vagas (`tab === 'vagas'`):**
   - Altera `sec-vagas.style.display = 'block'` e oculta `sec-auditoria.style.display = 'none'`.
   - Modifica os estados das classes CSS na barra de navegação superior (`.spa-nav-btn.active` vs `.spa-nav-btn.inactive`).
   - Reexecuta `updateSetorFilter()` e `applyFilters()` para garantir que o painel de vagas reflita o Centro de Custo em foco.
2. **Ativação da Aba de Auditoria (`tab === 'auditoria'`):**
   - Altera `sec-auditoria.style.display = 'block'` e oculta `sec-vagas.style.display = 'none'`.
   - **Lazy Loading (Carregamento Sob Demanda):** Utiliza a flag booleana `_auditoriaLoaded`. Na primeira transição para a aba de auditoria (`if (!_auditoriaLoaded)`), o front-end dispara a requisição assíncrona para `/api/dados_analytics`, otimizando o tempo de carregamento inicial da página.
   - Em acessos subsequentes na mesma sessão, reexecuta apenas o renderizador e filtros na memória (`applyIndustryCCFilter()`), preservando alta responsividade.

---

## 3. PIPELINE DE DADOS & INTEGRAÇÃO GOOGLE DRIVE (SHARED CORE)

### 3.1 Operação via Shared Core (`core/`)
O módulo de vagas segue estritamente a diretriz arquitetural de isolamento de credenciais na camada **Shared Core**, localizada no diretório pai (`../core/`):
- `token.json`: Armazena o token OAuth 2.0 de acesso e atualização (Refresh Token) do usuário autorizado.
- `credentials.json`: Segredos do cliente Google Cloud Platform (Client ID / Client Secret) para a API do Google Drive.

```
       [ Google Drive Cloud ]
                 │
                 ▼ (MediaIoBaseDownload / OAuth 2.0)
     [ ../core/token.json & credentials.json ]  <-- (Shared Core Credentials)
                 │
                 ▼
     [ app.py (Flask Server) ]
                 │
                 ▼ (Sincronização / Silenciosa)
  +--------------+--------------+
  │             data/           │
  ├─ *headcount*.csv            │
  ├─ *afastam*atual*.csv        │
  ├─ *afastam*old*.csv          │
  ├─ *aviso*.csv                │
  └─ vagas.json                 │
  +-----------------------------+
```

#### Regras de Atualização do Token (`get_drive_service`):
1. Verifica se `token.json` existe em `CORE_DIR`.
2. Caso o token esteja expirado, aciona automaticamente `creds.refresh(Request())` utilizando o `refresh_token` sem abrir janelas de login interativas.
3. Constrói o serviço autenticado da API v3 do Google Drive (`build('drive', 'v3', credentials=creds)`).

### 3.2 Consumo das Bases (CSVs)
A consulta ao Google Drive aponta para a pasta específica de relatórios de RH (`DRIVE_FOLDER_ID = '1UO_L8EkWn5dDyh59pYVMxo22FYKDf92V'`). Todos os arquivos que não foram enviados para a lixeira são baixados na pasta local `data/`.

| Base de Dados | Padrão no Código | Descrição & Função Analítica |
| :--- | :--- | :--- |
| **Headcount Geral** | `*headcount*` | Base primária contendo todos os cadastros ativos na folha (Matrícula/CAD, Nome, Admissão, Cargo, Salário e Centro de Custo). |
| **Afastamentos (Atual)** | `*afastam*` + `atual` | Relatório diário/corrente com registros de afastamentos temporários, licenças médicas, maternidade ou INSS. |
| **Afastamentos (Old)** | `*afastam*` + `old` | Base de retaguarda contendo o histórico recente de afastamentos, utilizada como *fallback* para colaboradores que não possuem lançamento no CSV atual (`afastamentoOld`). |
| **Aviso Prévio / Desligamento** | `*aviso*` | Base de colaboradores em transição de saída (aviso prévio trabalhado, indenizado ou rescisão em andamento). |
| **Vagas Customizadas** | `vagas.json` | Arquivo gerado localmente pelas edições interativas de requisição, substituição e status na aba de Cadastro de Vagas. |

---

## 4. REGRAS DE NEGÓCIO DA AUDITORIA DE LOTAÇÃO

A Auditoria de Lotação opera como um motor analítico executado na função JavaScript `parseAndConsolidateData()`. Para evitar divergências matemáticas ou contagem dupla (*double counting*), o código estabelece regras estritas de filtragem, prioridade de categoria e saneamento de folha.

### 4.1 Saneamento de Registros Contábeis / Relatórios
Ao parsear o arquivo de Headcount, o sistema descarta automaticamente linhas de cabeçalho, rodapé ou registros sintéticos do sistema de folha:
- `cad === '0001'`
- `nome === '-'`
- `nome.includes('MOVEIS')`
- `cargo.includes('Pág')`

### 4.2 Exclusão de Férias e Faltas (Motivos Ignorados)
Para isolar apenas os afastamentos de risco operacional (medicina do trabalho, auxílio-doença, etc.), a função `isMotivoIgnorado(motivo)` é aplicada a cada registro. Colaboradores com os seguintes motivos são **totalmente ignorados como afastados**, permanecendo classificados na força de trabalho **Ativa**:
- `'falta'` / `'faltas'`
- `'feria'` / `'ferias'` / `'férias'`
- `'marcações inválidas'` / `'marcacoes invalidas'`

### 4.3 Regra de Afastamentos de Longo Prazo (> 30 Dias)
A auditoria foca em afastamentos que representem vacância real de posto na indústria. A função `isPrevisaoRetornoValida(dtStr)` avalia a data de término prevista no relatório (`dtTermino` ou `lastDate`):
- Se a data de retorno prevista for **indefinida** (`""`, `"-"`, `"—"`), o afastamento é considerado **Válido**.
- Se a data estiver preenchida, o sistema calcula a diferença em dias contra a data atual (`Math.ceil(diffTime / (1000 * 60 * 60 * 24))`).
- O afastamento só entra no indicador de risco se `diffDays > 30` (retornos em menos de 30 dias não reduzem o headcount ativo da auditoria).

### 4.4 Isolamento de Exceções Trabalhistas
Determinadas situações excepcionais de folha possuem tratamento exclusivo para não inflacionar distorcidamente o indicador de absenteísmo médico ou turnover:
1. **Aposentadoria por Invalidez (`KNOWN_APOSENTADOS`):**  
   Colaboradores cadastrados na constante (`1135`, `510`, `4926`) ou com motivo contendo `'aposent'`. São classificados na categoria `aposentados` com badge roxo (`Aposentadoria por Invalidez`).
2. **Licença Reclusão (`KNOWN_RECLUSOS`):**  
   Colaborador com CAD `3338` (*Alessandro Renato Ocanha dos Santos*) ou motivo contendo `'reclus'` / `'pris'`. Classificado em `reclusos` com badge cinza (`Licença Reclusão`).
3. **Rescisões Pendentes no ERP / Pedidos de Demissão (`KNOWN_AVISO_PREVIO_DETAILS`):**  
   Colaboradores que já pediram demissão (ex: CADs `4970`, `4955`, `4993` com data limite até 22/07/2026), cujas rescisões ainda estão pendentes de processamento contábil. São forçados para a categoria de `aviso` com o tipo `'Pedido de Demissão (Antecipação Exp.)'`.
4. **Previsão de Demissões Gestão (`KNOWN_PREVISAO_DEMISSAO`):**  
   Lista de colaboradores sinalizados pela gestão para substituição/corte futuro.

### 4.5 Classificação Exclusiva sem Duplicidade (`primaryCategory`)
Cada colaborador é atribuído a **uma única categoria primária** na seguinte ordem estrita de precedência:

```
[ Colaborador no Headcount ]
            │
            ├─► 1. Está em KNOWN_PREVISAO_DEMISSAO? ───────► 'previsao-demissao'
            ├─► 2. É Aposentado (Invalidez)? ──────────────► 'aposentados'
            ├─► 3. É Recluso / Licença Reclusão? ──────────► 'reclusos'
            ├─► 4. Está em Aviso Prévio ou Rescisão? ──────► 'aviso'
            ├─► 5. Afastamento Válido (>30d / sem Férias)? ► 'afastados'
            └─► 6. Caso Nenhuma das Anteriores ────────────► 'ativo' (Força de Trabalho Efetiva)
```

### 4.6 A Matemática Exata da Auditoria (Headcount Líquido)
A consolidação de indicadores exibida no topo do painel e calculada pela rotina `updateCalculatedHeadAtivo()` obedece à seguinte equação contábil-operacional:

$$\text{Headcount Líquido (Ativo Real)} = \max\Big(0,\; \text{HeadTotal} - \text{TotalAfastados} - \text{TotalAvisoPrévio} - \text{PrevisãoDemissão}\Big)$$

#### Memória de Cálculo:
- **`HeadTotal`**: Soma de colaboradores que superaram a validação de saneamento de folha.
- **`TotalAfastados`**: Exclui **Aposentados por Invalidez** e **Reclusos** (que não entram nessa subtração por estarem isolados fora da base operacional) e exclui motivos de **Férias/Faltas** e afastamentos com prazo de retorno **$\le 30$ dias**.
- **`TotalAvisoPrévio`**: Soma de colaboradores em processo formal de aviso prévio mais as rescisões pendentes conhecidas.
- **`PrevisãoDemissão`**: Total de colaboradores marcados para substituição planejada (`KNOWN_PREVISAO_DEMISSAO.length`).

---

## 5. RESUMO DE CONFORMIDADE TÉCNICA E SEGURANÇA

1. **Preservação de Escopo:** Todos os scripts de parsing, regras de cálculo e arquivos persistidos estão confinados dentro de `D:\Projeto geral\People analytics - GP\module_controle_vagas`.
2. **Sem Intervenção Manual no OAuth:** O token é gerido de forma autônoma pela rotina em `app.py` consultando o `Shared Core` (`../core/token.json`).
3. **Persistência de Visão por Setor:** O filtro de setores da indústria é gravado no `localStorage` sob a chave `'people_analytics_industry_ccs'`, garantindo que a sessão do analista de RH preserve o contexto entre recarregamentos e alternâncias de abas.
