# 

Documentação Técnica: Estrutura de Acesso e RBAC \- Homedock Suite

---

Este documento detalha a arquitetura de autenticação e o controle de acesso baseado em funções (RBAC \- Role-Based Access Control) implementados na **Homedock Suite**. O foco principal é a gestão segura de logins, senhas e a delegação de permissões para criação de novos usuários (Master/Admins criando outros usuários).

## **1\. Visão Geral da Arquitetura (Shared Core)**

A arquitetura de segurança segue o nosso princípio de **Shared Core (Coração Blindado)**. Nenhum dado sensível de login ou senha trafega livremente pelo código cliente (Front-end). Toda a lógica de autenticação é centralizada e isolada, garantindo que o sistema de atualização autônoma (OTA) não sobrescreva as credenciais dos usuários.

> * **Isolamento de Dados:** O arquivo principal de configuração de acessos (acesso\_config\_cloud.json) fica armazenado de forma segura na nuvem/Data Lake e é consumido pelo backend.  
> * **Criptografia:** As senhas nunca são armazenadas em texto plano. É utilizado um algoritmo de hashing forte (como *Bcrypt* ou *SHA-256 com Salt*).  
> * **Sessão Isolada:** O Flask/Waitress no backend gerencia a sessão via tokens JWT ou cookies seguros, garantindo que o usuário só acesse as rotas permitidas.

## **2\. Hierarquia de Níveis de Acesso (RBAC)**

Para permitir que "usuários criem outros usuários" de forma segura, estabelecemos uma matriz de privilégios. Apenas usuários com a flag de administrador possuem acesso ao painel de gestão de contas.

| Nível de Acesso (Role) | Descrição e Privilégios | Pode Criar Usuários?   |
| :---- | :---- | :---- |
| **Master Admin / Diretor** | Acesso total a todos os módulos (Absenteísmo, Quadro de Vagas, Jurídico, SST). Pode ver todas as configurações do Shared Core. | **Sim** (Qualquer nível) |
| **Gestor RH (Admin Regional)** | Visualiza e interage com os dashboards. Possui permissão para convidar novos funcionários da sua própria equipe. | **Sim** (Apenas Visualizadores) |
| **Visualizador Padrão** | Acesso somente leitura aos módulos autorizados. Não possui acesso ao painel de configurações. | Não |

## **3\. Estrutura de Dados (acesso\_config\_cloud.json)**

A persistência dos usuários é feita em um dicionário JSON estruturado. Abaixo está o modelo de como o sistema armazena quem é quem e quem criou quem.

`{`  
  `"users": {`  
    `"andre_diretor": {`  
      `"nome": "André Chefe",`  
      `"password_hash": "$2b$12$Kix...[HASH_AQUI]",`  
      `"role": "master_admin",`  
      `"modulos_autorizados": ["todos"],`  
      `"criado_por": "system",`  
      `"data_criacao": "2026-08-01"`  
    `},`  
    `"joao_rh": {`  
      `"nome": "João do RH",`  
      `"password_hash": "$2b$12$Lpm...[HASH_AQUI]",`  
      `"role": "gestor_rh",`  
      `"modulos_autorizados": ["frequencia_diaria", "organograma"],`  
      `"criado_por": "andre_diretor",`  
      `"data_criacao": "2026-08-10"`  
    `}`  
  `}`  
`}`  
  


## **4\. Fluxo de Criação de Novos Usuários (O Motor)**

O fluxo técnico para que um usuário crie outro dentro da Homedock Suite segue etapas estritas de validação para garantir a integridade da plataforma:

> 1. **Autenticação do Solicitante:** O usuário acessa o "Painel de Controle". O backend verifica via middleware (ex: @admin\_required) se a sessão ativa pertence a um master\_admin ou gestor\_rh.  
> 2. **Preenchimento do Formulário:** O administrador preenche o Novo Login, Senha Temporária, Nível de Acesso (Role) e Módulos Permitidos.  
> 3. **Interceptação no Backend:** O Python recebe o POST. Ele **não salva** a senha digitada. Ele passa a string por uma biblioteca de hash (ex: werkzeug.security.generate\_password\_hash).  
> 4. **Gravação no Core:** O sistema abre o acesso\_config\_cloud.json, adiciona o novo objeto de usuário, registra quem foi o "Padrinho" (campo criado\_por) e salva o arquivo de volta no Data Lake / Shared Core.  
> 5. **Primeiro Login (Opcional):** Ao logar pela primeira vez, o sistema pode forçar o novo usuário a trocar a senha temporária para uma definitiva, atualizando o hash.