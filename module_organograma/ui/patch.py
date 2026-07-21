import os
import re

ui_dir = os.path.dirname(os.path.abspath(__file__))

def patch_index():
    path = os.path.join(ui_dir, 'index.html')
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remover botão de upload
    html = re.sub(r'<label class="upload-btn".*?</label>', '', html, flags=re.DOTALL)
    
    # Substituir a variável hardcoded window.__HEADCOUNT__ (pode ter milhares de linhas)
    # A maneira mais segura de remover é procurar pela atribuição window.__HEADCOUNT__ = [...]
    html = re.sub(r'window\.__HEADCOUNT__\s*=\s*\[.*?\];', '', html, flags=re.DOTALL)

    # Remover o event listener do csvUpload
    html = re.sub(r'document\.getElementById\(\'csvUpload\'\)\.addEventListener\([^}]+\}\);', '', html, flags=re.DOTALL)
    
    # Substituir a func init()
    new_init = """
/* ---------- Utils Automáticos (Extrai CCs do Headcount) ---------- */
function buildCostCenters(hc) {
  const map = {};
  hc.forEach(e => {
    if(!e.ccCod) return;
    if(!map[e.ccCod]) map[e.ccCod] = { ccCod: e.ccCod, ccNome: e.ccNome, count: 0 };
    map[e.ccCod].count++;
  });
  return Object.values(map).sort((a,b) => a.ccNome.localeCompare(b.ccNome));
}

/* ---------- Init ---------- */
async function init(){
  try {
    const res = await fetch('/api/headcount');
    headcount = await res.json();
    costCenters = buildCostCenters(headcount);
    sourceLabel = 'Google Drive Automático';
    
    await loadResponsaveis();
    renderStats();
    renderTable();
  } catch (err) {
    console.error('Falha ao inicializar dados', err);
    alert('Erro ao carregar os dados do backend.');
  }
}
init();
"""
    html = re.sub(r'async function init\(\)\{.*\}[\r\n\s]*init\(\);', new_init, html, flags=re.DOTALL)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)


def patch_headcount():
    path = os.path.join(ui_dir, 'headcount.html')
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remover botão de upload CSV
    html = re.sub(r'<label class="upload-btn".*?</label>', '', html, flags=re.DOTALL)
    html = re.sub(r'document\.getElementById\(\'csvUpload\'\)\.addEventListener\([^}]+\}\);', '', html, flags=re.DOTALL)
    
    # Ajustar init para buscar da API de headcount e afastamentos
    new_init = """
/* ---------- Init Fetch (Drive Automático) ---------- */
async function init(){
  try {
    const res = await fetch('/api/headcount');
    headcountData = await res.json();
    
    const resAf = await fetch('/api/afastamentos');
    const afData = await resAf.json();
    
    // Opcional: injetar dados da api_afastamentos se o html original não fizer isso
    window.__AFASTAMENTOS__ = afData;
    
    // (Opcional) carregar estado dos "Posso contar?"
    const stored = await window.storage.get('organograma:posso_contar');
    if(stored) possoContarState = JSON.parse(stored.value);
    
    renderAuditoria();
  } catch (err) {
    console.error('Falha ao inicializar dados', err);
  }
}
init();

// Hook simples para salvar estado de 'Posso contar?'
window.savePossoContar = function() {
    window.storage.set('organograma:posso_contar', JSON.stringify(possoContarState));
};
"""
    html = re.sub(r'async function init\(\)\{.*\}[\r\n\s]*init\(\);', new_init, html, flags=re.DOTALL)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

patch_index()
patch_headcount()
print("HTMLs adaptados com sucesso.")
