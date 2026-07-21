import os
import sys
import threading
import time
import json
from flask import Flask, send_from_directory, jsonify, request, make_response

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
core_dir = os.path.join(root_dir, 'core')

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from module_organograma.data_processor import (
    fetch_organograma_data,
    sync_configs_to_cloud,
    process_csv_files,
)

app = Flask(__name__, template_folder='ui', static_folder='ui')
PORT = 5009

# ─── versão ────────────────────────────────────────────────
def _read_version():
    try:
        vpath = os.path.join(core_dir, 'version.json')
        if os.path.exists(vpath):
            with open(vpath, 'r', encoding='utf-8') as f:
                return json.load(f).get('version', '—')
    except Exception:
        pass
    return '—'

APP_VERSION = _read_version()

# ─── API ────────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    return jsonify({"status": "DRIVE CONECTADO E PRONTO PARA DESENVOLVIMENTO", "ready": True, "version": _read_version()})

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/headcount')
def api_headcount():
    try:
        path = os.path.join(current_dir, 'data', 'headcount.json')
        if not os.path.exists(path):
            return jsonify([])
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"[Organograma] Erro ao ler headcount.json: {e}")
        return jsonify([])

@app.route('/api/afastamentos')
def api_afastamentos():
    try:
        path = os.path.join(current_dir, 'data', 'afastamentos.json')
        if not os.path.exists(path):
            return jsonify([])
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"[Organograma] Erro ao ler afastamentos.json: {e}")
        return jsonify([])

@app.route('/api/storage/get/<path:key>')
def api_storage_get(key):
    safe_key = key.replace(':', '_').replace('/', '_')
    path = os.path.join(current_dir, 'data', f"{safe_key}.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify({"value": f.read()})
    return jsonify({"value": None})

@app.route('/api/storage/set/<path:key>', methods=['POST'])
def api_storage_set(key):
    safe_key = key.replace(':', '_').replace('/', '_')
    os.makedirs(os.path.join(current_dir, 'data'), exist_ok=True)
    path = os.path.join(current_dir, 'data', f"{safe_key}.json")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(request.json.get('value', ''))
    # Async cloud sync so the UI response is instant
    threading.Thread(target=_safe_cloud_sync, daemon=True).start()
    return jsonify({"success": True})

def _safe_cloud_sync():
    try:
        sync_configs_to_cloud()
    except Exception as e:
        print(f"[Organograma] Cloud sync em background falhou: {e}")

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Endpoint acionado pelo botão 'Atualizar Informações'. Baixa CSVs do Drive e reprocessa."""
    def _do_refresh():
        try:
            print("[Organograma] Refresh manual iniciado pelo usuário...")
            fetch_organograma_data()
            print("[Organograma] Refresh manual concluído.")
        except Exception as e:
            print(f"[Organograma] Erro no refresh manual: {e}")

    t = threading.Thread(target=_do_refresh, daemon=True)
    t.start()
    t.join(timeout=60)   # aguarda até 60 s para responder
    return jsonify({"success": True, "message": "Dados atualizados com sucesso."})

@app.route('/api/metadata')
def api_metadata():
    try:
        path = os.path.join(current_dir, 'data', 'metadata.json')
        if not os.path.exists(path):
            return jsonify({})
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"[Organograma] Erro ao ler metadata.json: {e}")
        return jsonify({})

@app.route('/api/afastamentos_stats')
def api_afastamentos_stats():
    try:
        path = os.path.join(current_dir, 'data', 'afastamentos_stats.json')
        if not os.path.exists(path):
            return jsonify({})
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"[Organograma] Erro ao ler afastamentos_stats.json: {e}")
        return jsonify({})

@app.route('/api/version')
def api_version():
    return jsonify({"version": _read_version()})

# ─── UI injectors ───────────────────────────────────────────
def inject_navigation(html):
    nav = f"""
    <style>
      body {{ padding-left: 64px !important; transition: padding-left 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; }}
      body:has(.master-sidebar.open) {{ padding-left: 280px !important; }}
      .master-sidebar {{
        position: fixed; top: 0; left: 0; bottom: 0; width: 64px;
        background: #182333; color: white; z-index: 10000;
        transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex; flex-direction: column; overflow: hidden;
        box-shadow: 2px 0 12px rgba(0,0,0,0.15); font-family: 'IBM Plex Sans', sans-serif;
        white-space: nowrap;
      }}
      .master-sidebar.open {{ width: 280px; }}
      
      .ms-header {{
        height: 64px; display: flex; align-items: center; padding: 0 20px;
        border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer;
      }}
      .ms-header svg {{ flex-shrink: 0; width: 24px; height: 24px; color: #fff; opacity: 0.7; }}
      .ms-brand {{ 
        font-family: 'Space Grotesk', sans-serif; font-weight: 600; color: #fff; 
        font-size: 16px; margin-left: 20px; opacity: 0; transition: opacity 0.2s;
      }}
      .master-sidebar.open .ms-brand {{ opacity: 1; transition-delay: 0.1s;}}
      
      .ms-nav {{ display: flex; flex-direction: column; padding: 16px 0; flex: 1; }}
      .ms-item {{
        display: flex; align-items: center; padding: 12px 20px;
        color: #8A96A3; text-decoration: none; font-weight: 500; font-size: 14.5px;
        transition: color 0.2s, background 0.2s; border-left: 3px solid transparent;
      }}
      .ms-item:hover {{ color: #FFFFFF; background: rgba(255,255,255,0.05); }}
      .ms-item.active {{ color: #FFFFFF; background: rgba(36,80,124,0.4); border-left-color: #5C95C6; }}
      .ms-item svg {{ flex-shrink: 0; width: 22px; height: 22px; margin-right: 22px; margin-left: 1px; }}
      .ms-label {{ opacity: 0; transition: opacity 0.2s; }}
      .master-sidebar.open .ms-label {{ opacity: 1; transition-delay: 0.1s; }}

      /* Version badge at bottom */
      .ms-version {{
        padding: 12px 20px; border-top: 1px solid rgba(255,255,255,0.05);
        font-size: 10.5px; color: rgba(255,255,255,0.28); font-family: 'IBM Plex Mono', monospace;
        white-space: nowrap; overflow: hidden;
        opacity: 0; transition: opacity 0.2s;
      }}
      .master-sidebar.open .ms-version {{ opacity: 1; transition-delay: 0.1s; }}

      /* Refresh button */
      .ms-refresh {{
        display: flex; align-items: center; margin: 8px 12px; padding: 9px 12px;
        background: rgba(36,80,124,0.3); border: 1px solid rgba(92,149,198,0.25);
        border-radius: 8px; color: #8A96A3; cursor: pointer; gap: 10px;
        font-size: 13px; font-family: 'IBM Plex Sans', sans-serif; font-weight: 500;
        transition: background 0.2s, color 0.2s, opacity 0.2s;
        opacity: 0; pointer-events: none;
        white-space: nowrap;
      }}
      .master-sidebar.open .ms-refresh {{ opacity: 1; pointer-events: auto; transition-delay: 0.1s; }}
      .ms-refresh:hover {{ background: rgba(36,80,124,0.6); color: #fff; }}
      .ms-refresh:disabled {{ opacity: 0.4 !important; cursor: not-allowed; }}
      .ms-refresh svg {{ flex-shrink: 0; width: 16px; height: 16px; }}
      @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
      .ms-refresh.loading svg {{ animation: spin 1s linear infinite; }}
    </style>
    <div class="master-sidebar" id="masterSidebar">
      <div class="ms-header" id="msHeader">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        <span class="ms-brand">Organograma Tool</span>
      </div>
      <div class="ms-nav">
        <a href="/" class="ms-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
          <span class="ms-label">Cadastro de Responsáveis</span>
        </a>
        <a href="/headcount" class="ms-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
          <span class="ms-label">Headcount / Auditoria</span>
        </a>
        <a href="/arvore" class="ms-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
          <span class="ms-label">Visão Organograma</span>
        </a>
      </div>
      <button class="ms-refresh" id="msRefreshBtn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        <span class="ms-refresh-label">Atualizar Informações</span>
      </button>
      <div class="ms-version">v{_read_version()} · Organograma Tool</div>
    </div>
    <script>
      document.querySelectorAll('.ms-nav .ms-item').forEach(link => {{
        if (link.getAttribute('href') === window.location.pathname) link.classList.add('active');
      }});
      document.getElementById('msHeader').addEventListener('click', () => {{
        document.getElementById('masterSidebar').classList.toggle('open');
      }});

      // Refresh button handler
      document.getElementById('msRefreshBtn').addEventListener('click', async function() {{
        const btn = this;
        const label = btn.querySelector('.ms-refresh-label');
        btn.disabled = true;
        btn.classList.add('loading');
        label.textContent = 'Atualizando...';
        try {{
          const res = await fetch('/api/refresh', {{ method: 'POST' }});
          const data = await res.json();
          label.textContent = data.success ? 'Atualizado!' : 'Erro';
          setTimeout(() => {{
            label.textContent = 'Atualizar Informações';
            btn.disabled = false;
            btn.classList.remove('loading');
            // Reload page to show fresh data
            window.location.reload();
          }}, 1800);
        }} catch(e) {{
          label.textContent = 'Erro de conexão';
          setTimeout(() => {{
            label.textContent = 'Atualizar Informações';
            btn.disabled = false;
            btn.classList.remove('loading');
          }}, 2000);
        }}
      }});
    </script>
    """
    return html.replace('<body>', '<body>' + nav)

def inject_storage(html):
    storage_script = """
    <script>
    window.storage = {
        get: async function(key, fallback) {
            try {
                const res = await fetch('/api/storage/get/' + encodeURIComponent(key));
                const data = await res.json();
                return data.value ? {value: data.value} : null;
            } catch(e) { return null; }
        },
        set: async function(key, value, sync) {
            try {
                const res = await fetch('/api/storage/set/' + encodeURIComponent(key), {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({value: value})
                });
                return await res.json();
            } catch(e) { return false; }
        }
    };
    </script>
    """
    if '</body>' in html:
        return html.replace('</body>', storage_script + '</body>')
    return html + storage_script

def _render_page(html_file):
    path = os.path.join(current_dir, 'ui', html_file)
    if not os.path.exists(path):
        return f"Arquivo UI não encontrado: {html_file}"
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = inject_navigation(html)
    html = inject_storage(html)
    response = make_response(html)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    return _render_page('index.html')

@app.route('/headcount')
def route_headcount():
    return _render_page('headcount.html')

@app.route('/arvore')
def route_arvore():
    return _render_page('organograma.html')

# ─── background autopilot ───────────────────────────────────
def vigia_autopilot():
    print("[Organograma Vigia] Iniciando thread Autopilot...")
    while True:
        try:
            print("[Organograma Vigia] Sincronizando dados com o Google Drive (Autopilot)...")
            fetch_organograma_data()
        except Exception as e:
            print(f"[Organograma Vigia] Erro no autopilot: {e}")
        time.sleep(300)

def main():
    print(f"[Organograma] Bootloader v{_read_version()} — Iniciando módulo Organograma.")
    vigia_thread = threading.Thread(target=vigia_autopilot, daemon=True)
    vigia_thread.start()
    try:
        app.run(port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Organograma] Erro ao iniciar servidor na porta {PORT}: {e}")


if __name__ == '__main__':
    main()
