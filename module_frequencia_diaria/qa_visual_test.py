from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('http://localhost:5008/login')
        page.fill('input[name="login"]', 'Andre')
        page.fill('input[name="senha"]', '*Savoia10')
        # Pressiona Enter para submeter, ou clica no botão (não sabemos o seletor do botão, enter é mais seguro)
        page.press('input[name="senha"]', 'Enter')
        
        # Aguarda a navegação para o dashboard
        page.wait_for_url('http://localhost:5008/dashboard', timeout=15000)
        
        # Dá um tempo extra para a renderização do data lake / charts
        page.wait_for_timeout(5000)
        
        # Tira screenshot da página inteira
        page.screenshot(path='D:/Projeto geral/People analytics - GP/module_frequencia_diaria/prova_visual_datalake_v260.png', full_page=True)
        print("Screenshot saved.")
        browser.close()

if __name__ == '__main__':
    run()
