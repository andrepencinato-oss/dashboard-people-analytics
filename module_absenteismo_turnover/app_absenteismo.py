import os
import time
from flask import Flask, send_from_directory, jsonify
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
from data_processor import get_dashboard_data

app = Flask(__name__, template_folder='.', static_folder='.')

# Em memória para cache estrito (Singleton)
CACHE = None

@app.route('/api/absenteismo/resumo')
def api_resumo():
    global CACHE
    t0 = time.time()
    is_cached = True
    
    if CACHE is None:
        is_cached = False
        try:
            CACHE = get_dashboard_data()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    resp = jsonify({
        "kpis": CACHE.get("kpis"),
        "top_colaboradores": CACHE.get("top_colaboradores"),
        "situacoes": CACHE.get("situacoes"),
        "sync_info": CACHE.get("sync_info")
    })
    
    t1 = time.time()
    status = "[RAM CACHE]" if is_cached else "[COLD START]"
    print(f"[PERF] {status} /api/absenteismo/resumo respondida em {(t1-t0)*1000:.2f} ms.")
    return resp

@app.route('/api/absenteismo/evolucao')
def api_evolucao():
    global CACHE
    t0 = time.time()
    is_cached = True
    
    if CACHE is None:
        is_cached = False
        try:
            CACHE = get_dashboard_data()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    resp = jsonify({
        "evolucao": CACHE.get("evolucao"),
        "yoy": CACHE.get("yoy"),
        "sync_info": CACHE.get("sync_info")
    })
    
    t1 = time.time()
    status = "[RAM CACHE]" if is_cached else "[COLD START]"
    print(f"[PERF] {status} /api/absenteismo/evolucao respondida em {(t1-t0)*1000:.2f} ms.")
    return resp

@app.route('/api/absenteismo/auditoria')
def api_auditoria():
    global CACHE
    t0 = time.time()
    is_cached = True
    
    if CACHE is None:
        is_cached = False
        try:
            CACHE = get_dashboard_data()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    resp = jsonify({
        "auditoria": CACHE.get("auditoria"),
        "sync_info": CACHE.get("sync_info"),
        "kpis": CACHE.get("kpis")
    })
    
    t1 = time.time()
    status = "[RAM CACHE]" if is_cached else "[COLD START]"
    print(f"[PERF] {status} /api/absenteismo/auditoria respondida em {(t1-t0)*1000:.2f} ms.")
    return resp

@app.route('/api/absenteismo/sync')
def api_sync():
    global CACHE
    t0 = time.time()
    try:
        CACHE = get_dashboard_data()
        t1 = time.time()
        print(f"[PERF] [SYNC/DRIVE] Sincronização forçada executada em {(t1-t0):.3f} s.")
        return jsonify({"status": "success", "message": "Dados sincronizados."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('.', 'dashboard_absenteismo.html')

def main():
    global CACHE
    print("[INIT] Realizando pré-carregamento dos dados em RAM (Cold Start Inicial)...")
    try:
        CACHE = get_dashboard_data()
        print("[INIT] Cache Populado com Sucesso. Servidor Pronto.")
    except Exception as e:
        print(f"[INIT ERROR] Falha ao pre-carregar: {e}")
        
    # use_reloader=False é vital para impedir que o Flask mate o cache do Pandas no start e ao receber requisições em background
    app.run(port=5006, debug=True, use_reloader=False)

if __name__ == '__main__':
    main()
