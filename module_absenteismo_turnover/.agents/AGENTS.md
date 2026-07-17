# General Rules

- **Autonomia de Servidor:** Sempre que atualizar o backend, o frontend, ou quando o usuário pedir para 'subir o projeto', o assistente DEVE, de forma autônoma: buscar o processo que está usando a porta 5006, derrubá-lo via terminal (ex: listando tarefas ou usando taskkill), e levantar o servidor Flask novamente em background (`py -3 app_absenteismo.py`). Nunca deve pedir ao usuário para fazer isso.
- **Entrega Visual do Link:** Toda vez que finalizar uma tarefa e o servidor estiver pronto, a resposta final DEVE conter obrigatoriamente o link de acesso formatado e em destaque: 👉 http://localhost:5006. O assistente nunca deve encerrar uma tarefa sem fornecer o link de acesso ao usuário.
