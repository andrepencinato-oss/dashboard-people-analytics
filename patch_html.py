import os

with open('module_frequencia_diaria/Auditoria de falta.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find("document.getElementById('csvFileInput').addEventListener('change', function(e) {")
end_idx = content.find("// Iniciar a p", start_idx) 
    
if start_idx != -1 and end_idx != -1:
    replacement = '''document.getElementById('btnSyncDrive').addEventListener('click', function(e) {
    const btn = document.getElementById('btnSyncDrive');
    const icon = document.getElementById('syncIcon');
    const text = document.getElementById('syncText');
    
    icon.classList.add('animate-spin');
    text.textContent = 'Sincronizando...';
    btn.style.pointerEvents = 'none';
    
    fetch('/api/sync-drive')
      .then(r => r.json())
      .then(data => {
          if(data.status === 'sucesso') {
              window.location.reload();
          } else {
              alert('Erro na sincronização: ' + data.detalhe);
              icon.classList.remove('animate-spin');
              text.textContent = 'Sincronizar Dados do Drive';
              btn.style.pointerEvents = 'auto';
          }
      })
      .catch(err => {
          alert('Erro de conexão: ' + err);
          icon.classList.remove('animate-spin');
          text.textContent = 'Sincronizar Dados do Drive';
          btn.style.pointerEvents = 'auto';
      });
});

'''
    new_content = content[:start_idx] + replacement + content[end_idx:]
    with open('module_frequencia_diaria/Auditoria de falta.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Replaced successfully')
else:
    print('Failed to find start or end', start_idx, end_idx)
