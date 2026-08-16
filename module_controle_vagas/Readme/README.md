# People Analytics - GP

Bem-vindo ao repositório central do **People Analytics - GP**, uma suíte avançada de módulos analíticos de Recursos Humanos focada em alta performance, disponibilidade local (On-Premise) e atualizações transparentes (OTA).

Este documento consolida as principais diretrizes arquiteturais e regras de negócio extraídas dos manifestos do projeto.

---

## 1. Visão Geral da Arquitetura

O projeto adota uma arquitetura de aplicação web desacoplada (**Single Page Application - SPA**) distribuída através de executáveis locais autônomos.

- **Stack Principal:** Backend em Python (Flask) servindo APIs RESTful; Frontend em Vanilla HTML/CSS/JS (com uso de bibliotecas como Select2, DataTables e Tailwind CSS).
- **Servidor Local Autônomo (Zero-Cloud Cost):** Os módulos são compilados via PyInstaller e rodam como serviços locais no Windows, abertos para a rede local (`0.0.0.0`) e inicializados silenciosamente via `VBScript` no boot. Acessíveis na Intranet através do *Hostname* (ex: `http://NomeDoPC:5000`).
- **Sistema de Cache em Memória (Singleton):** Para garantir tempos de resposta de milissegundos, o back-end processa os dados (Pandas) e armazena na memória RAM (`CACHE`) durante o "Cold Start" da aplicação.
- **Integração Read-Only via Arquivos (Air Gap Lógico):** Não há conexão direta aos bancos de dados transacionais. O sistema consome relatórios (XLS, XLSX, CSV) sincronizados do Google Drive.
- **Shared Core (Coração Blindado):** Credenciais críticas (`token.json`, `credentials.json`) vivem isoladas na pasta `core/`, jamais expostas nos binários dos módulos individuais.

---

## 2. Módulos da Suíte (Status Atual)

O ecossistema é formado por sub-sistemas independentes, que compartilham as premissas arquiteturais:

1. **Frequência Diária (Absenteísmo):** Dashboard dinâmico para acompanhamento de faltas e horas devidas. **Regra vital**: Faltas parciais >= 8.5 horas são convertidas em "Faltas Integrais".
2. **Quadro de Vagas & Auditoria de Lotação:** Monitoramento de SLA de recrutamento e cruzamento do Headcount Ativo com movimentações (afastamentos > 30 dias, avisos prévios, rescisões e aposentadoria). Calcula o *Headcount Líquido* descontando vacâncias reais.
3. **SST (Saúde e Segurança do Trabalho):** Acompanha retenções do INSS e inclui scripts ETL autônomos para calcular o tempo de empresa dos colaboradores.
4. **Organograma:** Distribuição visual hierárquica baseada nos dados contábeis.
5. **Jurídico:** Sistema inteligente de roteamento que direciona os usuários diretamente para a subpasta do colaborador no Google Drive.

---

## 3. Regras de Negócio Analíticas

Ao processar relatórios de Headcount e Faltas (como feito na Auditoria de Lotação), o motor analítico segue regras estritas:

- **Saneamento Contábil:** Registros puramente sintéticos (cabeçalhos, totais, nomes vazios) são completamente ignorados.
- **O que NÃO é Afastamento:** Férias e faltas esporádicas não configuram redução de ocupação da vaga.
- **Regra dos 30 Dias:** Afastamentos temporários só impactam o Headcount ativo se a previsão de retorno for superior a 30 dias.
- **Exceções Trabalhistas Isoladas:** Aposentadorias por Invalidez e Licenças Reclusão recebem tags específicas para não inflacionar distorcidamente as métricas operacionais regulares.

---

## 4. Pipeline OTA (Over-The-Air) e Atualizações

O sistema utiliza um mecanismo resiliente para manter os executáveis clientes sempre atualizados silenciosamente, contornando o bloqueio de arquivos em uso pelo Windows.

### Fluxo de Build & Deploy:
1. **Compilação Local:** O script `build_release.py` empacota a versão via PyInstaller.
2. **Upload Automático:** Um arquivo `.zip` com a compilação e um `version.json` atualizado são enviados para o Drive.
3. **Download e Substituição:** Ao iniciar, o `auto_updater.py` local checa as versões. Se estiver desatualizado, ele baixa o `.zip` na pasta `.update_stage`.
4. **Detached Swap:** Um arquivo `.bat` roda em um subprocesso desvinculado (*detached process*), mata o executável antigo, renomeia-o para `.old` e extrai a nova versão antes de iniciar.

### ⚠️ Regras Essenciais de Build:
- O arquivo `.spec` **deve** conter a *Blacklist* que impede que as pastas de compilações antigas (`dist/` e `build/`) sejam sugadas recursivamente (Efeito Matrioska).
- Atualizações devem ser validadas comparando as versões via disco na pasta do app (`app_root/core/`), e nunca através da pasta temporária protegida `_MEIPASS`.

---

## 5. Como Iniciar Localmente

Para rodar qualquer um dos módulos em ambiente de desenvolvimento (como o Quadro de Vagas):
1. Verifique se o diretório raiz `core/` contém `token.json` e `credentials.json` válidos.
2. Acesse a pasta do módulo: `cd module_controle_vagas`.
3. Inicie o servidor: `python app.py` (ou script equivalente de inicialização).
4. O servidor escutará em `http://127.0.0.1:5000` e puxará os dados necessários automaticamente do Drive via Shared Core.

*Para maior aprofundamento, os documentos `Manifesto_People_Analytics.md` e `CORE_ARCHITECTURE.md` na raiz do projeto contêm a visão integral da infraestrutura.*
