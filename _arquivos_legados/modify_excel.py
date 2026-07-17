from bs4 import BeautifulSoup
import codecs

try:
    with codecs.open('DP_-_Colaboradores_-_Extrato_Diário.xls', 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    print(f"Total rows: {len(rows)}")
    
    if len(rows) >= 700:
        row_700 = rows[699] # 0-indexed, so 699 is row 700
        tds = row_700.find_all(['td', 'th'])
        if tds:
            print(f"Row 700 Col A original: {tds[0].text}")
            if tds[0].text.strip().lower() == 'x':
                tds[0].string = 'eu estou aqui'
                print(f"Row 700 Col A changed to: {tds[0].text}")
                
        with codecs.open('DP_-_Colaboradores_-_Extrato_Diário_Modified.xls', 'w', encoding='utf-8') as f:
            f.write(str(soup))
        print("File saved as DP_-_Colaboradores_-_Extrato_Diário_Modified.xls")
    else:
        print(f"Only {len(rows)} rows found, looking at last row: {rows[-1].find_all(['td', 'th'])[0].text}")
        
except Exception as e:
    import traceback
    traceback.print_exc()
