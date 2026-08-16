# 📘 Arquitetura Padrão: Servidor Local Autônomo & Distribuição em Rede Interna (LAN / Intranet)

> **Documento de Engenharia de Software & Infraestrutura**  
> **Finalidade**: Guia padrão e reutilizável para transformar qualquer aplicação web local em um servidor de rede autônomo, acessível por múltiplos usuários da empresa via link, sem custos de hospedagem em nuvem e sem necessidade de comandos manuais no terminal.

---

## 1. Visão Geral do Modelo Arquitetural

Esta arquitetura adota o modelo **On-Premise Local Server (Zero-Cloud Cost)**. Ela permite transformar qualquer computador Windows em um **Servidor Central de Aplicação**, distribuindo sistemas web para qualquer dispositivo conectado na mesma rede Wi-Fi ou cabo de rede (LAN/Intranet).

```mermaid
graph TD
    A["💾 Fonte de Dados Local<br/>(Excel / SQLite / JSON / BD)"] --> B["⚙️ Motor de Regras de Negócio & API<br/>(Python, Node.js, Go, etc.)"]
    B --> C["🚀 Servidor Web Local<br/>(Binding Global em 0.0.0.0:Porta)"]
    
    subgraph Servidor Host (Máquina Local do Projeto)
        A
        B
        C
        D["🤖 Script VBS Oculto<br/>(Auto-Start no Boot do Windows)"] --> C
    end

    C -->|HTTP / Nome da Máquina| E["💻 Computador 1 (Equipe)<br/>http://PencinatoGalaxyBook2:5000"]
    C -->|HTTP / Nome da Máquina| F["💻 Computador 2 (Gestão)<br/>http://PencinatoGalaxyBook2:5000"]
    C -->|Navegador Local| G["🖥️ Tela Local (Host)<br/>http://localhost:5000"]
```

---

## 2. Pilares da Arquitetura

### 2.1. Conexão Global de Rede (`0.0.0.0` Binding)
Para que uma aplicação web local possa responder a requisições de outros computadores da rede, a escuta (*binding*) do servidor deve ser configurada para `0.0.0.0` em vez de `127.0.0.1`:

- `127.0.0.1` (**localhost**): Aceita conexões **apenas** da própria máquina onde o código está rodando.
- `0.0.0.0` (**All Network Interfaces**): Instrui o servidor a aceitar requisições vindas de qualquer placa de rede ativa no computador (Placa de Rede Ethernet, Wi-Fi ou VPN local).

#### Exemplo em Python (Flask / FastAPI):
```python
if __name__ == '__main__':
    # host='0.0.0.0' libera a aplicação para a rede local
    app.run(host='0.0.0.0', port=5000, debug=False)
```

#### Exemplo em Node.js (Express):
```javascript
const PORT = 5000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Servidor rodando em http://0.0.0.0:${PORT}`);
});
```

---

### 2.2. Execução Autônoma em Segundo Plano (Background Service)

Para impedir a dependência de manter janelas pretas de terminal ativas e evitar o risco do usuário fechar o sistema por engano, a aplicação é envolvida por um executor **VBScript Silencioso**:

#### Template Genérico do VBScript (`iniciar_servidor.vbs`):
```vbscript
Set WshShell = CreateObject("WScript.Shell")

' 1. Define a pasta do projeto
WshShell.CurrentDirectory = "C:\Caminho\Do\Seu\Projeto"

' 2. Executa o comando em modo oculto (O parâmetro 0 oculta a janela preta)
WshShell.Run "py app.py", 0, False

' 3. Aguarda a inicialização do servidor e abre o navegador
WScript.Sleep 2000
WshShell.Run "http://localhost:5000"
```

#### Autoinício no Boot do Windows (`shell:startup`):
Para tornar o projeto **100% independente de ação humana**, uma cópia do script VBScript é inserida no diretório de inicialização nativa do Windows:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

**Resultado**: Sempre que o computador host for ligado ou reiniciado, o servidor sobe automaticamente em segundo plano.

---

### 2.3. Resolução de Nomes de Rede (Evitando Mudanças de IP via mDNS / Hostname)

Quando o computador é reconectado em redes Wi-Fi diferentes (ex: em casa, no escritório ou em viagens), o roteador via DHCP pode atribuir um número de IP diferente (ex: `192.168.1.15` em vez de `192.168.41.99`).

Para evitar a necessidade de reenviar um novo link com IP numérico a cada mudança de rede, adotam-se três estratégias:

1. **Uso do Hostname do Computador (Recomendado)**:
   - Todo computador Windows possui um nome único registrado na rede (ex: `PencinatoGalaxyBook2`).
   - O Windows e os roteadores modernos resolvem esse nome automaticamente via **mDNS / NetBIOS**.
   - **Link Fixo Único**: `http://PencinatoGalaxyBook2:5000` (ou `http://PencinatoGalaxyBook2.local:5000`).
   - *Vantagem*: O link permanece exatamente o mesmo, independentemente de qual IP o roteador atribuiu para a máquina.

2. **Reserva de IP Fixo no Roteador (DHCP Reservation)**:
   - Na rede fixa do escritório, o administrador de TI associa o endereço MAC da placa de rede da máquina Host a um IP estático (ex: `192.168.41.99`), garantindo que o IP numérico jamais mude naquela rede.

3. **Túnel Seguro Remoto para Acesso Fora da Rede (Cloudflare Tunnel / LocalTunnel)**:
   - Se pessoas fora da mesma rede Wi-Fi (em outras cidades ou casas) precisarem acessar a aplicação, pode ser ativado um túnel criptografado gratuito (ex: Cloudflare Tunnel) que gera um link fixo universal HTTPS (ex: `https://meu-projeto.trycloudflare.com`).

---

### 2.4. Resiliência de Dados & Persistência Local (Zero Data Loss)

Em aplicações locais, a perda de dados ao fechar a janela deve ser prevenida estruturando a persistência em arquivo:
- **Fontes de Dados Leves**: Planilhas Excel (`.xlsx`), bancos de dados embarcados (`SQLite`, `DuckDB`) ou arquivos estruturados (`JSON` / `YAML`).
- **Escrita Assíncrona / Imediata**: Toda alteração de estado feita pelo usuário (como formulários ou checklists) deve ser gravada imediatamente no disco local.

---

## 3. Checklist Passo a Passo para Replicar em Novos Projetos

Para aplicar esta arquitetura em qualquer novo projeto da empresa, siga este roteiro:

1. **Configurar o Server Binding**: No arquivo principal da aplicação web (ex: `app.py` ou `server.js`), defina o escutador em `host='0.0.0.0'`.
2. **Criar o Script de Inicialização Silenciosa**: Crie o arquivo `iniciar_servidor.vbs` apontando para o arquivo principal do seu projeto.
3. **Instalar na Pasta Startup do Windows**: Copie o arquivo VBScript para `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` (ou crie um arquivo `.bat` automatizado para realizar essa cópia).
4. **Usar Hostname para Link Fixo**: Obtenha o nome do computador (`hostname` no terminal) e distribua o link `http://NOME_DO_PC:PORTA`.
5. **Configurar Liberação de Firewall**: Adicione a regra de liberação de porta no Windows Defender Firewall se necessário.

---

## 4. Matriz de Vantagens da Arquitetura

| Critério | Aplicação em Nuvem Tradicional | Arquitetura Local Autônoma (LAN) |
| :--- | :--- | :--- |
| **Custo de Hospedagem** | Cobrança mensal em Dólar/Reais (AWS/Azure) | **R$ 0,00** (Utiliza a infraestrutura existente) |
| **Dependência de Internet** | Requer conexão contínua com a internet | **Funciona Offline** na rede interna da empresa |
| **Estabilidade de Link** | Requer domínio pago `.com.br` | **Link Fixo por Hostname** (`http://PencinatoGalaxyBook2:5000`) |
| **Instalação no Usuário Final** | Nenhuma (Acesso via Navegador) | **Nenhuma** (Acesso via Navegador) |
| **Velocidade de Leitura** | Limitada pela banda de internet | **Instantânea** (Leitura direta em disco local) |

---

*Padrão arquitetural estabelecido para desenvolvimento de soluções corporativas autônomas em rede local.*
