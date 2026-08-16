# 🕵️ BUILD_AUDIT: Relatório Técnico de Compilação

## 1. Ferramenta de Empacotamento
A ferramenta sendo utilizada para empacotar o aplicativo é o **PyInstaller**, configurado e orquestrado através do arquivo `FrequenciaDiaria.spec` (e acionado pelo script `build_release.py`).

## 2. Regra Atual de Varredura (O Problema)
O erro "Matrioska" está ocorrendo devido à forma como o PyInstaller analisa as dependências. Durante o bloco `Analysis` no arquivo `.spec`:
- O `module_frequencia_diaria` é incluído como pacote (via `hiddenimports` e pelas regras em `datas`).
- Ao identificar o diretório como um pacote Python/módulo principal, o motor do PyInstaller copia recursivamente **todo o conteúdo do diretório base** para garantir que recursos de dados (HTML, JS) sejam levados ao executável.
- Como não há nenhum filtro explícito de exclusão de subdiretórios de sistema no `.spec`, ele "varre" tudo o que vê pela frente.

## 3. Por Que Ocorre o Efeito Matrioska? (Vazamento de Lixo)
As pastas de lixo (`dist`, `build`, `.agents`, `__pycache__`) vazam para dentro do pacote final devido a um ciclo recursivo:
1. O PyInstaller gera a compilação atual e despeja os binários e os pacotes nas pastas temporárias `build/` e na final `dist/`, localizadas dentro do próprio diretório do projeto.
2. Na compilação **seguinte**, o varredor de dados do PyInstaller (que copia a pasta do módulo) enxerga as pastas `dist/` e `build/` da compilação anterior como se fossem "arquivos normais do projeto".
3. Ele então coloca o `dist` antigo *dentro* do novo executável empacotado.
4. Ao repetir esse processo, cada nova compilação engole a compilação anterior (Matrioska), deixando o arquivo massivo, poluído e consumindo memória excessiva. O parâmetro `excludes=[]` do PyInstaller infelizmente só bloqueia módulos Python puros, e não diretórios estáticos.

## 4. Onde e Como Aplicar a Lista Negra (Blacklist)
Para estancar esse vazamento, precisaremos interceptar e filtrar a lista de dados (`a.datas`) recolhida pelo PyInstaller **antes** de passá-la para as etapas de criação do executável (`PYZ` e `EXE`).

- **Arquivo Alvo**: `FrequenciaDiaria.spec` (e demais `.spec` do projeto, se necessário).
- **Local Exato (Linha)**: Imediatamente após o fechamento do bloco `a = Analysis(...)` (por volta da linha 56), e **antes** da linha `pyz = PYZ(a.pure)`.
- **Implementação Sugerida**:
  Criaremos um filtro iterativo em Python dentro do próprio arquivo `.spec` para remover da variável `a.datas` qualquer arquivo que pertença às pastas da Lista Negra.
  
  ```python
  # --- LISTA NEGRA (Correção do Efeito Matrioska) ---
  blacklist = ['dist', 'build', '.agents', '__pycache__', '.update_stage', '.update_temp']
  filtered_datas = []
  for data in a.datas:
      # O data[0] contém o caminho de destino no executável ou o caminho de origem
      if not any(f"\\{b}\\" in data[0] or f"/{b}/" in data[0] or data[0].startswith(b) for b in blacklist):
          filtered_datas.append(data)
  a.datas = filtered_datas
  # --------------------------------------------------
  ```
