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

---

## 4. Testes Assistidos

Sempre que a lógica do dashboard for modificada intensamente, recomenda-se:
1. Validar rodando localmente (acessando os HTMLs).
2. Compilar um executável de testes com o `FrequenciaDiaria.spec`.
3. Executar o `FrequenciaDiaria.exe` gerado em `dist/FrequenciaDiaria/` antes de disparar o `build_release.py`.
4. Monitorar o console ou logs gerados pela interface do sistema de atualização.
