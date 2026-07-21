import os

file_path = r"ui/organograma.html"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Fix buildMatrixTree to attach to Gerente
old_build = """    let topNodeCreated = null;
    let oldCurrentLevel = currentLevel;

    sortedResp.forEach((r, idx) => {
        insertLevel(r);
        if (idx === 0) topNodeCreated = currentLevel;
    });
    
    // Attach custom roles as staff to the top node (or root if no standard roles)
    const attachNode = topNodeCreated || rootNode;"""

new_build = """    let topNodeCreated = null;
    let gerenteNode = null;

    sortedResp.forEach((r, idx) => {
        insertLevel(r);
        if (idx === 0) topNodeCreated = currentLevel;
        if (r.label === 'Gerente') gerenteNode = currentLevel;
    });
    
    // Attach custom roles as staff to the Gerente node (or fallback to topNode)
    const attachNode = gerenteNode || topNodeCreated || rootNode;"""

html = html.replace(old_build, new_build)

# 2. Fix renderNode to avoid absolute positioning overlap
old_render = """          let staffHtml = '';
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

new_render = """          if (node.staffList && node.staffList.length > 0) {
              let cards = '';
              node.staffList.forEach((st) => {
                  cards += `
                      <div class="matrix-card staff-card" style="border-top:3px solid var(--copper); min-width: 140px; max-width: 180px; background:#fffcfb; margin-bottom: 8px;">
                          <div class="role" style="font-size:9px; color:var(--copper);">${st.label}</div>
                          <div class="name" style="font-size: 13px;">${st.nome}</div>
                          ${st.salario ? `<div style="font-family:var(--font-mono);font-size:10px;color:var(--copper);">${fmtMoney(st.salario)}</div>` : ''}
                      </div>
                  `;
              });
              
              html += `
                  <div style="display: flex; align-items: flex-start; justify-content: center;">
                      <div style="margin-right: 24px; flex-shrink: 0; display: flex; flex-direction: column; visibility: hidden; pointer-events: none;">
                          ${cards}
                      </div>
                      
                      <div style="display: flex; flex-direction: column; align-items: center; position: relative;">
                          <div class="matrix-card" style="border-top:3px solid var(--blue); min-width: 140px; max-width: 180px; cursor: pointer; transition: 0.2s;" onclick="${clickHandler}" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'" title="Clique para focar na hierarquia deste gestor">
                              <div class="role" style="font-size:9px;">${node.role}</div>
                              <div class="name" style="font-size: 13px;">${node.name}</div>
                              ${node.data ? `<div style="font-family:var(--font-mono);font-size:10px;color:var(--blue);">${fmtMoney(node.data.salario)}</div>` : ''}
                          </div>
                      </div>
                      
                      <div style="margin-left: 24px; flex-shrink: 0; display: flex; flex-direction: column;">
                          ${cards}
                      </div>
                  </div>
              `;
          } else {
              html += `
                  <div class="matrix-card" style="border-top:3px solid var(--blue); min-width: 140px; max-width: 180px; cursor: pointer; transition: 0.2s;" onclick="${clickHandler}" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'" title="Clique para focar na hierarquia deste gestor">
                      <div class="role" style="font-size:9px;">${node.role}</div>
                      <div class="name" style="font-size: 13px;">${node.name}</div>
                      ${node.data ? `<div style="font-family:var(--font-mono);font-size:10px;color:var(--blue);">${fmtMoney(node.data.salario)}</div>` : ''}
                  </div>
              `;
          }"""

html = html.replace(old_render, new_render)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Patch applied!")
