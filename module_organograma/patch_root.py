import os
import re

file_path = r"d:\Projeto geral\People analytics - GP\module_organograma\organograma-cadastro.html"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Patch the table headers
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

# 2. Add migrateResponsaveis before normalize(s)
if "function migrateResponsaveis()" not in html:
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

# 3. Call migrateResponsaveis on load
html = html.replace(
    "responsaveis = r && r.value ? JSON.parse(r.value) : {};",
    "responsaveis = r && r.value ? JSON.parse(r.value) : {}; migrateResponsaveis();"
)

# 4. Patch renderTable
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

html = re.sub(r"function renderTable\(\).*?(?=function buildEditor)", render_table_js, html, flags=re.DOTALL)


# 5. Patch buildEditor
editor_js = """function buildEditor(cc){
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
  
  function getExistingPJs() {
    const existingPJs = [];
    const seenNames = new Set();
    Object.values(responsaveis).forEach(c => {
       Object.values(c).forEach(roleObj => {
           if(roleObj && roleObj.tipo === 'pj') {
               const n = (roleObj.nome || '').trim();
               if(n && !seenNames.has(n)) {
                   seenNames.add(n);
                   existingPJs.push({ cad: 'PJ-' + n, nome: n, cargo: 'PJ (Pessoa Jurídica)', salario: roleObj.salario, tipo: 'pj' });
               }
           }
       });
    });
    return existingPJs;
  }
  
  function renderDropdown(searchQuery) {
    const normQ = normalize(searchQuery);
    const allOptions = [...getExistingPJs(), ...headcount];
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

html = re.sub(r"function buildEditor\(cc, role\).*?(?=document\.addEventListener\('click')", editor_js, html, flags=re.DOTALL)


# 6. Patch renderStats
html = re.sub(
    r"function renderStats\(\).*?document\.getElementById\('stats'\)\.innerHTML = `.*?`;\n}",
    """function renderStats(){
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
}""",
    html,
    flags=re.DOTALL
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Patch root aplicado com sucesso!")
