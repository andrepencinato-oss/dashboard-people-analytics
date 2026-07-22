import os
with open('app_organograma.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_item = """
        <a href="/sugestao" class="ms-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
          <span class="ms-label">Sugestão de Organograma</span>
        </a>"""

code = code.replace('<span class="ms-label">Visão Organograma</span>\n        </a>', '<span class="ms-label">Visão Organograma</span>\n        </a>' + new_item)

new_route = """
@app.route('/sugestao')
def route_sugestao():
    import os
    from flask import make_response
    path = os.path.join(current_dir, 'Template_Sugestao_Excel.html')
    if not os.path.exists(path):
        return "Arquivo de Sugestão não gerado ainda."
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = inject_navigation(html)
    response = make_response(html)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
"""

code = code.replace("    return _render_page('organograma.html')", "    return _render_page('organograma.html')\n" + new_route)

with open('app_organograma.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Updated successfully')
