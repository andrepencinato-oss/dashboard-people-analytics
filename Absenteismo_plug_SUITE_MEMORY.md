# 🧠 Absenteismo_plug SUITE - MEMÓRIA ARQUITETURAL E REGRAS DE NEGÓCIO

## 1. Regras Operacionais da IA (Lockdown & Token-Friendly)
- **Lockdown Operacional:** O agente deve sempre trabalhar restrito à pasta do módulo atual. É proibido alterar arquivos de outros módulos sem ordem expressa.
- **Sem Teste Assistido (Trava Financeira):** É ESTRITAMENTE PROIBIDO abrir instâncias de navegadores (Chrome/Edge) para visualização. Testes de UI são feitos apenas pelo usuário humano.
- **QA Headless:** Validações de UI automatizadas devem usar scripts em background (Playwright Headless) que geram prints (.png) como prova física do funcionamento, sem abrir janelas visuais.
- **SUDO MODE:** Quando acionado, a IA não deve fazer perguntas de triagem. Deve assumir o risco técnico, executar, compilar e entregar o recibo.

## 2. Padrões de Arquitetura (Homedock Suite)
- **Shared Core (Coração Blindado):** Arquivos vitais ('token.json', 'credentials.json', atualizadores) ficam isolados na pasta 'core/'. Nenhum módulo tem senhas hardcoded.
- **Code vs Data:** Código no C: ou subpastas estruturadas; arquivos de dados pesados (.xlsx, .csv) não se misturam com o código da aplicação principal.
- **Atualização OTA (Over-The-Air):** Deploy de novas versões é feito alterando o 'version.json' e subindo o executável '.exe' (compilado via PyInstaller) direto para a pasta OTA oficial no Google Drive (ID: 16iPgRhOPqb4pBDGI9FoBqQdYgnzuAcqg) via API silenciosa.
- **RBAC (Cegueira Hierárquica):** Módulos possuem filtros restritivos que leem o perfil do usuário logado e mostram apenas os Centros de Custo (Setores) autorizados para ele.

## 3. Mapeamento de Módulos (Status Atual)
- **Módulo Frequência Diária (Absenteísmo):** Dashboard reativo com filtros globais (Mês, Semana, Setor). Implementado "Triplo Quadro Top 20 Absenteísmo" (Abas: Semana, Mês, Global) operando independente do filtro de dia. Tela de Controle de Acesso homologada e sincronização em memória corrigida. (Versão OTA Atual: 1.0.8).
- **Módulo Jurídico:** Implementada rota inteligente que cruza o ID e direciona o usuário direto para a subpasta do colaborador no Google Drive, em vez da pasta raiz.
- **Módulo Quadro de Vagas:** Estruturado com regras de ancoragem do Shared Core. Layouts de Cadastro e Auditoria unificados.
- **Módulo SST:** Regras de retenção do INSS estruturadas. Desenvolvimento de script ETL autônomo focado no cálculo de Tempo de Empresa a partir da Data de Admissão.
- **Módulo Organograma:** Deploy isolado na pasta de distribuição contendo a Chave-Mestra para GitHub e Drive.
