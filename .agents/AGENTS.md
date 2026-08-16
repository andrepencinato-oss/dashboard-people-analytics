# Regras do Projeto — Módulo Frequência Diária / OTA Deployment

> **REGRA OBRIGATÓRIA**: Este resumo técnico deve ser **dinâmico**. Toda vez que qualquer novo problema ou ajuste relacionado à atualização/deploy for resolvido no futuro, esta documentação deve ser **atualizada imediatamente** com o novo cenário, causa raiz e solução aplicada.

## Resumo Técnico: Diagnóstico de Falhas na Atualização OTA e Protocolo de Resolução

Sempre que o usuário solicitar subir uma atualização e ela não aplicar nos computadores dos usuários ou no executável desktop, seguir e aplicar os pontos descritos abaixo:


### 1.1 Bug de Integração com Google Drive (Falso Negativo de Lotação)
- **Causa**: Ao processar os CSVs do Drive (Afastamento e Aviso Prévio), o sistema realizava o cruzamento (lookup) baseando-se estritamente na propriedade `cad` (`vagasData.find(v => String(v.cad) === cad)`). No entanto, os colaboradores já persistidos no cache local (`vagas.json`) possuíam apenas `codigo` e `id`, sem a chave `cad`. Isso gerava falsos negativos nas comparações (`String(undefined) === cad`), fazendo com que o painel exibisse 0 afastados/avisos mesmo lendo o arquivo corretamente.
- **Resolução**: A rotina de cruzamento no Javascript (`templates/index.html`) deve utilizar uma verificação tripla de identificadores: `vagasData.find(v => String(v.cad) === cad || String(v.codigo) === cad || String(v.id) === cad)`.
- **Aprimoramento Visual (Ação)**: Em vez de sobrescrever o estado dos afastados de risco apenas com a string genérica "Afastamento", a variável `colab.acao` recebe o motivo real mapeado do CSV (ex: "Auxílio Doença", "Licença Maternidade"). O array estático do elemento `<select>` também foi atualizado para carregar de forma dinâmica `[...new Set([...acoesList, acaoAtual])]` para garantir a exibição visual do motivo do Drive sem quebrar o componente do dropdown.

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

---

### 3. Regra de Deploy Automático (Sinal Verde Permanente)

> **AUTORIZAÇÃO E OBRIGATORIEDADE PERMANENTE**: A partir de 30/07/2026, o agente possui **autorização total, absoluta e permanente** para executar o pipeline de Release e Upload OTA para o Google Drive sempre que uma nova versão local for compilada e validada com sucesso.
> - **NÃO PEÇA PERMISSÃO** para subir a nova versão para o Google Drive.
> - O upload dos pacotes (`update_FrequenciaDiaria.zip` e `version_FrequenciaDiaria.json`) para a nuvem **é etapa obrigatória da conclusão de qualquer tarefa de alteração ou validação de versão**.

---

### 4. Rotina de Consulta Técnica Autônoma
> **REGRA DE CONTEXTO**: O usuário não memoriza a lista de todos os arquivos de arquitetura criados. É seu papel como agente autônomo garantir que você sempre tenha o contexto mais atualizado.
- **Trigger Ouro**: Sempre que iniciar uma nova conversa neste repositório (ou quando o usuário disser "faça consulta técnica" / "consulta técnica"), sua PRIMEIRA AÇÃO obrigatória é ler a documentação do projeto.
- **Ação Obrigatória**: Você DEVE utilizar a ferramenta `view_file` para ler (ou reler se estiverem truncados) os seguintes arquivos de orientação antes de planejar ou executar qualquer alteração estrutural:
  1. `D:\Projeto geral\People analytics - GP\Absenteismo_plug_SUITE_MEMORY.md` (ou sua versão no módulo)
  2. `D:\Projeto geral\People analytics - GP\CORE_ARCHITECTURE.md`
  3. `D:\Projeto geral\People analytics - GP\Manifesto_People_Analytics.md`
  4. `D:\Projeto geral\People analytics - GP\relatorio_tecnico_build.md`
  5. E os arquivos `.md` correspondentes ao módulo em que estiver trabalhando (ex: `ARQUITETURA_TECNICA_SERVIDOR_LOCAL.md` ou `BUILD_AUDIT.md`).
