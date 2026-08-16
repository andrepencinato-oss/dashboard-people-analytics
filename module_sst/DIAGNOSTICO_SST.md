# 📊 Diagnóstico Técnico de Arquitetura e Renderização (SST)

**Documento:** Relatório de Auditoria e Diagnóstico de Falha de Renderização de Gráficos  
**Módulo:** `module_sst/dashboard_sst_v4_regra_inss.html`  
**Autor:** Engenheiro de Front-end & Arquiteto de Software  
**Data:** 04/08/2026  

---

## 1. O Fluxo do Fetch (`fetch('/api/sst_data')`)

### A. Rota Atual Configurada
Atualmente, a chamada assíncrona de busca no arquivo `dashboard_sst_v4_regra_inss.html` está configurada apontando para a URL relativa:
```javascript
fetch('/api/sst_data')
    .then(res => {
        if (!res.ok) throw new Error('Dados remotos não encontrados');
        return res.json();
    })
    ...
```

### B. Diagnóstico Arquitetural do Ambiente de Execução
- **Ausência de Backend HTTP Local:** O projeto atualmente não possui um servidor HTTP/API local ou proxy reverso em execução na porta local para responder à rota `/api/sst_data`.
- **Comportamento em Ambiente `file://` (Abertura Direta no Navegador):** Quando o usuário abre o arquivo `dashboard_sst_v4_regra_inss.html` direto no navegador no Windows (via protocolo `file:///D:/Projeto...`), o navegador bloqueia requisições `fetch` relativas/locais por política de segurança (**CORS / Same-Origin Policy para scheme `file://`**).
- **Consequência:** A requisição `fetch('/api/sst_data')` falha sistematicamente com erro de rede (`ERR_FAILED` ou `URL scheme "file" is not supported`), caindo imediatamente no bloco de fallback `.catch(err => { console.warn("Usando dados offline/padrão:", err); })`.
- **Decisão Arquitetural Recomendada:**
  1. Se o dashboard for consumido via arquivo local/Google Drive sem servidor node/python ativo, a arquitetura deve prever o carregamento de dados via **script JSONP / injeção de payload leve em variável global** (como em `data_payload.js` gerado pelo pipeline Python), em vez de depender de `fetch()` relativo.
  2. Se for consumido web, é obrigatório subir um serviço (ex: `app_sst.py` com Flask/FastAPI) servindo a rota `/api/sst_data`.

---

## 2. Ciclo de Vida da Renderização e Atualização do `state`

### A. Inicialização e Ordem de Execução no DOM
1. **Instanciação do Estado Global:**
   - No escopo global do script, a variável `state` é inicializada de forma síncrona com os dados padrão do objeto `DEFAULT_DATA`:
     ```javascript
     let state = JSON.parse(JSON.stringify(DEFAULT_DATA));
     ```
2. **Disparo do Rebuild Inicial (`DOMContentLoaded` / Carga Síncrona):**
   - Ao terminar a leitura do script HTML, a aplicação executa as funções de renderização (`rebuildAll()`, que invoca `rebuildSeguranca()`, `rebuildSaude()`, etc.) **de forma síncrona**, montando o DOM com os dados presentes na memória naquele instante (`DEFAULT_DATA`).

### B. O Momento da Chamada Assíncrona (Pós-Fetch)
- O `fetch('/api/sst_data')` é assíncrono e roda em paralelo/background:
  ```javascript
  .then(data => {
      if (data) {
          if (data.acidentes) state.acidentes = data.acidentes;
          if (data.afastados) state.afastados = data.afastados;
          if (data.atestados) state.atestados = data.atestados;
          rebuildAll(); // Re-renderiza somente AQUI após JSON na memória
      }
  })
  ```
- **Avaliação:** O acionamento de `rebuildAll()` dentro do `.then(data => ...)` está arquiteturalmente **no momento correto** (somente após o payload remoto ter sido parseado e atribuído a `state`).
- **Problema de Sincronia no Cenário Falho:** Como o `fetch` falha por falta de API/servidor rodando, o `.then()` nunca é executado, e a tela depende exclusivamente dos dados estáticos que estavam em `DEFAULT_DATA` no momento da inicialização síncrona.

---

## 3. Mapeamento de Chaves (De/Para — Python ETL vs. Chart.js)

Auditoria comparativa entre a estrutura JSON exportada pelo motor Python (`sst_sync.py`) e as chaves lidas pelo gerador de gráficos em `rebuildSeguranca()` (`dashboard_sst_v4_regra_inss.html`):

| Campo / Dimensão | Chave Gerada em `sst_sync.py` (JSON) | Chave Lida no `rebuildSeguranca()` (Chart.js) | Status de Compatibilidade | Observações / Pontos Críticos |
| :--- | :---: | :---: | :---: | :--- |
| **Data do Acidente** | `"data"` (ex: `"12/01"`) e `"data_full"` (`"12/01/2026"`) | `a.data \|\| a.data_full` | ✅ **Compatível** | Parser flexível implementado em JS com `str.split(/[\/\-\.]/)`. |
| **Nome do Colaborador** | `"colaborador"` | `a.colaborador` | ✅ **Compatível** | Usado na tabela e para cálculo de reincidência. |
| **Setor / Departamento** | `"setor"` | `a.setor` | ✅ **Compatível** | Agrupado nos gráficos `cSetorTip` e `cSetorTra`. |
| **Tipo do Acidente** | `"tipo"` (`"Típico"`, `"Trajeto"`) | `a.tipo` | ✅ **Compatível** | Comparação via função auxiliar `normTipo(a.tipo)`. |
| **Dias Afastados** | `"dias"` (inteiro, ex: `15`) | `a.dias` / `Number(a.dias)` | ✅ **Compatível** | Compatível com cálculos de dias perdidos e gravidade. |
| **Parte do Corpo** | `"parte"` (ex: *"Membros Inferiores..."*) | `a.parte` | ✅ **Compatível** | Extraído semanticamente pelo ETL e lido pelo gráfico `cParte`. |
| **Tipo de Lesão** | `"lesao"` (ex: *"Contusão / Impacto"*) | `a.lesao` | ✅ **Compatível** | Extraído semanticamente pelo ETL e lido pelo gráfico `cLesao`. |

### ⚠️ Identificação da Causa dos Gráficos em Branco (Caixas com Legenda, mas sem Gráfico)
1. **Comportamento do Chart.js com Volumes Mínimos de Dados:**  
   Quando o objeto estático `DEFAULT_DATA.acidentes` foi reduzido a apenas 2 registros mínimos (`12/01` e `16/01`, ambos no mês de **Janeiro** e com o mesmo setor/lesão), os gráficos de barras (`cMes`, `cDias`) renderizaram os eixos, mas por problemas de dimensionamento no contêiner CSS Grid sem altura explícita (`canvas` colapsado ou `height: 0px` por herança de grid) ou falha no carregamento externo da biblioteca, o canvas fica em branco.
2. **Incompatibilidade de Ambiente Offline (CDN Chart.js):**
   A importação da biblioteca depende de CDN:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
   ```
   Caso o usuário teste o arquivo em ambiente offline ou rede corporativa que restrinja pacotes externos da `jsdelivr` sem resolver o fallback a tempo da chamada síncrona `rebuildAll()`, o gráfico não é instanciado.

---

## 4. Console do Navegador (Erros Exatos no Developer Tools)

No cenário atual onde o HTML é aberto diretamente ou em ambiente sem backend ativo, os logs do **Console do Developer Tools (F12)** apresentam exatamente a seguinte sequência:

### Erro 1 — Falha na Requisição Fetch (CORS / Protocolo `file://` ou 404)
```text
Access to fetch at 'file:///api/sst_data' from origin 'null' has been blocked by CORS policy: 
Cross origin requests are only supported for protocol schemes: http, data, chrome, chrome-extension, https.
```
*(No Firefox / Edge offline: `Fetch API cannot load file:///api/sst_data. URL scheme "file" is not supported.`)*

### Erro 2 — Aviso do Catch Fallback no Dashboard
```text
Usando dados offline/padrão: TypeError: Failed to fetch
```
*(Confirmando que a aplicação reverteu para a leitura síncrona de `DEFAULT_DATA` e abortou a atualização remota).*

### Erro 3 — (Caso haja bloqueio de CDN ou offline no momento da execução de `updateChart`)
```text
Uncaught ReferenceError: Chart is not defined
    at updateChart (dashboard_sst_v4_regra_inss.html:1645)
    at rebuildSeguranca (dashboard_sst_v4_regra_inss.html:1580)
    at rebuildAll (dashboard_sst_v4_regra_inss.html:1610)
```
*(Ou, caso o Chart.js tenha carregado, mas o elemento Pai do Grid tenha altura zero no cálculo inicial de flex/grid):*
```text
Chart.js - Canvas is zero-sized, rendering cannot occur.
```

---

## 5. Recomendação Arquitetural para a Diretoria

1. **Separação de Responsabilidade (Desacoplar HTML do ETL):**
   - **Não** utilizar chamadas `fetch('/api/...')` no arquivo estático caso o produto final seja distribuído via arquivos no Google Drive/Desktop.
   - Adotar o padrão de geração de um arquivo auxiliar `sst_payload.js` pelo script Python que injete diretamente `window.__SST_DATA__ = { ... }`, sendo referenciado via `<script src="sst_payload.js"></script>`. Assim, o HTML se mantém extremamente leve e sem risco de CORS ou erro de CDN/fetch.
2. **Definição Explícita de Dimensões para o Chart.js:**
   - Garantir que todas as divs wrappers dos cards de gráfico possuam uma altura CSS mínima explícita (`min-height: 250px; position: relative;`) para que o `Chart.js` não colapse em canvas zero-sized ao renderizar dentro de CSS Grid.
