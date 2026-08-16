# Relatório Técnico: Build, Release e OTA (Over-The-Air)
**Projeto:** Dashboard People Analytics - Frequência Diária
**Data de Criação:** 25 de Julho de 2026

Este relatório documenta o processo de compilação (build), empacotamento e distribuição de atualizações do dashboard para garantir que futuros problemas de atualização (quando um executável falhar ao subir) possam ser rapidamente diagnosticados e resolvidos.

---

## 1. Visão Geral da Arquitetura de Build
O sistema possui scripts dedicados para automatizar a compilação do código Python em um executável (usando PyInstaller) e o envio desse pacote compilado para a nuvem (Google Drive), onde a aplicação cliente verificará se há novas atualizações através de um mecanismo OTA (Over-The-Air).

### Arquivos Principais Envolvidos:
- **`build_release.py`**: Script interativo principal que compila a aplicação (`FrequenciaDiaria.spec`), empacota os arquivos compilados (`dist/`) num `.zip`, altera as versões, faz upload para a pasta do Drive configurada e também gera *tags/commits* automáticos no Git.
- **`ota_release_auto.py`**: Uma versão não-interativa do release OTA, focada em enviar a versão *source code* ou uma versão pré-compilada, útil para pipelines de CI/CD.
- **`module_frequencia_diaria/FrequenciaDiaria.spec`**: O arquivo de configuração do PyInstaller. Ele define:
  - O ponto de entrada: `launcher.py` (com `console=False`).
  - Os módulos a incluir (`app_frequencia.py`, HTMLs, JS, arquivos do *core*).
  - Exclusões de pacotes pesados não utilizados (como pandas, numpy) para manter o `.exe` leve.
- **Arquivos de Configuração (`core/`)**:
  - `ota_config.json`: Contém o ID da pasta do Drive (`ota_folder_id`) onde o `.zip` será hospedado.
  - `token.json` e `credentials.json`: Credenciais OAuth2 usadas pelos scripts de release para autenticar no Google Drive API e fazer o upload.
  - `version_FrequenciaDiaria.json` (ou `version.json`): Controla a versão atual. A aplicação verifica a nuvem comparando a versão local com este arquivo.

---

## 2. Fluxo Normal de Atualização

Quando uma alteração é feita no frontend (`Auditoria de falta.html`) ou no backend (`app_frequencia.py`), os passos para lançar a atualização para os usuários são:

1. Executar `python build_release.py` na raiz do projeto.
2. Selecionar a opção correspondente (ex: `1 - FrequenciaDiaria`).
3. Definir a nova versão (ex: `v2.4.0`).
4. O script executará o PyInstaller usando o arquivo `.spec`.
5. Uma pasta `dist/FrequenciaDiaria` será gerada.
6. Todos os arquivos dentro de `dist/FrequenciaDiaria` serão empacotados em um arquivo temporário `.zip`.
7. O script usará a API do Google Drive para fazer upload do `.zip` e do `version_FrequenciaDiaria.json` sobrescrevendo os arquivos antigos usando o ID da pasta do Google Drive (`ota_folder_id`).
8. Opcionalmente, o script comitará as alterações no Git e publicará uma tag de Release.

---

## 3. Troubleshooting: O que fazer quando uma atualização "não subir"

Se você fez alterações no código e o executável dos usuários não está recebendo a atualização, verifique os seguintes itens:

### Problema A: Falha na Compilação Local
> **Sintoma:** O comando do PyInstaller quebra e o `.zip` nunca é gerado.
> **Como resolver:**
> 1. Execute a compilação de forma isolada para ler os erros: `py -m PyInstaller --noconfirm --clean "module_frequencia_diaria\FrequenciaDiaria.spec"`
> 2. Verifique se algum pacote novo importado não foi listado no `hiddenimports` dentro do `FrequenciaDiaria.spec`.
> 3. Certifique-se de que nenhum arquivo em uso ou terminal preso está segurando os arquivos da pasta `dist/` e `build/`.

### Problema B: Falha no Upload OTA (Google Drive)
> **Sintoma:** O script termina em erro ao tentar autenticar no Drive. A atualização não é disponibilizada na nuvem.
> **Como resolver:**
> 1. Verifique o arquivo `core/token.json`. Se ele expirou e não pode ser renovado sem interface gráfica, você pode precisar deletá-lo e rodar um script de autenticação interativo (`auto_updater.py` ou um script manual) para abrir o navegador, autorizar com sua conta Google e recriar o `token.json` válido.
> 2. Confirme se o `ota_folder_id` no `core/ota_config.json` ainda existe e você tem permissão de edição nele.

### Problema C: O Cliente não atualiza ao abrir o sistema
> **Sintoma:** A compilação e o upload dão certo, mas os usuários continuam na versão velha.
> **Como resolver:**
> 1. Abra o arquivo `core/version_FrequenciaDiaria.json` (ou `version.json` conforme configurado). A propriedade `"version"` **deve ser numericamente superior** à versão que o cliente tem (ex: mudando de `"2.3.9"` para `"2.4.0"`). O auto-updater (dentro de `core/auto_updater.py`) usa esse arquivo hospedado no Drive para saber se um novo `.zip` deve ser baixado.
> 2. Confirme se os arquivos (o `.zip` e o `version.json`) estão sendo criados na mesma pasta do Drive cujo ID está configurado no auto-updater do cliente.

### Problema D: Desalinhamento de Nomenclatura no Auto-Updater (Deploy Alfa Manual / Sudo Mode)
> **Sintoma:** Você faz o upload manual de um executável (ex: `.exe` direto) e de um arquivo chamado `version.json` para a nuvem, mas o cliente não atualiza.
> **Como resolver:**
> 1. O `core/auto_updater.py` **exige** que o arquivo na nuvem se chame `version_FrequenciaDiaria.json` e que o pacote seja um arquivo ZIP chamado `update_FrequenciaDiaria.zip`.
> 2. Se você subiu `version.json` ou o `.exe` solto (como exigido em alguns deploys forçados ou Alfa), a query da API do Drive no auto-updater (`name='version_FrequenciaDiaria.json'`) não retornará nada e a atualização ficará presa. Você deve sempre empacotar em `.zip` e usar o nome correto do versionador ou ajustar o script do auto-updater.

### Problema E: Efeito Matrioska no PyInstaller (Falta de Blacklist)
> **Sintoma:** O executável gerado na pasta `dist` começa a ficar gigante (gigabytes de tamanho) ou o build demora horas. Quando o cliente tenta baixar, a atualização trava pelo tamanho absurdo.
> **Como resolver:**
> 1. O PyInstaller, ao incluir a pasta do módulo local via `datas`, acaba engolindo a compilação anterior (pastas `dist/` e `build/`) num ciclo infinito se elas não forem bloqueadas.
> 2. Certifique-se de que o arquivo `.spec` utilizado (ex: `FrequenciaDiaria.spec`) contém o script de **Lista Negra** (Blacklist) que remove `dist` e `build` do array `a.datas` antes de gerar o binário. Sem isso, a atualização fica inviável para distribuição OTA.

### Problema F: Mismatch Crítico entre Nome do EXE e Arquivos OTA no Drive ⚠️ CAUSA RAIZ HISTÓRICA
> **Sintoma:** Os uploads OTA são feitos com sucesso para o Drive, mas os clientes **jamais** detectam uma nova versão. O sistema parece estar preso eternamente na mesma versão (ex: v2.4.2), sem atualizar mesmo após múltiplas tentativas de publicação.
> **Causa Raiz:**
> O `core/auto_updater.py` determina o nome do aplicativo dinamicamente a partir do nome do executável (linha `app_name = os.path.basename(sys.executable).replace('.exe', '')`).
> O EXE instalado nos clientes chama-se **`Absenteismo_plug.exe`**, portanto `app_name = "Absenteismo_plug"`.
> O auto-updater então busca no Drive por: `version_Absenteismo_plug.json` e `update_Absenteismo_plug.zip`.
> Se o servidor publicar apenas `version_FrequenciaDiaria.json` e `update_FrequenciaDiaria.zip`, a query da API retorna vazio e **nenhuma atualização é disparada**.
> **Como resolver:**
> 1. O script `ota_release_auto.py` foi corrigido para publicar **ambos os conjuntos** de arquivos a cada release:
>    - `version_FrequenciaDiaria.json` + `update_FrequenciaDiaria.zip` (para futuras instalações com o novo exe)
>    - `version_Absenteismo_plug.json` + `update_Absenteismo_plug.zip` (para os clientes já instalados com o exe antigo)
> 2. Este problema ficou escondido porque os scripts anteriores usavam nomes genéricos (`version.json`, `update.zip`), mas o `auto_updater.py` **nunca usou esses nomes genéricos** — ele sempre buscou pelo nome específico do app.


---

## 4. Testes Assistidos

Sempre que a lógica do dashboard for modificada intensamente, recomenda-se:
1. Validar rodando localmente (acessando os HTMLs).
2. Compilar um executável de testes com o `FrequenciaDiaria.spec`.
3. Executar o `FrequenciaDiaria.exe` gerado em `dist/FrequenciaDiaria/` antes de disparar o `build_release.py`.
4. Monitorar o console ou logs gerados pela interface do sistema de atualização.

---

## 5. Problema G — Loop Infinito de OTA (EXE nunca sobe o servidor)
**Data:** 07/08/2026 | **Versão corrigida:** v2.4.8

### Sintoma
O `FrequenciaDiaria.exe` iniciava, ficava ativo por ~10 segundos e morria silenciosamente sem abrir a porta 5008. Nenhum crash log era gerado. O comportamento se repetia em loop infinito.

### Causa Raiz (duas)
**Causa 1 — `auto_updater.py` lendo versão do `_MEIPASS` (somente leitura):**
- Em modo `frozen` (PyInstaller), `sys._MEIPASS` é uma pasta temporária extraída a cada execução, **sempre** contendo a versão que estava no bundle no momento da compilação.
- O `auto_updater.py` lia `version_{app_name}.json` de `base_dir = sys._MEIPASS`, que nunca era atualizado pelo OTA (pois `_MEIPASS` é read-only e recriado a cada execução).
- Resultado: local sempre = versão antiga → Drive sempre > local → OTA sempre disparava → `sys.exit(0)` antes do Flask iniciar.

**Causa 2 — `.update_stage` e `apply_update.bat` remanescentes:**
- Quando um OTA anterior rodava e o bat era gerado, mas o processo era encerrado abruptamente (ex: pelo PowerShell em testes), o `.update_stage/` e o `apply_update.bat` ficavam no disco.
- Na próxima execução do exe, o bat anterior rodava em background e matava o exe recém-iniciado.

### Solução Aplicada
1. **`core/auto_updater.py`** — Alterado `version_path` para usar `app_root` (pasta do `.exe` instalado) em vez de `base_dir` (`_MEIPASS`):
   ```python
   # ANTES (bug): versão embutida no bundle, nunca atualizada
   version_path = os.path.join(base_dir, 'core', f'version_{app_name}.json')
   # DEPOIS (fix): versão persistente ao lado do .exe, atualizada pelo OTA
   version_path = os.path.join(app_root, 'core', f'version_{app_name}.json')
   ```
2. **`dist/Absenteismo_plug/core/`** — O ZIP de release agora inclui `core/version_FrequenciaDiaria.json` e `core/version_Absenteismo_plug.json` com a versão correta, para que após o `apply_update.bat` extrair o ZIP, o `app_root/core/` tenha a versão atualizada.
3. **`module_frequencia_diaria/launcher.py`** — Melhorado crash logging com fallback para `%TEMP%` e Desktop, garantindo que erros do servidor sejam sempre capturados.

### Procedimento de Diagnóstico para o Futuro
Se o EXE morrer silenciosamente (~10s, sem porta, sem crash log):
1. Verificar se `app_root/core/version_FrequenciaDiaria.json` existe e tem JSON válido
2. Verificar se `.update_stage/` ou `apply_update.bat` estão na pasta do exe (artefatos órfãos — apagar!)
3. Comparar versão local vs Drive com: `py -3 scratch/diagnose_ota_version.py`
