# Regras do Projeto — Módulo Frequência Diária / OTA Deployment

> **REGRA OBRIGATÓRIA**: Este resumo técnico deve ser **dinâmico**. Toda vez que qualquer novo problema ou ajuste relacionado à atualização/deploy for resolvido no futuro, esta documentação deve ser **atualizada imediatamente** com o novo cenário, causa raiz e solução aplicada.

## Resumo Técnico: Diagnóstico de Falhas na Atualização OTA e Protocolo de Resolução

Sempre que o usuário solicitar subir uma atualização e ela não aplicar nos computadores dos usuários ou no executável desktop, seguir e aplicar os pontos descritos abaixo:

---

### 1. Diagnóstico dos 3 Motivos de Falha

1. **Bloqueio por Igualdade de Versão (`remote <= local`)**:
   - **Causa**: O `auto_updater.py` compara a versão remota no Google Drive (`version_FrequenciaDiaria.json`) com a versão do app local. Se as duas versões forem iguais (ex: `2.1.6 == 2.1.6`), o atualizador conclui que o app já está atualizado e **cancela o download do arquivo ZIP**.
   - **Resolução**: É obrigatório realizar um **bump de versão** (ex: `2.1.6` -> `2.1.7`) em `core/version.json`, `core/version_FrequenciaDiaria.json` e no HTML do aplicativo antes de empacotar.

2. **Bloqueio do Token OAuth por Ausência de Fallback**:
   - **Causa**: Em modo empacotado (`frozen`), a verificação de credenciais do Drive em `auto_updater.py` buscava o `token.json` estritamente na pasta `%LOCALAPPDATA%\PeopleAnalytics\core\token.json`. Se o arquivo não existia no `%LOCALAPPDATA%`, o `get_drive_service()` retornava `None` e abortava silenciosamente.
   - **Resolução**: Manter o fallback no `get_drive_service()` para buscar em `sys._MEIPASS\core\token.json` e na pasta raiz da aplicação caso o `%LOCALAPPDATA%` não esteja populado.

3. **Bloqueio do Executável (`.exe`) na Memória do Windows**:
   - **Causa**: O processo `FrequenciaDiaria.exe` permanecia preso em memória ou segurando a porta `5008` enquanto o script `apply_update.bat` tentava rodar o `xcopy`. Como o arquivo `.exe` estava em execução, o Windows bloqueava a substituição, fazendo o `xcopy` falhar e o sistema reiniciar na versão antiga.
   - **Resolução**: Incluir o encerramento forçado (`taskkill /f /im FrequenciaDiaria.exe`) e a liberação da porta `5008` no script `apply_update.bat` e no `launcher.py` antes da sobreposição dos arquivos.

---

### 2. Protocolo Padrão para Subir Atualizações OTA

Sempre executar os passos abaixo na sequência exata:

1. **Incremento de Versão**:
   - Atualizar a versão em `core/version.json` e `core/version_FrequenciaDiaria.json`.
   - Atualizar a tag de versão em `module_frequencia_diaria/Auditoria de falta.html`.

2. **Compilação e Empacotamento**:
   - Compilar o aplicativo via PyInstaller com o spec `module_frequencia_diaria/FrequenciaDiaria.spec`.
   - Gerar os arquivos `.zip`: `update_FrequenciaDiaria.zip` e `update.zip` a partir da pasta `dist/FrequenciaDiaria`.

3. **Upload para o Google Drive e GitHub**:
   - Enviar `update_FrequenciaDiaria.zip`, `version_FrequenciaDiaria.json`, `update.zip` e `version.json` para o diretório OTA do Drive (`1Qw7NaPXXl_BEK6uFKdcL3NQ0liB2v1bC`).
   - Registrar o commit e a tag correspondente no repositório Git.

4. **Aplicação e Teste de Funcionamento**:
   - Finalizar os processos pendurados em memória na porta `5008`.
   - Garantir que a pasta `%LOCALAPPDATA%\PeopleAnalytics\core` contenha o `token.json` e `credentials.json` válidos.
   - Executar o app localmente/no desktop e validar o HTML servido em `http://127.0.0.1:5008/dashboard`.
