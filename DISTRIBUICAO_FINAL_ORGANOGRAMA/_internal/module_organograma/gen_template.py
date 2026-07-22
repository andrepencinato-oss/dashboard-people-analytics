import urllib.request
import json
import os
import re

BASE_URL = "http://127.0.0.1:5009/api"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_data(endpoint):
    try:
        req = urllib.request.urlopen(f"{BASE_URL}/{endpoint}", timeout=2)
        return json.loads(req.read().decode('utf-8'))
    except Exception as e:
        return None

def get_local_data(filename):
    path = os.path.join(BASE_DIR, 'data', filename)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                try:
                    return json.loads(content)
                except:
                    return content
        except Exception as e:
            print(f"[gen_template] Erro ao ler local {filename}: {e}")
    return None

def generate_template():
    print("[gen_template] Gerando Template_Sugestao_Excel.html...")
    headcount = get_data("headcount")
    if headcount is None:
        headcount = get_local_data("headcount.json") or []
    if not isinstance(headcount, list):
        headcount = []

    metadata = get_data("metadata")
    if metadata is None:
        metadata = get_local_data("metadata.json") or {}

    afast = get_data("afastamentos_stats")
    if afast is None:
        afast = get_local_data("afastamentos_stats.json") or {}

    resp_raw = get_data("storage/get/organograma:responsaveis")
    if resp_raw is None:
        resp_raw = get_local_data("organograma_responsaveis.json")
    
    if isinstance(resp_raw, dict) and 'value' in resp_raw:
        try: responsaveis_dict = json.loads(resp_raw['value'])
        except: responsaveis_dict = {}
    elif isinstance(resp_raw, str):
        try: responsaveis_dict = json.loads(resp_raw)
        except: responsaveis_dict = {}
    elif isinstance(resp_raw, dict):
        responsaveis_dict = resp_raw
    else:
        responsaveis_dict = {}

    posso_contar_raw = get_data("storage/get/organograma:posso_contar")
    if posso_contar_raw is None:
        posso_contar_raw = get_local_data("organograma_contagem.json")

    if isinstance(posso_contar_raw, dict) and 'value' in posso_contar_raw:
        try: posso_contar_dict = json.loads(posso_contar_raw['value'])
        except: posso_contar_dict = {}
    elif isinstance(posso_contar_raw, str):
        try: posso_contar_dict = json.loads(posso_contar_raw)
        except: posso_contar_dict = {}
    elif isinstance(posso_contar_raw, dict):
        posso_contar_dict = posso_contar_raw
    else:
        posso_contar_dict = {}

    # Oculta colaboradores e força salários a 0
    for p in headcount:
        p['nome'] = 'Colaborador Oculto'
        p['salario'] = 0
        if 'salario_fmt' in p: p['salario_fmt'] = 'R$ 0,00'

    # Zerar salários de não-gestores/não-PJ em responsaveis
    if isinstance(responsaveis_dict, dict):
        for cc, arr in responsaveis_dict.items():
            if isinstance(arr, list):
                for r in arr:
                    if isinstance(r, dict):
                        lbl = str(r.get('label') or '').lower()
                        tipo = str(r.get('tipo') or '').lower()
                        cad = str(r.get('cad') or '').upper()
                        is_boss = 'diretor' in lbl or 'gerente' in lbl or tipo == 'pj' or cad.startswith('PJ-') or 'pj' in lbl
                        if not is_boss:
                            r['salario'] = 0
        
    html_path = os.path.join(BASE_DIR, 'ui', 'organograma.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
        
    js_injection = f"""
    let headcount = {json.dumps(headcount)};
    let globalMetadata = {json.dumps(metadata)};
    let afastamentosStats = {json.dumps(afast)};
    let responsaveis = {json.dumps(responsaveis_dict)};
    let possoContar = {json.dumps(posso_contar_dict)};
    let costCenters = [];
    let totalSalarialPJ = 0;
    """

    # Replace fetch lines with hardcoded JSON
    html = html.replace("let headcount = [];", "")
    html = html.replace("let globalMetadata = {};", "")
    html = html.replace("let afastamentosStats = {};", "")
    html = html.replace("let responsaveis = {};", "")
    html = html.replace("let possoContar = {};", "")
    html = html.replace("let costCenters = [];", "")
    html = html.replace("let totalSalarialPJ = 0;", js_injection)
    
    html = html.replace("const resHc = await fetch('/api/headcount');", "")
    html = html.replace("headcount = await resHc.json();", "")
    html = html.replace("const resMeta = await fetch('/api/metadata');", "")
    html = html.replace("if(resMeta.ok) globalMetadata = await resMeta.json();", "")
    html = html.replace("const resAfStats = await fetch('/api/afastamentos_stats');", "")
    html = html.replace("if(resAfStats.ok) afastamentosStats = await resAfStats.json();", "")
    
    html = html.replace("const stResp = await window.storage.get('organograma:responsaveis');\n    if(stResp) {\n            responsaveis = JSON.parse(stResp.value);", f"const stResp = true;\n    if(stResp) {{")
    html = html.replace("const stCont = await window.storage.get('organograma:posso_contar');\n    if(stCont) possoContar = JSON.parse(stCont.value);", f"")

    # Insert title block for Sugestão de Organograma
    sugestao_title_html = """
    <div class="sugestao-header" style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid var(--line);">
      <h1 style="font-family: var(--font-display); font-size: 26px; font-weight: 600; color: var(--blue); margin: 0 0 6px 0;">Sugestão de Organograma</h1>
      <p style="margin: 0; color: var(--ink-soft); font-size: 14px;">Preencha a quantidade sugerida por cargo diretamente na árvore para planejar o quadro e exportar em Excel.</p>
    </div>
    """
    html = html.replace('<div class="header">', sugestao_title_html + '<div class="header" style="display:none !important;">')
    html = html.replace('.wrap { max-width: 1400px; margin: 0 auto; padding: 28px 24px 90px; }', '.wrap { max-width: 1400px; margin: 0 auto; padding: 24px 24px 90px; }')

    # REMOVE KPI Board completely
    html = html.replace('<div class="kpi-board">', '<div class="kpi-board-removed" style="display:none !important; visibility:hidden;">')
    html = html.replace("if (kpiBoard) kpiBoard.style.display = view === 'matrix' ? 'flex' : 'none';", "")

    # Hide salaries in matrix nodes
    html = html.replace("${showCardSalary(node.data, node.role) ? `<div style=\"font-family:var(--font-mono);font-size:10px;color:var(--blue); margin-bottom: 2px;\">Vencimentos: ${fmtMoney(node.data.salario)}</div>` : ''}", "")
    html = html.replace("${checkIsPJ(st) && st.salario ? `<div style=\"font-family:var(--font-mono);font-size:10px;color:var(--copper);\">${fmtMoney(st.salario)}</div>` : ''}", "")
    
    # Disable opening CC Cards (sem card)
    html = html.replace("onclick=\"openCCView('${node.name}')\"", "")
    html = html.replace("cursor: pointer;", "")
    
    # Replace count bubble with input field (empty placeholder) - NO LOCALSTORAGE INLINE
    target_span = '<span style="background:var(--paper); padding:2px 6px; border-radius:10px; font-weight:600; margin-left:8px;">${count}</span>'
    new_input = '<input type="number" class="hc-sugestao" data-cc="${node.name}" data-cargo="${roleName}" placeholder="" style="width:40px; padding:2px; font-size:12px; border:1px solid var(--line); border-radius:4px; text-align:center; background:#fff; font-family:var(--font-body);">'
    html = html.replace(target_span, new_input)
    
    # Replace Manager Names with Input Field (Except for Diretor/Presidente)
    manager_name_html = '<div class="name" style="font-size: 13px;">${node.name}</div>'
    manager_input_logic = '''${(node.role === 'Diretor' || node.role === 'Presidente' || node.role === 'Diretoria') ? 
        `<div class="name" style="font-size: 13px;">${node.name}</div>` : 
        `<input type="number" class="hc-sugestao" data-cc="Hierarquia" data-cargo="${node.role}" placeholder="Qtd" style="width:60px; padding:4px; margin-top:4px; font-size:12px; border:1px solid var(--line); border-radius:4px; text-align:center; background:#fff; font-family:var(--font-body);">`
    }'''
    html = html.replace(manager_name_html, manager_input_logic)

    # Replace Staff Names with Input Field
    staff_name_html = '<div class="name" style="font-size: 13px;">${st.nome}</div>'
    staff_input_logic = '''<input type="number" class="hc-sugestao" data-cc="Hierarquia" data-cargo="${st.label}" placeholder="Qtd" style="width:60px; padding:4px; margin-top:4px; font-size:12px; border:1px solid var(--line); border-radius:4px; text-align:center; background:#fff; font-family:var(--font-body);">'''
    html = html.replace(staff_name_html, staff_input_logic)
    
    # Add SheetJS, LocalStorage loader and Export logic
    export_ui = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <button onclick="exportarSugestoesExcel()" style="position:fixed; bottom:24px; right:24px; background:var(--blue); color:#fff; padding:12px 24px; border-radius:8px; border:none; cursor:pointer; font-weight:600; font-family:var(--font-body); font-size:14px; box-shadow:0 4px 12px rgba(0,0,0,0.15); z-index:9999;">Salvar Sugestões (Excel)</button>
    <script>
    // Listener to save inputs to localStorage immediately as they are typed
    document.addEventListener('input', function(e) {
        if (e.target && e.target.classList.contains('hc-sugestao')) {
            const key = 'sugestao_' + e.target.getAttribute('data-cc') + '_' + e.target.getAttribute('data-cargo');
            localStorage.setItem(key, e.target.value);
        }
    });
    
    // Observer to load values into inputs when they are rendered
    const observer = new MutationObserver(() => {
        document.querySelectorAll('.hc-sugestao').forEach(inp => {
            if (!inp.dataset.loaded) {
                const key = 'sugestao_' + inp.getAttribute('data-cc') + '_' + inp.getAttribute('data-cargo');
                const saved = localStorage.getItem(key);
                if (saved !== null) inp.value = saved;
                inp.dataset.loaded = 'true';
            }
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });

    function exportarSugestoesExcel() {
        let inputs = document.querySelectorAll('.hc-sugestao');
        let data = [];
        
        inputs.forEach(inp => {
            let val = inp.value;
            if (val && val.trim() !== "") {
                let cc = inp.getAttribute('data-cc');
                let cargo = inp.getAttribute('data-cargo');
                data.push({
                    "Centro de Custo": cc,
                    "Cargo": cargo,
                    "Quantidade Sugerida": parseInt(val)
                });
            }
        });
        
        if (data.length === 0) {
            alert("Preencha ao menos uma quantidade sugerida.");
            return;
        }
        
        const worksheet = XLSX.utils.json_to_sheet(data);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Sugestoes");
        XLSX.writeFile(workbook, "Sugestao_Quadro_Organograma.xlsx");
    }
    
    </script>
    """
    html = html.replace("</body>", export_ui + "\n</body>")
    
    # Disable view toggles since we only want the matrix tree
    html = html.replace('<div class="view-toggles" style="display:none;">', '<div class="view-toggles" style="display:none !important;">')

    out_path = os.path.join(BASE_DIR, 'Template_Sugestao_Excel.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    print("[gen_template] Template gerado com sucesso em Template_Sugestao_Excel.html!")

if __name__ == '__main__':
    generate_template()
