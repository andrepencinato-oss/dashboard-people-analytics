import re

with open('ui/organograma.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add CSS
new_css = """
  /* New Grid & Cards CSS */
  .dir-section { margin-bottom: 48px; }
  .dir-header { font-family: var(--font-display); font-size: 20px; font-weight: 600; color: var(--blue); margin-bottom: 16px; border-bottom: 2px solid var(--line-soft); padding-bottom: 8px; }
  .cc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .cc-card { background: var(--card); border: 1px solid var(--line); border-top: 3px solid var(--copper); border-radius: 8px; box-shadow: 0 4px 12px rgba(24, 35, 51, 0.04); overflow: hidden; }
  .cc-card-header { padding: 16px; border-bottom: 1px solid var(--line-soft); }
  .cc-card-eyebrow { font-size: 10px; font-weight: 600; color: var(--copper); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .cc-card-title { font-family: var(--font-display); font-size: 18px; font-weight: 600; color: var(--ink); margin: 0; }
  .cc-card-body { padding: 0; }
  .role-group { border-bottom: 1px solid var(--line-soft); }
  .role-group:last-child { border-bottom: none; }
  .role-summary { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; cursor: pointer; transition: background 0.2s; user-select: none; outline: none; }
  .role-summary::-webkit-details-marker { display: none; }
  .role-summary:hover { background: var(--paper); }
  .role-name { font-size: 13px; font-weight: 500; color: var(--ink-soft); }
  .role-count { background: var(--paper); color: var(--ink-soft); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; }
  .role-details { padding: 0; display: none; background: #FAFBFC; border-top: 1px dashed var(--line); }
  .role-group[open] .role-details { display: block; }
  .role-group[open] .role-summary { background: var(--blue-soft); border-bottom: 1px solid transparent; }
  .role-group[open] .role-name { color: var(--blue-800); font-weight: 600; }
  .role-group[open] .role-count { background: var(--card); color: var(--blue-800); }
  .colab-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; border-bottom: 1px solid var(--line-soft); }
  .colab-item:last-child { border-bottom: none; }
  .colab-info { flex: 1; }
  .colab-name { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 2px; }
  .colab-tenure { font-size: 11px; color: var(--ink-faint); }
  .colab-salary { font-family: var(--font-mono); font-size: 12px; font-weight: 500; color: var(--ink-soft); }
"""

# insert CSS right before </style>
html = html.replace('</style>', new_css + '\n</style>')

# Replace renderTree completely
new_render_tree = """
function calcularTempoDeCasa(admissao) {
  if(!admissao) return 'Data não informada';
  const parts = admissao.split('/');
  if(parts.length !== 3) return admissao;
  const dataAdmissao = new Date(parts[2], parts[1] - 1, parts[0]);
  if(isNaN(dataAdmissao)) return admissao;
  const hoje = new Date();
  
  let anos = hoje.getFullYear() - dataAdmissao.getFullYear();
  let meses = hoje.getMonth() - dataAdmissao.getMonth();
  
  if (meses < 0 || (meses === 0 && hoje.getDate() < dataAdmissao.getDate())) {
      anos--;
      meses += 12;
  }
  if (hoje.getDate() < dataAdmissao.getDate()) {
      meses--;
      if (meses < 0) {
          meses = 11;
      }
  }
  
  let str = [];
  if (anos > 0) str.push(`${anos} ano${anos > 1 ? 's' : ''}`);
  if (meses > 0) str.push(`${meses} mês${meses > 1 ? 'es' : ''}`);
  if (anos === 0 && meses === 0) return 'Menos de 1 mês';
  
  return str.join(' e ');
}

function renderTree() {
  const filterInput = document.getElementById('ccSelect').value.trim().toLowerCase();
  const treeView = document.getElementById('treeView');
  treeView.innerHTML = '';
  
  let activeHC = headcount.filter(e => possoContar[e.cad] !== false);
  
  let ccsToRender = [];
  if(filterInput === '') {
    ccsToRender = costCenters.map(c=>c.cod);
  } else {
    const matchedCCs = costCenters.filter(c => c.nome.toLowerCase().includes(filterInput));
    ccsToRender = matchedCCs.map(c=>c.cod);
  }

  if(filterInput !== '') {
    activeHC = activeHC.filter(e => ccsToRender.includes(e.ccCod));
  }

  let totalSalarial = 0;
  let totalPessoas = 0;
  
  const groupsByDir = {};
  
  ccsToRender.forEach(ccCod => {
    const ccObj = costCenters.find(c => c.cod === ccCod);
    const ccName = ccObj ? ccObj.nome : ccCod;
    const resp = responsaveis[ccCod] || {};
    const baseHC = activeHC.filter(e => e.ccCod === ccCod);
    
    if (baseHC.length === 0 && !resp.diretor && !resp.gerente && !resp.coordenador && !resp.lider) return; // ignora CCs vazios
    
    let dirName = "Sem Diretoria Atribuída";
    if (resp.diretor && resp.diretor.nome) {
        dirName = resp.diretor.nome;
    }
    
    if (!groupsByDir[dirName]) groupsByDir[dirName] = [];
    groupsByDir[dirName].push({ ccCod, ccName, resp, baseHC });
  });
  
  let finalHtml = '';
  const dirNames = Object.keys(groupsByDir).sort((a,b) => {
      if(a === "Sem Diretoria Atribuída") return 1;
      if(b === "Sem Diretoria Atribuída") return -1;
      return a.localeCompare(b);
  });
  
  dirNames.forEach(dirName => {
      const ccs = groupsByDir[dirName];
      let cardsHtml = '';
      
      ccs.forEach(cc => {
          let ccTotal = 0; let ccCount = 0;
          const addCust = (r) => { if(r){ ccTotal+=r.salario; ccCount++; } };
          addCust(cc.resp.diretor); addCust(cc.resp.gerente); addCust(cc.resp.coordenador); addCust(cc.resp.lider);
          cc.baseHC.forEach(e => { ccTotal+=e.salario; ccCount++; });
          
          totalSalarial += ccTotal;
          totalPessoas += ccCount;
          
          const roleGroups = {};
          
          const addGestor = (r, label) => {
              if(r && r.nome) {
                  if (r.tipo === 'clt' && cc.baseHC.find(e => e.cad === r.cad)) return;
                  if(!roleGroups[label]) roleGroups[label] = [];
                  roleGroups[label].push({nome: r.nome, salario: r.salario, admissao: '', tipo: r.tipo});
              }
          };
          
          addGestor(cc.resp.lider, 'Líder (Atribuído)');
          addGestor(cc.resp.coordenador, 'Coordenador (Atribuído)');
          addGestor(cc.resp.gerente, 'Gerente (Atribuído)');
          
          cc.baseHC.forEach(e => {
            const cargo = e.cargo || 'Sem Função';
            if(!roleGroups[cargo]) roleGroups[cargo] = [];
            roleGroups[cargo].push(e);
          });
          
          let rolesHtml = '';
          Object.keys(roleGroups).sort().forEach(cargo => {
              const colabs = roleGroups[cargo];
              let colabsHtml = '';
              colabs.forEach(e => {
                  const isManager = e.tipo === 'pj' || e.tipo === 'socio';
                  const badgeInfo = e.tipo === 'pj' ? ' (PJ)' : (e.tipo === 'socio' ? ' (Diretoria)' : '');
                  const tenure = e.admissao ? calcularTempoDeCasa(e.admissao) : (isManager ? 'Contrato/Sócio' : 'Data não informada');
                  
                  colabsHtml += `
                    <div class="colab-item">
                        <div class="colab-info">
                            <div class="colab-name">${e.nome}${badgeInfo}</div>
                            <div class="colab-tenure">${tenure}</div>
                        </div>
                        <div class="colab-salary">${fmtMoney(e.salario)}</div>
                    </div>
                  `;
              });
              
              rolesHtml += `
                  <details class="role-group">
                      <summary class="role-summary">
                          <span class="role-name">${cargo}</span>
                          <span class="role-count">${colabs.length}</span>
                      </summary>
                      <div class="role-details">
                          ${colabsHtml}
                      </div>
                  </details>
              `;
          });
          
          cardsHtml += `
              <div class="cc-card">
                  <div class="cc-card-header">
                      <div class="cc-card-eyebrow">Centro de Custo</div>
                      <h3 class="cc-card-title">${cc.ccName}</h3>
                  </div>
                  <div class="cc-card-body">
                      ${rolesHtml || '<div style="padding:16px;font-size:13px;color:var(--ink-faint);text-align:center;">Nenhum colaborador atribuído</div>'}
                  </div>
              </div>
          `;
      });
      
      finalHtml += `
          <div class="dir-section">
              <div class="dir-header">Diretor: ${dirName}</div>
              <div class="cc-grid">
                  ${cardsHtml}
              </div>
          </div>
      `;
  });
  
  if (Object.keys(groupsByDir).length === 0) {
      treeView.innerHTML = '<div class="empty-state">Nenhum dado encontrado para esta visão.</div>';
  } else {
      treeView.innerHTML = finalHtml;
  }
  
  document.getElementById('kpiTotal').innerText = fmtMoney(totalSalarial);
  document.getElementById('kpiCount').innerText = totalPessoas;
  document.getElementById('kpiAvg').innerText = fmtMoney(totalPessoas > 0 ? totalSalarial / totalPessoas : 0);
}
"""

# Use regex to replace the old renderTree block
# Need to capture from `function renderTree() {` to just before `function buildMatrixTree() {`
pattern = re.compile(r'function renderTree\(\) \{.*?(?=function buildMatrixTree\(\) \{)', re.DOTALL)
html = pattern.sub(new_render_tree + '\n\n', html)

with open('ui/organograma.html', 'w', encoding='utf-8') as f:
    f.write(html)
