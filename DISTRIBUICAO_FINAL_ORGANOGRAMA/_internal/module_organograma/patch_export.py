import os

html_path = 'ui/headcount.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

btn_target = """      <button class="export-btn" id="btnPlanoAcao" style="background: var(--blue-soft); border-color: var(--blue); color: var(--blue-800); box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: background 0.2s;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
        Plano de Ação
      </button>"""

btn_replacement = """      <button class="export-btn" id="btnExportCSV" style="background: var(--blue-soft); border-color: var(--blue); color: var(--blue-800); box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: background 0.2s;" onclick="exportTableToCSV()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
        Exportar Tabela
      </button>
      <button class="export-btn" id="btnPlanoAcao" style="background: var(--blue-soft); border-color: var(--blue); color: var(--blue-800); box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: background 0.2s;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
        Plano de Ação
      </button>"""

html = html.replace(btn_target, btn_replacement)

js_target = """  // Initialization"""

js_replacement = """  function exportTableToCSV() {
    const tbody = document.getElementById('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    let csvContent = "Centro de custo;Cadastro;Colaborador;Tempo de casa;Cargo;Líder Direto;Salário;Faltas;Atestado;Acidente;Conta no organograma\\n";
    
    rows.forEach(row => {
      const cols = row.querySelectorAll('td');
      if (cols.length < 11) return;
      
      const cc = cols[0].innerText.trim();
      const cad = cols[1].innerText.trim();
      const nome = cols[2].innerText.trim();
      const tempo = cols[3].innerText.trim();
      const cargo = cols[4].innerText.trim();
      
      const selectLider = cols[5].querySelector('select');
      const lider = selectLider ? selectLider.value.trim() : cols[5].innerText.trim();
      if (lider === '— sem resp. —') {
        lider = '';
      }
      
      const salario = cols[6].innerText.trim();
      
      const faltas = cols[7].innerText.trim() === '-' ? '0' : cols[7].innerText.trim();
      const atestado = cols[8].innerText.trim() === '-' ? '0' : cols[8].innerText.trim();
      const acidente = cols[9].innerText.trim() === '-' ? '0' : cols[9].innerText.trim();
      
      const checkbox = cols[10].querySelector('input[type=checkbox]');
      const conta = checkbox && checkbox.checked ? 'Sim' : 'Não';
      
      const rowData = [cc, cad, nome, tempo, cargo, lider === '— sem resp. —' ? '' : lider, salario, faltas, atestado, acidente, conta];
      const escapedRow = rowData.map(d => {
        let f = (d || '').replace(/"/g, '""');
        if (f.search(/("|,|;|\\n)/g) >= 0) {
          f = `"${f}"`;
        }
        return f;
      }).join(';');
      
      csvContent += escapedRow + "\\n";
    });
    
    const bom = "\\uFEFF";
    const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const date = new Date().toISOString().split('T')[0];
    link.setAttribute("href", url);
    link.setAttribute("download", `Auditoria_Headcount_${date}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Initialization"""

if js_target in html:
    html = html.replace(js_target, js_replacement)
else:
    # Append to the end before </script>
    html = html.replace('</script>', js_replacement.replace('// Initialization', '') + '\\n</script>')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
