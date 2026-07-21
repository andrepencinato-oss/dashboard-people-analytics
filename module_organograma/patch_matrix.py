import os
import re

file_path = r"ui/organograma.html"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. CSS changes
html = html.replace('.matrix-tree li:only-child { padding-top: 0; }', '')
html = html.replace('.matrix-card { border: 1px solid var(--line); padding: 8px 10px; text-decoration: none; color: var(--ink); font-family: var(--font-body); font-size: 12px; display: inline-block; border-radius: 6px; transition: all 0.2s; background: var(--card); box-shadow: 0 2px 4px rgba(0,0,0,0.02); text-align: left; }',
                    '.matrix-card { border: 1px solid var(--line); padding: 8px 10px; text-decoration: none; color: var(--ink); font-family: var(--font-body); font-size: 12px; display: inline-block; border-radius: 6px; transition: all 0.2s; background: var(--card); box-shadow: 0 2px 4px rgba(0,0,0,0.02); text-align: left; margin-bottom: 24px; }')

# 2. Modify buildMatrixTree
old_build = """    const roleRank = {'Diretor':1, 'Gerente':2, 'Coordenador':3, 'Líder':4};
    const sortedResp = [...resp].sort((a,b) => (roleRank[a.label] || 99) - (roleRank[b.label] || 99));
    
    sortedResp.forEach(r => insertLevel(r));"""

new_build = """    const roleRank = {'Diretor':1, 'Gerente':2, 'Coordenador':3, 'Líder':4};
    
    const standardResp = [];
    const customResp = [];
    
    resp.forEach(r => {
        if (roleRank[r.label]) standardResp.push(r);
        else customResp.push(r);
    });
    
    const sortedResp = [...standardResp].sort((a,b) => roleRank[a.label] - roleRank[b.label]);
    
    let topNodeCreated = null;
    let oldCurrentLevel = currentLevel;

    sortedResp.forEach((r, idx) => {
        insertLevel(r);
        if (idx === 0) topNodeCreated = currentLevel;
    });
    
    // Attach custom roles as staff to the top node (or root if no standard roles)
    const attachNode = topNodeCreated || rootNode;
    if (customResp.length > 0) {
        if (!attachNode.staffList) attachNode.staffList = [];
        customResp.forEach(st => {
            const key = st.cad || st.nome;
            if (!attachNode.staffList.find(x => (x.cad || x.nome) === key)) {
                attachNode.staffList.push(st);
            }
        });
    }"""

html = html.replace(old_build, new_build)

# 3. Modify renderNode
old_render_1 = """          const escapedName = node.name.replace(/'/g, "\\\\'");
          const clickHandler = level ? `handleMenuSelect('${level}', '${escapedName}')` : `handleMenuSelect('Dir', 'all')`;
          
          html += `
              <div class="matrix-card" style="border-top:3px solid var(--blue); min-width: 140px; max-width: 180px; cursor: pointer; transition: 0.2s;" onclick="${clickHandler}" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'" title="Clique para focar na hierarquia deste gestor">
                  <div class="role" style="font-size:9px;">${node.role}</div>
                  <div class="name" style="font-size: 13px;">${node.name}</div>
                  ${node.data ? `<div style="font-family:var(--font-mono);font-size:10px;color:var(--blue);">${fmtMoney(node.data.salario)}</div>` : ''}
              </div>
          `;"""

new_render_1 = """          const escapedName = node.name.replace(/'/g, "\\\\'");
          const clickHandler = level ? `handleMenuSelect('${level}', '${escapedName}')` : `handleMenuSelect('Dir', 'all')`;
          
          let staffHtml = '';
          if (node.staffList && node.staffList.length > 0) {
              node.staffList.forEach((st, idx) => {
                  staffHtml += `
                      <div class="matrix-card staff-card" style="border-top:3px solid var(--copper); min-width: 140px; max-width: 180px; background:#fffcfb; position: absolute; left: 100%; top: ${idx * 80}px; margin-left: 24px; z-index: 10; margin-bottom: 0;">
                          <div class="role" style="font-size:9px; color:var(--copper);">${st.label}</div>
                          <div class="name" style="font-size: 13px;">${st.nome}</div>
                          ${st.salario ? `<div style="font-family:var(--font-mono);font-size:10px;color:var(--copper);">${fmtMoney(st.salario)}</div>` : ''}
                      </div>
                  `;
              });
          }

          html += `
              <div style="position: relative; display: inline-block;">
                  <div class="matrix-card" style="border-top:3px solid var(--blue); min-width: 140px; max-width: 180px; cursor: pointer; transition: 0.2s;" onclick="${clickHandler}" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'" title="Clique para focar na hierarquia deste gestor">
                      <div class="role" style="font-size:9px;">${node.role}</div>
                      <div class="name" style="font-size: 13px;">${node.name}</div>
                      ${node.data ? `<div style="font-family:var(--font-mono);font-size:10px;color:var(--blue);">${fmtMoney(node.data.salario)}</div>` : ''}
                  </div>
                  ${staffHtml}
              </div>
          `;"""

html = html.replace(old_render_1, new_render_1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Patch applied!")
