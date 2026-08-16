# PLANO DE TRABALHO E DIRETRIZES DE EXECUÇÃO DA IA

0. DIRETRIZ SUPREMA: AUTORIDADE DO USUÁRIO (SUDO MODE)
- O usuário tem liberdade e autoridade absoluta. TODAS as regras abaixo são apenas o "Comportamento Padrão". Se o usuário der uma ordem explícita que vá contra as regras abaixo (ex: "abra o navegador", "leia linha por linha", "crie um arquivo em outra pasta"), a ordem dele PREVALECE SEMPRE. Não bloqueie, não recuse e não aponte conflito. Apenas execute a ordem específica e depois retorne ao padrão.

1. CONFINAMENTO DE DIRETÓRIO (COMPORTAMENTO PADRÃO)
- Por padrão, atue apenas dentro de `module_controle_vagas`. Não mexa em outras pastas a menos que solicitado.
- Você tem passe livre para usar as credenciais do Drive/GitHub via `core/` sem pedir permissão.

2. MODO TURBO (COMPORTAMENTO PADRÃO)
- Evite `grep_search` excessivo. Prefira abrir e ler o arquivo inteiro na memória de uma vez para ganhar velocidade.
- Não processe arquivos linha por linha no terminal. Avalie tudo em memória e aplique a solução.

3. ECONOMIA DE TOKENS / SEM TESTE VISUAL (COMPORTAMENTO PADRÃO)
- Como regra geral, NÃO use simulação de browser (`manage_task`) para testar UI. Deixe o QA visual para o usuário.

4. ONE-SHOT OUTPUT (COMPORTAMENTO PADRÃO)
- Ao gerar relatórios (.md) ou arquivos novos, cuspa o resultado de uma vez só. Use scripts Python para escrever arquivos pesados rápido se o terminal for lento.

5. PADRÃO TOKEN-FRIENDLY (COMPORTAMENTO PADRÃO)
- Trabalhe em silêncio absoluto no terminal. Sem logs longos ou explicações dos seus "pensamentos".
- Devolva apenas um recibo minimalista ao concluir a tarefa.
