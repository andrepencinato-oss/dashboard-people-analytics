
let headcount = [];
let globalMetadata = {};
let afastamentosStats = {};
let responsaveis = {};
let possoContar = {};
let costCenters = [];

const fmtMoney = (v) => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0);

async function init() {
  try {
    const resHc = await fetch('/api/headcount');
    headcount = await resHc.json();

        const resMeta = await fetch('/api/metadata');
        if(resMeta.ok) globalMetadata = await resMeta.json();
        
        const resAfStats = await fetch('/api/afastamentos_stats');
        if(resAfStats.ok) afastamentosStats = await resAfStats.json();

    
    // Obter cost centers unicos
    const map = {};
    headcount.forEach(e => {
      if(!e.ccCod) return;
      if(!map[e.ccCod]) map[e.ccCod] = { cod: e.ccCod, nome: e.ccNome };
    });
    costCenters = Object.values(map).sort((a,b)=>a.nome.localeCompare(b.nome));
    
    const sel = document.getElementById('ccSelect');
    const dl = document.getElementById('ccList');
    costCenters.forEach(cc => {
      const opt = document.createElement('option');
      opt.value = cc.nome;
      dl.appendChild(opt);
    });
    
    switchView('matrix');

    // Puxar cadastros e toggles
    const stResp = await window.storage.get('organograma:responsaveis');
    if(stResp) responsaveis = JSON.parse(stResp.value);
    
    const stCont = await window.storage.get('organograma:posso_contar');
    if(stCont) possoContar = JSON.parse(stCont.value);
    
    sel.addEventListener('change', renderTree);
    sel.addEventListener('input', renderTree);
    renderTree();
  } catch(e) {
    document.getElementById('treeView').innerHTML = '<div class="empty-state">Falha ao carregar dados.</div>';
  }
}

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
  
  let allHeadersHtml = '';
  
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
  const allGestores = {}; // cad -> gestor info
  
  ccsToRender.forEach(ccCod => {
    const ccObj = costCenters.find(c => c.cod === ccCod);
    const ccName = ccObj ? ccObj.nome : ccCod;
    const resp = responsaveis[ccCod] || {};
    const baseHC = activeHC.filter(e => e.ccCod === ccCod);
    
    if (baseHC.length === 0 && !resp.diretor && !resp.gerente && !resp.coordenador && !resp.lider) return;
    
    let dirName = "Sem Diretoria Atribuída";
    if (resp.diretor && resp.diretor.nome) {
        dirName = resp.diretor.nome;
    }
    
    if (!groupsByDir[dirName]) groupsByDir[dirName] = { ccs: [], gestores: {} };
    groupsByDir[dirName].ccs.push({ ccCod, ccName, resp, baseHC });
    
    // Process Gestores (Gerente, Coordenador, Lider) -> add them to this Directorate's gestores
    const processGestor = (r, roleTitle) => {
        if (!r || !r.nome) return;
        const key = r.cad || r.nome;
        if (!groupsByDir[dirName].gestores[key]) {
            let allCcs = [];
            for(let cod in responsaveis) {
                let res = responsaveis[cod];
                if ((res.diretor && res.diretor.nome === r.nome) ||
                    (res.gerente && res.gerente.nome === r.nome) ||
                    (res.coordenador && res.coordenador.nome === r.nome) ||
                    (res.lider && res.lider.nome === r.nome)) {
                    
                    let ccNomeObj = costCenters.find(c => c.cod === cod);
                    allCcs.push(ccNomeObj ? ccNomeObj.nome : cod);
                }
            }
            allCcs = [...new Set(allCcs)].sort();
            groupsByDir[dirName].gestores[key] = { ...r, roleTitle, ccsManaged: allCcs };
        }
        
        // Mark for global total (only count once globally)
        if (!allGestores[key]) {
            allGestores[key] = r;
            totalSalarial += (r.salario || 0);
            totalPessoas += 1;
        }
    };
    
    // Also include Director in the Gestores box, so it's clean and unified
    processGestor(resp.diretor, 'Diretor');
    processGestor(resp.gerente, 'Gerente');
    processGestor(resp.coordenador, 'Coordenador');
    processGestor(resp.lider, 'Líder');
  });
  
  let finalHtml = '';
  let allGestoresHtml = '';
  const dirNames = Object.keys(groupsByDir).sort((a,b) => {
      if(a === "Sem Diretoria Atribuída") return 1;
      if(b === "Sem Diretoria Atribuída") return -1;
      return a.localeCompare(b);
  });
  
  dirNames.forEach(dirName => {
      const dirData = groupsByDir[dirName];
      let cardsHtml = '';
      
      dirData.ccs.forEach(cc => {
          let ccTotal = 0; let ccCount = 0;
          
          // NO LONGER SUMMING MANAGER SALARIES IN THE CARD! ONLY BASE HC!
          cc.baseHC.forEach(e => { ccTotal+=e.salario; ccCount++; });
          
          totalSalarial += ccTotal;
          totalPessoas += ccCount;
          
          const roleGroups = {};
          
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
                  
                  
                  const stats = afastamentosStats[e.cad] || { faltas: 0, atestado: 0, acidente: 0 };
                  colabsHtml += `<div class="colab-item">
                      <div class="colab-info"><div class="colab-name">${e.nome}${badgeInfo}</div><div class="colab-tenure">${tenure}</div></div>
                      <div class="colab-stat-col" title="Faltas">${stats.faltas}</div>
                      <div class="colab-stat-col" title="Atestados">${stats.atestado}</div>
                      <div class="colab-stat-col" title="Acidentes">${stats.acidente}</div>
                      <div class="colab-salary" style="text-align:right;">${fmtMoney(e.salario)}</div>
                  </div>`;

              });
              
              const safeId = (cc.ccCod + '_' + cargo).replace(/[^a-zA-Z0-9]/g, '');
const listHeader = `
<div class="colab-list-header" style="display: grid; grid-template-columns: 2fr 75px 75px 75px 90px; gap: 8px; align-items: center; padding: 6px 16px; background: var(--card); border-bottom: 1px solid var(--line); font-size: 10px; font-weight: 700; color: var(--ink-faint); text-transform: uppercase; letter-spacing: 0.5px;">
    <div>Colaborador</div>
    <div style="text-align:center;">Faltas</div>
    <div style="text-align:center;">Atestado</div>
    <div style="text-align:center;">Acidente</div>
    <div style="text-align:right;">Salário</div>
</div>`;
const hiddenDataHtml = `<div id="data-${safeId}" style="display:none;">${listHeader}${colabsHtml}</div>`;
rolesHtml += `<div class="role-group" id="rg-${safeId}" onclick="showColabs('${safeId}', '${cargo.replace(/'/g, "\\'")}', ${colabs.length})"><div class="role-summary"><span class="role-name">${cargo}</span><span class="role-count">${colabs.length}</span></div>${hiddenDataHtml}</div>`;
          });
          
          cardsHtml += `<div class="cc-card"><div class="cc-card-header"><div class="cc-card-title-group"><div class="cc-card-eyebrow">Centro de Custo</div><h3 class="cc-card-title">${cc.ccName}</h3></div><div class="cc-card-stats"><div class="cc-card-hc">${ccCount} pessoas</div><div class="cc-card-cost">${fmtMoney(ccTotal)}</div></div></div><div class="cc-card-body">${rolesHtml || '<div style="padding:16px;font-size:13px;color:var(--ink-faint);text-align:center;">Nenhum colaborador base atribuído</div>'}</div></div>`;
      });
      
      // Build Gestores HTML for this Directorate
      let gestoresHtml = '';
      
      // Define a custom sort order for roles
      const roleWeight = { 'Diretor': 1, 'Gerente': 2, 'Coordenador': 3, 'Líder': 4 };
      const gestoresSorted = Object.values(dirData.gestores).sort((a,b) => {
          return (roleWeight[a.roleTitle] || 99) - (roleWeight[b.roleTitle] || 99);
      });
      
      gestoresSorted.forEach(g => {
          if (g.roleTitle === 'Diretor') return;
          // Truncate long list of CCs
          let ccsStr = g.ccsManaged.join(', ');
          if(ccsStr.length > 50) ccsStr = ccsStr.substring(0, 47) + '...';
          
          gestoresHtml += `
            <div class="gestor-pill">
                <div class="gestor-pill-header">
                    <span class="gestor-pill-role">${g.roleTitle}: <span class="gestor-pill-name">${g.nome}</span></span>
                    <span class="gestor-pill-cost">${fmtMoney(g.salario)}</span>
                </div>
                <div class="gestor-pill-ccs">Cuida de: ${ccsStr}</div>
            </div>
          `;
      });
      allGestoresHtml += gestoresHtml;
      
      allHeadersHtml += `
          <div class="dir-header-container" style="margin-bottom: 24px;">
              <h2 class="dir-header" style="margin: 0; padding-bottom: 8px; border-bottom: 2px solid var(--line-soft); color: var(--blue); font-family: var(--font-display); font-size: 20px; font-weight: 600;">Diretor: ${dirName}</h2>
          </div>
      `;
      
      finalHtml += `
        <div class="dir-section">
            <div class="cc-grid">
                ${cardsHtml}
            </div>
        </div>
      `;
  });
  
  if (Object.keys(groupsByDir).length === 0) {
    treeView.innerHTML = '<div class="empty-state">Nenhum dado encontrado para esta visão.</div>';
  } else {
    treeView.innerHTML = `
${allHeadersHtml}
<div class="master-detail-layout" style="display:flex; gap:16px; align-items:flex-start; justify-content:flex-start;">
    <div class="master-column" style="flex: 0 0 360px;">
        ${finalHtml}
    </div>
    <div class="detail-column" id="detailPanel" style="display:block; flex: 1; min-width:350px; background:var(--card); border:1px solid var(--line); border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.05); padding:0; position:sticky; top:24px; max-height:calc(100vh - 48px); overflow-y:auto;">
        <div class="detail-header" style="padding:16px 24px; border-bottom:1px solid var(--line); position:sticky; top:0; background:var(--card); z-index:1; border-radius: 8px 8px 0 0;">
            <div style="font-size:11px; color:var(--copper); font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Colaboradores no Cargo</div>
            <h3 id="detailTitle" style="margin:0; color:var(--ink); font-size:16px;">Selecione um cargo à esquerda</h3>
        </div>
        <div class="detail-body" id="detailBody" style="padding:0;">
            <div style="padding:60px 40px; text-align:center; color:var(--ink-faint); font-size:14px;">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:16px; opacity:0.5;">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
                <br>
                Clique em um cargo no painel à esquerda para visualizar a lista de colaboradores que atuam nele.
            </div>
        </div>
    </div>
</div>
`;
}
  
  document.getElementById('kpiTotal').innerText = fmtMoney(totalSalarial);
  document.getElementById('kpiCount').innerText = totalPessoas;
  document.getElementById('kpiAvg').innerText = fmtMoney(totalPessoas > 0 ? totalSalarial / totalPessoas : 0);
  
  const topGestores = document.getElementById('topHeaderGestores');
  if (topGestores) {
      if (allGestoresHtml.trim() !== '') {
          topGestores.innerHTML = '<div style="font-size: 11px; font-weight: 600; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 0.5px; margin-right: 4px;">Linha de Gestão:</div>' + allGestoresHtml;
          topGestores.style.display = currentView === 'matrix' ? 'none' : 'flex';
      } else {
          topGestores.style.display = 'none';
      }
  }
  
  buildMatrixTree(ccsToRender);
}

function openCCView(ccName) {
  document.getElementById('ccSelect').value = ccName;
  switchView('cc');
  renderTree(); // re-render to apply filter
}

function voltarParaMatriz() {
  document.getElementById('ccSelect').value = '';
  switchView('matrix');
  renderTree(); // re-render without CC filter
}

let currentView = 'matrix';

function switchView(view) {
  currentView = view;
  const headerSubtitle = document.getElementById('headerSubtitle');
  if (headerSubtitle) {
      
        if(view === 'matrix') {
            headerSubtitle.innerHTML = 'Árvore Matricial';
        } else {
            const p = globalMetadata.periodo_afastamento || '';
            headerSubtitle.innerHTML = `Visão por Centro de Custo <div style="font-size:12px; color:var(--ink-faint); margin-top:4px; font-weight: 400; text-transform:none;">Período base: ${p.replace('.CSV', '')}</div>`;
        }

  }
  document.getElementById('btnViewCC').className = view === 'cc' ? 'active' : '';
  document.getElementById('btnViewMatrix').className = view === 'matrix' ? 'active' : '';
  
  document.getElementById('btnVoltarTopo').style.display = view === 'cc' ? 'block' : 'none';
  const topGestores = document.getElementById('topHeaderGestores');
  if (topGestores) {
      if (view === 'matrix' || topGestores.innerHTML.trim() === '') {
          topGestores.style.display = 'none';
      } else {
          topGestores.style.display = 'flex';
      }
  }
  document.getElementById('controlsMatrix').style.display = view === 'matrix' ? 'flex' : 'none';
  document.getElementById('treeView').style.display = view === 'cc' ? 'block' : 'none';
  document.getElementById('matrixView').style.display = view === 'matrix' ? 'block' : 'none';
  const kpiBoard = document.querySelector('.kpi-board');
  if (kpiBoard) kpiBoard.style.display = view === 'matrix' ? 'flex' : 'none';
}

function buildMatrixTree(ccsToRender) {
  const matrixView = document.getElementById('matrixView');
  
  // Build hierarchy tree
  const rootNode = { id: 'root', role: 'Presidente', name: 'Roberto Pereira Da Costa', data: null, children: {}, ccList: new Set() };
  
  ccsToRender.forEach(ccCod => {
    const resp = responsaveis[ccCod];
    if(!resp) return;
    
    const dir = resp.diretor;
    const ger = resp.gerente;
    const coo = resp.coordenador;
    const lid = resp.lider;
    
    // Ignorar CCs sem gestor ALGUM e sem base (a menos que a visão permita)
    if(!dir && !ger && !coo && !lid) return;
    
    let currentLevel = rootNode;
    
    const insertLevel = (roleData, roleTitle) => {
      if(!roleData) return;
      const key = roleData.cad || ('PJ_' + (roleData.nome || '').replace(/\s+/g, '_').toUpperCase());
      if(!currentLevel.children[key]) {
        currentLevel.children[key] = {
           id: key, role: roleTitle, name: roleData.nome, data: roleData,
           ccList: new Set(), children: {}, parent: currentLevel
};
      }
      currentLevel = currentLevel.children[key];
    };
    
    if(dir) insertLevel(dir, 'Diretor');
    if(ger) insertLevel(ger, 'Gerente');
    if(coo) insertLevel(coo, 'Coordenador');
    if(lid) insertLevel(lid, 'Líder');
    
    // Adicionar o Centro de Custo como nó folha abaixo do último gestor
    const ccObj = costCenters.find(c => c.cod === ccCod);
    const ccName = ccObj ? ccObj.nome : ccCod;
    
    const baseHC = headcount.filter(e => e.ccCod === ccCod && possoContar[e.cad] !== false);
    const roleGroups = {};
    baseHC.forEach(e => {
        const c = e.cargo || 'Sem Função';
        if(!roleGroups[c]) roleGroups[c] = [];
        roleGroups[c].push(e);
    });
    
    currentLevel.children[`CC_${ccCod}`] = {
        id: `CC_${ccCod}`,
        role: 'Centro de Custo',
        name: ccName,
        isCC: true,
        roles: roleGroups,
        children: {}
    };
  });
  
    const renderNode = (node, pathNodes, targetNode, hasPassedTarget = false) => {
      let html = '<li>';
      
      if(node.isCC) {
          let rolesHtml = '';
          Object.keys(node.roles).sort().forEach(roleName => {
              const count = node.roles[roleName].length;
              rolesHtml += `<div style="font-size:10px; color:var(--ink-soft); border-top:1px solid var(--line); padding-top:4px; margin-top:4px; display:flex; justify-content:space-between; align-items:center;">
                  <span style="white-space:normal;text-align:left;line-height:1.2;">${roleName}</span>
                  <span style="background:var(--paper); padding:2px 6px; border-radius:10px; font-weight:600; margin-left:8px;">${count}</span>
              </div>`;
          });
          html += `
              <div class="matrix-card" style="border-top:3px solid var(--copper); min-width: 170px; max-width: 220px; cursor: pointer; transition: 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.08);" onclick="openCCView('${node.name}')" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                  <div class="role" style="color:var(--copper); font-size:9px;">${node.role}</div>
                  <div class="name" style="white-space:normal; line-height:1.2; font-size: 13px;">${node.name}</div>
                  <div style="margin-top: 6px;">${rolesHtml}</div>
              </div>
          `;
      } else {
          let level = '';
          if(node.role === 'Diretor') level = 'Dir';
          else if(node.role === 'Gerente') level = 'Ger';
          else if(node.role === 'Coordenador') level = 'Coo';
          else if(node.role === 'Líder') level = 'Lid';
          
          const escapedName = node.name.replace(/'/g, "\\'");
          const clickHandler = level ? `handleMenuSelect('${level}', '${escapedName}')` : `handleMenuSelect('Dir', 'all')`;
          
          html += `
              <div class="matrix-card" style="border-top:3px solid var(--blue); min-width: 140px; max-width: 180px; cursor: pointer; transition: 0.2s;" onclick="${clickHandler}" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'" title="Clique para focar na hierarquia deste gestor">
                  <div class="role" style="font-size:9px;">${node.role}</div>
                  <div class="name" style="font-size: 13px;">${node.name}</div>
                  ${node.data ? `<div style="font-family:var(--font-mono);font-size:10px;color:var(--blue);">${fmtMoney(node.data.salario)}</div>` : ''}
              </div>
          `;
      }

      const childrenKeys = Object.keys(node.children);
      if(childrenKeys.length > 0) {
          let childrenToRender = childrenKeys.map(k => node.children[k]);
          
          if (!hasPassedTarget && node !== targetNode) {
              childrenToRender = childrenToRender.filter(child => pathNodes && pathNodes.has(child));
          }
          
          if (childrenToRender.length > 0) {
              html += '<ul>';
              childrenToRender.sort((a,b) => a.name.localeCompare(b.name)).forEach(child => {
                  const passed = hasPassedTarget || child === targetNode;
                  html += renderNode(child, pathNodes, targetNode, passed);
              });
              html += '</ul>';
          }
      }
      html += '</li>';
      return html;
  };
  
  const getSelectedKey = (inputVal, dict) => {
      if(!inputVal) return 'all';
      const lowVal = inputVal.trim().toLowerCase();
      let found = Object.keys(dict).find(k => dict[k].name.toLowerCase() === lowVal);
      if(found) return found;
      found = Object.keys(dict).find(k => dict[k].name.toLowerCase().includes(lowVal));
      return found || 'all';
  };

  const rawDir = document.getElementById('matrixFilterDir').value;
  const rawGer = document.getElementById('matrixFilterGer').value;
  const rawCoo = document.getElementById('matrixFilterCoo').value;
  const rawLid = document.getElementById('matrixFilterLid').value;
  
  const getDescendantsByRole = (node, roleTitle) => {
      let results = {};
      const traverse = (n) => {
          Object.keys(n.children).forEach(k => {
              const child = n.children[k];
              if(!child.isCC) {
                  if(child.role === roleTitle) results[k] = child;
                  traverse(child);
              }
          });
      };
      traverse(node);
      return results;
  };

  const allDirs = getDescendantsByRole(rootNode, 'Diretor');
  const allGers = getDescendantsByRole(rootNode, 'Gerente');
  const allCoos = getDescendantsByRole(rootNode, 'Coordenador');
  const allLids = getDescendantsByRole(rootNode, 'Líder');
  
  // Auto-fill upwards logic
  let initialTarget = rootNode;
  if (rawLid !== 'all' && rawLid) {
      initialTarget = Object.values(allLids).find(n => n.name === rawLid) || rootNode;
  } else if (rawCoo !== 'all' && rawCoo) {
      initialTarget = Object.values(allCoos).find(n => n.name === rawCoo) || rootNode;
  } else if (rawGer !== 'all' && rawGer) {
      initialTarget = Object.values(allGers).find(n => n.name === rawGer) || rootNode;
  } else if (rawDir !== 'all' && rawDir) {
      initialTarget = Object.values(allDirs).find(n => n.name === rawDir) || rootNode;
  }
  
  let temp = initialTarget;
  while(temp && temp !== rootNode) {
      if(temp.role === 'Líder') document.getElementById('matrixFilterLid').value = temp.name;
      if(temp.role === 'Coordenador') document.getElementById('matrixFilterCoo').value = temp.name;
      if(temp.role === 'Gerente') document.getElementById('matrixFilterGer').value = temp.name;
      if(temp.role === 'Diretor') document.getElementById('matrixFilterDir').value = temp.name;
      temp = temp.parent;
  }
  
  const newRawDir = document.getElementById('matrixFilterDir').value;
  const newRawGer = document.getElementById('matrixFilterGer').value;
  const newRawCoo = document.getElementById('matrixFilterCoo').value;
  const newRawLid = document.getElementById('matrixFilterLid').value;

  const valDir = getSelectedKey(newRawDir, allDirs);
    
  let dictGers = (valDir !== 'all' && allDirs[valDir]) ? getDescendantsByRole(allDirs[valDir], 'Gerente') : allGers;
  const valGer = getSelectedKey(newRawGer, dictGers);
    
  let dictCoos = (valGer !== 'all' && dictGers[valGer]) ? getDescendantsByRole(dictGers[valGer], 'Coordenador') : 
                 ((valDir !== 'all' && allDirs[valDir]) ? getDescendantsByRole(allDirs[valDir], 'Coordenador') : allCoos);
  const valCoo = getSelectedKey(newRawCoo, dictCoos);
    
  let dictLids = (valCoo !== 'all' && dictCoos[valCoo]) ? getDescendantsByRole(dictCoos[valCoo], 'Líder') :
                 ((valGer !== 'all' && dictGers[valGer]) ? getDescendantsByRole(dictGers[valGer], 'Líder') :
                 ((valDir !== 'all' && allDirs[valDir]) ? getDescendantsByRole(allDirs[valDir], 'Líder') : allLids));
  const valLid = getSelectedKey(newRawLid, dictLids);
    
  let targetNode = rootNode;
  if(valLid !== 'all' && dictLids[valLid]) targetNode = dictLids[valLid];
  else if(valCoo !== 'all' && dictCoos[valCoo]) targetNode = dictCoos[valCoo];
  else if(valGer !== 'all' && dictGers[valGer]) targetNode = dictGers[valGer];
  else if(valDir !== 'all' && allDirs[valDir]) targetNode = allDirs[valDir];
  
    // Compute path from target to root
  let pathNodes = new Set();
  let curr = targetNode;
  while(curr) {
      pathNodes.add(curr);
      curr = curr.parent;
  }
  
  // Calculate KPIs for targetNode subtree
  let kpiPessoas = 0;
  let kpiSalario = 0;
  let uniqueGestores = new Set();
  const collectTargetStats = (node) => {
      if(node.isCC) {
          Object.values(node.roles).forEach(arr => {
              arr.forEach(emp => {
                  kpiPessoas++;
                  kpiSalario += (emp.salario || 0);
              });
          });
      } else {
          if(node.data && node.data.cad) {
              uniqueGestores.add(node.data);
          }
          if(node.children) Object.values(node.children).forEach(collectTargetStats);
      }
  };
  collectTargetStats(targetNode);
  uniqueGestores.forEach(g => {
      kpiPessoas++;
      kpiSalario += (g.salario || 0);
  });
  
  if (document.getElementById('kpiCount')) document.getElementById('kpiCount').innerText = kpiPessoas;
  if (document.getElementById('kpiTotal')) document.getElementById('kpiTotal').innerText = fmtMoney(kpiSalario);
  if (document.getElementById('kpiAvg')) document.getElementById('kpiAvg').innerText = fmtMoney(kpiPessoas > 0 ? kpiSalario / kpiPessoas : 0);

  let finalHtml = '<ul>';
  
  if (targetNode === rootNode) {
      const dirKeys = Object.keys(allDirs);
      if(dirKeys.length === 0) {
        matrixView.innerHTML = '<div class="empty-state">Nenhum gestor encontrado para esta visão.</div>';
        return;
      }
      finalHtml += renderNode(rootNode, pathNodes, targetNode, false);
  } else {
      finalHtml += renderNode(rootNode, pathNodes, targetNode, false);
  }
  
  finalHtml += '</ul>';
  
  matrixView.innerHTML = finalHtml;
}

function handleMenuSelect(level, val) {
  document.getElementById('matrixFilter' + level).value = val;
  
  if(level === 'Dir') {
     document.getElementById('matrixFilterGer').value = 'all';
     document.getElementById('matrixFilterCoo').value = 'all';
     document.getElementById('matrixFilterLid').value = 'all';
  } else if(level === 'Ger') {
     document.getElementById('matrixFilterCoo').value = 'all';
     document.getElementById('matrixFilterLid').value = 'all';
  } else if(level === 'Coo') {
     document.getElementById('matrixFilterLid').value = 'all';
  }
  
  
  updateMatrixFilters(level.toLowerCase());
}

function updateMatrixFilters(level) {
    const dir = document.getElementById('matrixFilterDir');
    const ger = document.getElementById('matrixFilterGer');
    const coo = document.getElementById('matrixFilterCoo');
    const lid = document.getElementById('matrixFilterLid');
    
    if(level === 'dir') { ger.value = ''; coo.value = ''; lid.value = ''; }
    if(level === 'ger') { coo.value = ''; lid.value = ''; }
    if(level === 'coo') { lid.value = ''; }
    
    renderTree();
}

init();

document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState === 'visible') {
    const stResp = await window.storage.get('organograma:responsaveis');
    if (stResp && stResp.value) responsaveis = JSON.parse(stResp.value);
    
    const stCont = await window.storage.get('organograma:posso_contar');
    if (stCont && stCont.value) possoContar = JSON.parse(stCont.value);
    
    renderTree();
  }
});

window.showColabs = function(id, title, count) {
    const dPanel = document.getElementById('detailPanel');
    const dBody = document.getElementById('detailBody');
    const dTitle = document.getElementById('detailTitle');
    const dataDiv = document.getElementById('data-' + id);
    
    if (dPanel && dBody && dTitle && dataDiv) {
        dPanel.style.display = 'block';
        dTitle.innerText = `${title} (${count})`;
        dBody.innerHTML = dataDiv.innerHTML;
        
        document.querySelectorAll('.role-group').forEach(el => el.classList.remove('active'));
        const rg = document.getElementById('rg-' + id);
        if (rg) rg.classList.add('active');
    }
};
