# Diretrizes Operacionais do Módulo de Frequência Diária

## 🛑 Lockdown Operacional (Regra do Cercadinho)
- **Diretório Principal**: `D:\Projeto geral\People analytics - GP\module_frequencia_diaria`
- **Permissão de Leitura Externa**: Apenas para a pasta `D:\Projeto geral\People analytics - GP\core/` para leitura de credenciais (`token.json`, `acesso_config.json`, etc.).
- **Proibição**: Nenhuma modificação, criação ou busca de arquivos deve ser feita fora de `module_frequencia_diaria`.

## 🔑 Passe Livre no Google Drive
- **Pastas Autorizadas**:
  1. `https://drive.google.com/drive/folders/16iPgRhOPqb4pBDGI9FoBqQdYgnzuAcqg?usp=drive_link`
  2. `https://drive.google.com/drive/folders/11G8qWpSj87bRo0EmK-JJCFqGQ82MLyRc?usp=drive_link`
- **Autenticação Silenciosa**: Usar `token.json` presente na pasta `core/`. Operações de I/O nestas pastas estão pré-autorizadas.
- **Cloud-First Storage (Armazenamento na Nuvem Obrigatório)**: Todo novo arquivo de dados gerado, relatório extraído, ou pastas criadas dinamicamente DEVEM ser salvos DIRETAMENTE nas pastas autorizadas do Google Drive. O diretório local (`module_frequencia_diaria`) deve ser usado estritamente para hospedar CÓDIGO (HTML, JS, Python) e processamento em memória. Não suje o disco local do usuário com arquivos de dados se você tem passe livre para usar a nuvem.

## 🔇 Modo de Execução
- Proibida abertura de navegadores visuais sem autorização expressa do usuário.
- Executar operações de E/S de forma automatizada e silenciosa.

## 🤖 Protocolo Headless Ativado
- **Testes visuais proibidos**: PROIBIÇÃO TOTAL de abrir navegadores visuais ou interfaces gráficas para testes, a menos que o usuário dê uma ordem expressa e nominal.
- **Testes via script HTTP**: O teste deve ser feito de forma automatizada e invisível (Headless/Background) usando requisições HTTP internas em Python (ex: biblioteca 'requests') ou análise estática de logs do terminal.
- **Evidência de sucesso**: Entregar recibo técnico contendo o status HTTP da rota e o log limpo do terminal provando que o servidor subiu e respondeu sem exceções.

## 🧠 Memória Arquitetural Homedock Suite
- O arquivo `Absenteismo_plug_SUITE_MEMORY.md` na raiz do projeto contêm o mapeamento de módulos, padrões de arquitetura (Shared Core, OTA, RBAC) e regras de execução automatizada (QA Headless via Playwright).
- Sempre consulte este arquivo antes de planejar alterações complexas nos módulos.

## 📖 Rotina de Consulta Técnica Autônoma
- **Trigger Ouro**: Sempre que iniciar uma nova conversa neste projeto (ou quando o usuário usar as palavras-chave "faça consulta técnica" ou "consulta técnica"), sua PRIMEIRA AÇÃO obrigatória é ler a documentação do projeto.
- **Ação Obrigatória**: Você DEVE utilizar a ferramenta `view_file` para ler (ou reler se estiverem truncados) os seguintes arquivos de orientação antes de prosseguir com alterações de código ou arquitetura:
  1. `D:\Projeto geral\People analytics - GP\module_frequencia_diaria\Absenteismo_plug_SUITE_MEMORY.md`
  2. `D:\Projeto geral\People analytics - GP\module_frequencia_diaria\ARQUITETURA_TECNICA_SERVIDOR_LOCAL.md`
  3. `D:\Projeto geral\People analytics - GP\module_frequencia_diaria\BUILD_AUDIT.md`
  4. `D:\Projeto geral\People analytics - GP\CORE_ARCHITECTURE.md`
- **Por que isso é necessário?**: O usuário não memoriza a lista de todos os arquivos de arquitetura criados. É seu papel como agente autônomo garantir que você sempre tenha o contexto mais atualizado lendo esses arquivos como se fossem sua "bíblia" de desenvolvimento para este repositório.
