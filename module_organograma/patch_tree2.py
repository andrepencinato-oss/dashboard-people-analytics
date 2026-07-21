import os
import re

ui_dir = r"d:\Projeto geral\People analytics - GP\module_organograma\ui"

def patch_index():
    path = os.path.join(ui_dir, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    html = re.sub(
        r"<thead>.*?</thead>",
        """<thead>
        <tr>
          <th>Centro de custo</th>
          <th>Diretoria</th>
          <th>Gerência / Coordenação</th>
          <th>Liderança</th>
          <th>Cargos Customizados</th>
        </tr>
      </thead>""",
        html,
        flags=re.DOTALL
    )

    html = re.sub(
        r"function normalize\(s\)",
        """
function migrateResponsaveis() {
  for (let cc in responsaveis) {
    if (!Array.isArray(responsaveis[cc])) {
      let arr = [];
      const roleLabels = {'diretor':'Diretor', 'gerente':'Gerente', 'gerente2':'Gerente', 'coordenador':'Coordenador', 'coordenador2':'Coordenador', 'lider':'Líder', 'lider2':'Líder'};
      for (let k in responsaveis[cc]) {
        let r = responsaveis[cc][k];
        if (r) {
          r.roleKey = k.includes('custom') ? 'custom' : k.replace('2','');
          r.label = roleLabels[k] || r.roleLabel || 'Gestor';
          arr.push(r);
        }
      }
      responsaveis[cc] = arr;
    }
  }
}

function normalize(s)""",
        html
    )

    html = html.replace(
        "responsaveis = r && r.value ? JSON.parse(r.value) : {};",
        "responsaveis = r && r.value ? JSON.parse(r.value) : {}; migrateResponsaveis();"
    )

    render_table_js = """
function renderTable(){
  const filter = normalize(document.getElementById('ccFilter').value);
  const tbody = document.getElementById('tbody');
  tbody.innerHTML='';
  costCenters
    .filter(cc=> !filter || normalize(cc.ccNome).includes(filter) || cc.ccCod.includes(filter))
    .forEach(cc=>{
      const rArr = responsaveis[cc.ccCod] || [];
      const tr=document.createElement('tr');

      const filledCount = rArr.length;
      const tdCc=document.createElement('td');
      tdCc.innerHTML = `
        <div class="cc-cell">
          <div class="strip"><i class="${filledCount>0?'on':''}"></i></div>
          <div>
            <div class="cc-name">${cc.ccNome}</div>
            <div class="cc-sub">${cc.ccCod} · ${cc.count} colab.</div>
          </div>
        </div>`;
      tr.appendChild(tdCc);

      const groups = [
        { keys: ['Diretor'], id: 'dir' },
        { keys: ['Gerente', 'Coordenador'], id: 'ger_coo' },
        { keys: ['Líder'], id: 'lid' },
        { keys: ['Custom'], id: 'custom' }
      ];

      groups.forEach(g => {
        const td=document.createElement('td');
        td.className='slot';
        td.style.verticalAlign = 'top';

        const filtered = rArr.filter(r => g.id === 'custom' ? (!['Diretor','Gerente','Coordenador','Líder'].includes(r.label)) : g.keys.includes(r.label));
        
        filtered.forEach((a, idx) => {
            const chip=document.createElement('div');
            chip.className='chip';
            chip.style.marginBottom = '6px';
            chip.innerHTML = `
              <div class="row1">
                <div class="name">${a.nome}</div>
                ${a.tipo==='pj' ? '<span class="badge">PJ</span>' : ''}
              </div>
              <div class="sub" style="color:var(--blue);font-weight:600;">${a.label} ${a.cargo ? ' - '+a.cargo : ''}</div>
              <div class="sal">${fmtMoney(a.salario)}</div>
              <button class="rm" title="Remover">×</button>
            `;
            chip.querySelector('.rm').onclick=(ev)=>{
              ev.stopPropagation();
              if(!responsaveis[cc.ccCod]) return;
              responsaveis[cc.ccCod] = responsaveis[cc.ccCod].filter(item => item !== a);
              scheduleSave(); renderStats(); renderTable();
            };
            td.appendChild(chip);
        });

        const btn=document.createElement('button');
        btn.className='empty-btn';
        btn.textContent = g.id === 'custom' ? '+ cargo custom' : '+ atribuir';
        btn.onclick=()=>{ 
            let defaultLabel = g.keys[0];
            if(g.id === 'custom') defaultLabel = 'Custom';
            openEditor={ccCod:cc.ccCod, defaultLabel: defaultLabel, query:''}; 
            renderTable(); 
        };
        
        if (openEditor && openEditor.ccCod===cc.ccCod && openEditor.defaultLabel === (g.id==='custom'?'Custom':g.keys[0])) {
            td.appendChild(buildEditor(cc));
        } else {
            td.appendChild(btn);
        }

        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
}
"""
    html = re.sub(r"function renderTable\(\)\{.*?(?=function buildEditor)", render_table_js, html, flags=re.DOTALL)

    editor_js = """
function buildEditor(cc){
  const wrap=document.createElement('div');
  wrap.className='editor';
  
  const customLabelInput = openEditor.defaultLabel === 'Custom' || !['Diretor','Gerente','Coordenador','Líder'].includes(openEditor.defaultLabel) ? 
    `<input type="text" id="customRoleName" placeholder="Nome do Cargo (Ex: Supervisor)" style="border-color:var(--copper); margin-bottom:8px;">` : '';

  if(openEditor.pjMode){
    wrap.innerHTML = `
      <div class="pj-form">
        ${customLabelInput}
        <label>Nome (PJ)</label>
        <input type="text" id="pjNome" placeholder="Nome completo">
        <label>Salário / valor de contrato</label>
        <input type="number" id="pjSalario" placeholder="0,00" step="0.01">
        <div class="actions">
          <button class="ghost" id="pjCancel">Cancelar</button>
          <button class="primary" id="pjConfirm">Confirmar</button>
        </div>
      </div>`;
    setTimeout(()=>document.getElementById('pjNome')?.focus(),0);
    wrap.querySelector('#pjCancel').onclick=()=>{ openEditor=null; renderTable(); };
    wrap.querySelector('#pjConfirm').onclick=()=>{
      const nome=document.getElementById('pjNome').value.trim();
      const salario=parseFloat(document.getElementById('pjSalario').value)||0;
      if(!nome) return;
      let lbl = openEditor.defaultLabel;
      if(wrap.querySelector('#customRoleName')) {
         lbl = wrap.querySelector('#customRoleName').value.trim() || 'Supervisor';
      }
      if(!responsaveis[cc.ccCod]) responsaveis[cc.ccCod]=[];
      responsaveis[cc.ccCod].push({tipo:'pj', nome, salario, cargo:'', label: lbl});
      openEditor=null;
      scheduleSave(); renderStats(); renderTable();
    };
    return wrap;
  }

  const query = openEditor.query || '';
  
  let topOptionsHtml = `
      <div class="pj-option" id="pjOption">
        <span>+ Pessoa jurídica (PJ) — cadastro manual</span>
      </div>
  `;
  if (openEditor.defaultLabel === 'Diretor') {
      topOptionsHtml = `
      <div class="pj-option socio-opt" data-nome="Fernando Costa" style="background:var(--blue-soft);color:var(--blue-800);border-bottom:1px solid var(--line);">
        <span>+ Atribuir Fernando Costa (Diretoria)</span>
      </div>
      <div class="pj-option socio-opt" data-nome="Daniela Costa" style="background:var(--blue-soft);color:var(--blue-800);">
        <span>+ Atribuir Daniela Costa (Diretoria)</span>
      </div>
    `;
  }

  wrap.innerHTML = `
    ${customLabelInput}
    <input type="text" id="editorSearch" placeholder="Buscar no headcount..." value="${query.replace(/"/g,'&quot;')}">
    ${topOptionsHtml}
    <div class="opts" id="optsList"></div>
  `;

  const optsList = wrap.querySelector('#optsList');
  
  function renderDropdown(searchQuery) {
    const normQ = normalize(searchQuery);
    const allOptions = headcount;
    const matches = allOptions
      .filter(e=> !normQ || normalize(e.nome).includes(normQ) || normalize(e.cargo).includes(normQ))
      .slice(0,40);

    optsList.innerHTML = '';
    if(matches.length===0){
      optsList.innerHTML = '<div class="no-res">Nenhum colaborador encontrado</div>';
    } else {
      matches.forEach(e=>{
        const d=document.createElement('div');
        d.className='opt';
        const ccLabel = e.ccNome ? ` · ${e.ccNome}` : '';
        d.innerHTML = `<div class="n">${e.nome}</div><div class="c">${e.cargo}${ccLabel} · ${fmtMoney(e.salario)}</div>`;
        d.onclick=()=>{
          if(!responsaveis[cc.ccCod]) responsaveis[cc.ccCod]=[];
          let lbl = openEditor.defaultLabel;
          if(wrap.querySelector('#customRoleName')) {
             lbl = wrap.querySelector('#customRoleName').value.trim() || 'Supervisor';
          }
          responsaveis[cc.ccCod].push({tipo:'clt', cad:e.cad, nome:e.nome, cargo:e.cargo, salario:e.salario, label: lbl});
          openEditor=null;
          scheduleSave(); renderStats(); renderTable();
        };
        optsList.appendChild(d);
      });
    }
  }

  renderDropdown(query);

  const pjOpt = wrap.querySelector('#pjOption');
  if(pjOpt) pjOpt.onclick=()=>{ openEditor.pjMode=true; renderTable(); };

  wrap.querySelectorAll('.socio-opt').forEach(el => {
    el.onclick = () => {
      const nome = el.dataset.nome;
      if(!responsaveis[cc.ccCod]) responsaveis[cc.ccCod]=[];
      responsaveis[cc.ccCod].push({tipo:'socio', nome: nome, salario: 0, cargo: 'Diretoria', label: 'Diretor'});
      openEditor=null;
      scheduleSave(); renderStats(); renderTable();
    };
  });

  const input = wrap.querySelector('#editorSearch');
  setTimeout(()=>{ input.focus(); input.select(); },0);
  input.oninput=(ev)=>{ 
    openEditor.query=ev.target.value; 
    renderDropdown(ev.target.value); 
  };
  input.onkeydown=(ev)=>{ if(ev.key==='Escape'){ openEditor=null; renderTable(); } };
  wrap.onclick=(ev)=>ev.stopPropagation();

  return wrap;
}
"""
    html = re.sub(r"function buildEditor\(cc, role\).*?(?=document\.addEventListener\('click'\))", editor_js, html, flags=re.DOTALL)
    
    stats_js = """function renderStats(){
  const total=costCenters.length;
  let done=0;
  costCenters.forEach(cc=>{
    const r=responsaveis[cc.ccCod];
    if(r && r.length > 0) done++;
  });
  const el=document.getElementById('stats');
  el.innerHTML = `
    <div class="stat"><div class="n">${total}</div><div class="l">centros de custo</div></div>
    <div class="stat done"><div class="n">${done}</div><div class="l">com gestor</div></div>
    <div class="stat pending"><div class="n">${total-done}</div><div class="l">pendentes</div></div>
  `;
  document.getElementById('sourceNote').textContent = `${headcount.length} colaboradores · ${sourceLabel}`;
}
"""
    html = re.sub(r"function renderStats\(\).*?(?=function assignmentLabel)", stats_js, html, flags=re.DOTALL)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

def patch_headcount():
    path = os.path.join(ui_dir, "headcount.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    
    html = html.replace(
        "if(stResp) responsaveis = JSON.parse(stResp.value);",
        "if(stResp) { responsaveis = JSON.parse(stResp.value); migrateResponsaveis(); }"
    )

    if "function migrateResponsaveis" not in html:
        html = html.replace(
            "function normalize(s)",
            """function migrateResponsaveis() {
  for (let cc in responsaveis) {
    if (!Array.isArray(responsaveis[cc])) {
      let arr = [];
      for (let k in responsaveis[cc]) {
        let r = responsaveis[cc][k];
        if (r) {
           r.label = r.roleLabel || r.label || 'Gestor';
           arr.push(r);
        }
      }
      responsaveis[cc] = arr;
    }
  }
}
function normalize(s)"""
        )
        
    html = re.sub(
        r"function getLiderDireto\(ccCod\).*?\}",
        """function getLiderDireto(ccCod){
            const r = responsaveis[ccCod];
            if(!r || !Array.isArray(r) || r.length === 0) return null;
            return r[r.length - 1]; 
        }""",
        html,
        flags=re.DOTALL
    )
    
    html = re.sub(
        r"function getAllLideres\(\).*?\}",
        """function getAllLideres(){
            const set = new Set();
            Object.values(responsaveis).forEach(rArr => {
                if(Array.isArray(rArr)){
                    rArr.forEach(r => { if(r && r.nome) set.add(r.nome); });
                }
            });
            return Array.from(set).sort();
        }""",
        html,
        flags=re.DOTALL
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

def patch_organograma():
    path = os.path.join(ui_dir, "organograma.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace(
        "if(stResp) responsaveis = JSON.parse(stResp.value);",
        """if(stResp) {
            responsaveis = JSON.parse(stResp.value);
            for (let cc in responsaveis) {
              if (!Array.isArray(responsaveis[cc])) {
                let arr = [];
                const roleLabels = {'diretor':'Diretor', 'gerente':'Gerente', 'gerente2':'Gerente', 'coordenador':'Coordenador', 'coordenador2':'Coordenador', 'lider':'Líder', 'lider2':'Líder'};
                for (let k in responsaveis[cc]) {
                  let r = responsaveis[cc][k];
                  if (r) {
                     r.label = roleLabels[k] || r.roleLabel || 'Gestor';
                     arr.push(r);
                  }
                }
                responsaveis[cc] = arr;
              }
            }
        }"""
    )

    render_tree_js = """
    const resp = responsaveis[ccCod] || [];
    const baseHC = activeHC.filter(e => e.ccCod === ccCod);
    
    if (baseHC.length === 0 && resp.length === 0) return;
    
    let dirName = "Sem Diretoria Atribuída";
    let dirObj = resp.find(r => r.label === 'Diretor');
    if (dirObj && dirObj.nome) {
        dirName = dirObj.nome;
    }
    
    if (!groupsByDir[dirName]) groupsByDir[dirName] = { ccs: [], gestores: {} };
    groupsByDir[dirName].ccs.push({ ccCod, ccName, resp, baseHC });
    
    const processGestor = (r) => {
        if (!r || !r.nome) return;
        const key = r.cad || r.nome;
        if (!groupsByDir[dirName].gestores[key]) {
            let allCcs = [];
            for(let cod in responsaveis) {
                let resArr = responsaveis[cod] || [];
                if (resArr.some(x => x.nome === r.nome)) {
                    let ccNomeObj = costCenters.find(c => c.cod === cod);
                    allCcs.push(ccNomeObj ? ccNomeObj.nome : cod);
                }
            }
            allCcs = [...new Set(allCcs)].sort();
            groupsByDir[dirName].gestores[key] = { ...r, roleTitle: r.label, ccsManaged: allCcs };
        }
        
        if (!allGestores[key]) {
            allGestores[key] = r;
            totalSalarial += (r.salario || 0);
            totalPessoas += 1;
        }
    };
    
    resp.forEach(r => processGestor(r));
  });
"""
    html = re.sub(
        r"const resp = responsaveis\[ccCod\].*?processGestor\(resp\.lider2, 'Líder'\);\s*\}\);",
        render_tree_js,
        html,
        flags=re.DOTALL
    )

    build_matrix_js = """
  ccsToRender.forEach(ccCod => {
    const resp = responsaveis[ccCod] || [];
    if(resp.length === 0) return;
    
    let currentLevel = rootNode;
    
    const insertLevel = (roleData) => {
      if(!roleData) return;
      const key = roleData.cad || ('PJ_' + (roleData.nome || '').replace(/\s+/g, '_').toUpperCase());
      if(!currentLevel.children[key]) {
        currentLevel.children[key] = {
           id: key, role: roleData.label, name: roleData.nome, data: roleData,
           ccList: new Set(), children: {}, parent: currentLevel
        };
      }
      currentLevel = currentLevel.children[key];
    };
    
    const roleRank = {'Diretor':1, 'Gerente':2, 'Coordenador':3, 'Líder':4};
    const sortedResp = [...resp].sort((a,b) => (roleRank[a.label] || 99) - (roleRank[b.label] || 99));
    
    sortedResp.forEach(r => insertLevel(r));
    
    const ccObj = costCenters.find(c => c.cod === ccCod);
"""
    html = re.sub(
        r"ccsToRender\.forEach\(ccCod => \{.*?const ccObj = costCenters\.find\(c => c\.cod === ccCod\);",
        build_matrix_js.replace("\\", "\\\\"),
        html,
        flags=re.DOTALL
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    patch_index()
    patch_headcount()
    patch_organograma()
    print("Patch applied.")
