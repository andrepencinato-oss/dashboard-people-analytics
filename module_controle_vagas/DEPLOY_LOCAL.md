# 🚀 Guia Rápido de Instalação no Servidor (Deploy Local)

Siga os passos abaixo na **máquina Windows que servirá de Servidor** para a equipe:

### Passo 1: Instalação Automática com 1 Clique
1. Extraia a pasta do `.zip` no computador servidor (ex: na Área de Trabalho ou `C:\`).
2. Clique com o **botão direito** no arquivo **`instalar_servico.bat`** e selecione **"Executar como Administrador"**.
3. O script irá automaticamente:
   - Criar a regra de liberação da **porta 5000** no Firewall do Windows.
   - Configurar a inicialização automática no boot do Windows (`shell:startup`).

---

### Passo 2: Iniciar o Servidor Manualmente (Primeira Vez)
- Dê dois cliques em **`iniciar_servidor.vbs`** para subir o servidor em segundo plano imediatamente.

---

### Passo 3: Descobrir o Link de Acesso para a Equipe
1. Pressione `Win + R`, digite `cmd` e dê Enter.
2. Digite o comando:
   ```cmd
   hostname
   ```
3. O terminal mostrará o nome do seu computador (ex: `PC-RH-01`).
4. O link de acesso da aplicação para todos na rede será: **`http://NOME_DO_SEU_PC:5000`** (ex: `http://PC-RH-01:5000`).

---
🎉 **Pronto!** A aplicação está configurada e sempre subirá sozinha quando o Windows iniciar.
