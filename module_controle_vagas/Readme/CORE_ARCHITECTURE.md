SYSTEM_INSTRUCTION: Toda vez que o usuário relatar um problema com 'Build', 'OTA', 'Atualização' ou 'Deploy', o Agente Antigravity É OBRIGADO a ler a seção de Pipeline OTA deste arquivo ANTES de iniciar qualquer investigação ou propor qualquer código.

# CORE_ARCHITECTURE - Leis Imutáveis do Sistema

Este documento serve como a Constituição Arquitetural do projeto "People Analytics - GP". Estas regras são inegociáveis e devem ser consultadas e respeitadas por qualquer agente trabalhando nesta base de código.

## 1. Arquitetura Shared Core e Isolamento
- **Shared Core:** A pasta `core/` contém módulos e metadados vitais compartilhados que orquestram inicialização, autenticação e atualização OTA para os variados sub-sistemas compilados. 
- **Isolamento do Drive:** A aplicação e seus scripts de orquestração rodam baseados na estrutura de pastas estática provida no drive de execução, assumindo independência do ambiente host e garantindo que o software opere como um pacote autocontido (ONEDIR).

## 2. Regra de Autenticação (Login Clássico In-Memory)
- **Zero E-mail:** A autenticação, permissão de visualização e o controle de acesso a setores (como verificado via endpoints) são geridos de forma clássica em memória (usando estruturas como `acesso_config.json`). Não existe validação nem envio de e-mails de autenticação ativa ou dependência de servidores de e-mail online para login no Dashboard.

## 3. Pipeline OTA Saneado (Over-The-Air)
A rotina de atualização (OTA Bootloader) deve ser tratada com máxima cautela para não desencadear "Falhas Silenciosas" comuns no Windows (onde a versão é lida como atualizada, mas o cache/ficheiro físico não é alterado).

- **Rename Swap Pattern (.old):** O Windows bloqueia a sobrescrita e remoção de binários (`.exe`, `.dll`, `.pyd`) que se encontram alocados na memória. Atualizações automatizadas via `.bat` DEVEM usar obrigatoriamente a troca via renomeação (ex: `ren *.exe *.exe.old`), pois a renomeação é permitida pelo OS mesmo com o binário em uso. Só depois se executa o `xcopy` dos novos arquivos do `.update_stage`.
- **Detached Process:** Para impedir que o processo atualizador (o subprocesso executando o script `.bat` de *apply_update*) herde os *file handles* bloqueantes do executável Python (o processo pai), a chamada `subprocess.Popen` TEM QUE INJETAR a flag de desvinculação absoluta `creationflags=0x00000008` (DETACHED_PROCESS) em conjunto com `close_fds=True`. Após essa chamada, o Python deve morrer via `sys.exit()`.
- **Guarda de Versão (Success Guard):** O arquivo contendo a versão remota (`version.json` baixado) só pode ser promovido para a sua localização final se a cópia física (presença do novo `.exe` pós Rename Swap) for validada via código (ex: validação `if exist`). Nunca permitir que o `xcopy` da pasta temporária sobrescreva livremente os metadados antes de garantir os binários vitais.
