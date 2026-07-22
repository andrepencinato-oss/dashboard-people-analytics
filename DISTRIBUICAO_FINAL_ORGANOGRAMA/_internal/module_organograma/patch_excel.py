import os, re

html_path = 'ui/headcount.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Clean up corrupted SheetJS script tag if it exists
html = html.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js">', '<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>')

# 2. Remove any injected exportTableToCSV from the script
html = re.sub(r'  function exportTableToCSV\(\) \{.*?document\.body\.removeChild\(link\);\n  \}\n?', '', html, flags=re.DOTALL)
# Also remove any trailing empty script tags or literal \n added by mistake
html = html.replace('  \\n</script>', '</script>')
html = html.replace('</script></script>', '</script>')
html = html.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script></script>', '<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>')

# 3. Change the button onclick to exportTableToExcel()
html = html.replace('onclick="exportTableToCSV()"', 'onclick="exportTableToExcel()"')

# 4. Inject exportTableToExcel function at the end of the script, but before the last </script>
js_func = """  function exportTableToExcel() {
    const tbody = document.getElementById('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    const aoa = [
      ["Centro de custo", "Cadastro", "Colaborador", "Tempo de casa", "Cargo", "Líder Direto", "Salário", "Faltas", "Atestado", "Acidente", "Conta no organograma"]
    ];
    
    rows.forEach(row => {
      const cols = row.querySelectorAll('td');
      if (cols.length < 11) return;
      
      const cc = cols[0].innerText.trim();
      const cad = cols[1].innerText.trim();
      const nome = cols[2].innerText.trim();
      const tempo = cols[3].innerText.trim();
      const cargo = cols[4].innerText.trim();
      
      const selectLider = cols[5].querySelector('select');
      let lider = selectLider ? selectLider.value.trim() : cols[5].innerText.trim();
      if (lider === '— sem resp. —') {
        lider = '';
      }
      
      const salario = cols[6].innerText.trim();
      const faltas = cols[7].innerText.trim() === '-' ? '0' : cols[7].innerText.trim();
      const atestado = cols[8].innerText.trim() === '-' ? '0' : cols[8].innerText.trim();
      const acidente = cols[9].innerText.trim() === '-' ? '0' : cols[9].innerText.trim();
      
      const checkbox = cols[10].querySelector('input[type=checkbox]');
      const conta = checkbox && checkbox.checked ? 'Sim' : 'Não';
      
      aoa.push([cc, cad, nome, tempo, cargo, lider, salario, faltas, atestado, acidente, conta]);
    });
    
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Auditoria");
    
    const date = new Date().toISOString().split('T')[0];
    XLSX.writeFile(wb, `Auditoria_Headcount_${date}.xlsx`);
  }
"""

# Only add it if it doesn't already exist
if 'function exportTableToExcel()' not in html:
    # Inject it before the last </script>
    last_script_index = html.rfind('</script>')
    if last_script_index != -1:
        html = html[:last_script_index] + js_func + html[last_script_index:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
