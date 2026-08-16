from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('http://localhost:5008/login')
        page.fill('input[name="login"]', 'Andre')
        page.fill('input[name="senha"]', '*Savoia10')
        page.press('input[name="senha"]', 'Enter')
        page.wait_for_url('http://localhost:5008/dashboard', timeout=15000)
        page.wait_for_timeout(3000)

        # Seleciona a data 04/08 ou "04-08" no drop-down (tem ID 'f-data')
        # A página usa select2 ou um select normal? Vamos tentar focar e dar seta pra baixo, ou definir o value via JS
        page.evaluate("document.getElementById('f-data').value = '04/08/2026';") # Tenta mudar o value se for esse o formato
        # Dispara o evento change para os filtros rodarem
        page.evaluate("const ev = new Event('change'); document.getElementById('f-data').dispatchEvent(ev);")
        
        page.wait_for_timeout(3000)
        
        page.screenshot(path='D:/Projeto geral/People analytics - GP/module_frequencia_diaria/prova_visual_hc_granularidade.png', full_page=True)
        print("Screenshot saved.")
        browser.close()

if __name__ == '__main__':
    run()
