import os
import re

ui_dir = r"d:\Projeto geral\People analytics - GP\module_organograma\ui"
path = os.path.join(ui_dir, "index.html")

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

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

new_html = re.sub(r"function buildEditor\(cc, role\).*?(?=document\.addEventListener\('click')", editor_js, html, flags=re.DOTALL)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_html)
print("Done")
