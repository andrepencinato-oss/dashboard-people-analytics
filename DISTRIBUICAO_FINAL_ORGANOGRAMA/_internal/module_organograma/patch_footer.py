import os
import glob

footer_html = """
<footer style="text-align: center; padding: 20px; font-size: 12px; color: var(--ink-faint); font-family: var(--font-mono);">
  v2.0.7 &middot; Organograma Tool
</footer>
"""

ui_files = glob.glob('ui/*.html')
for html_path in ui_files:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Check if footer already exists to avoid duplication
    if 'v2.0.7 &middot; Organograma Tool' not in html:
        # Append before </body>
        html = html.replace('</body>', footer_html + '\n</body>')
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
print("Footer applied to:", ui_files)
