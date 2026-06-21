import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.readonly']
DOCUMENT_ID = '1X7E-BD8cGCHY3HNzTs7PN4LIr0nfUJwOJIO5YFzonB4'

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('docs', 'v1', credentials=creds)

    document = service.documents().get(documentId=DOCUMENT_ID).execute()
    content = document.get('body').get('content')
    end_index = content[-1].get('endIndex') - 1

    report_text = """RESUMO EXECUTIVO DE AUDITORIA DE DADOS - DIARIO DE BORDO - GESTÃO DE PESSOAS (V2.0.0)

ANÁLISE 1 - CLASSIFICAÇÃO DA AUDITORIA
- Etapa: Auditoria Primária e Secundária (Extrato Diário & Listagem Detalhada)
- Tipo de Ocorrência: Erro na base do código do cadastro e Corrupção de Atributos
- Severidade: Crítica (Impacto direto em headcount, folha de eventos e confiabilidade)

O QUE ACONTECEU?
No nosso sistema do dashboard, foram consideradas apenas 534 pessoas. Só que nas planilhas originais temos 58 pessoas a mais, totalizando 592 colaboradores. Ocorreu o desfalque exato de 58 pessoas.

POR QUE ISSO ACONTECEU? (ERRO DE CHAVE PRIMÁRIA)
O problema ocorreu porque o sistema utiliza a coluna "CADASTRO" para identificar de forma única cada pessoa. O erro reside no fato de que, em ambas as planilhas exportadas pelo RH, existem pessoas completamente diferentes usando o mesmo número de cadastro.

Exemplos práticos do erro na base:
- O cadastro 11 se repete para as pessoas: ILSON MARCAL, JOSE LEITE DA SILVA, MARCELO NUNES DOS SANTOS e WILSON PEREIRA DA SILVA.
- O cadastro 1 se repete para as pessoas: FRANCINE, JANAINA, JULIO, LORAINE, LUCIA, LUCINEI, ORLINDO e ROBERTO.
- O cadastro 5 se repete para as pessoas: EDUARDO, IVAIR, JOSE EDUARDO e PEDRO.

QUAL É O IMPACTO DISSO NO SISTEMA?
1. Desaparecimento de Pessoas: Como o sistema lê e processa a planilha de cima para baixo, o nome das outras pessoas (ex: José, Marcelo e Wilson no cadastro 11) é ignorado, gerando o sumiço das 58 pessoas.
2. Mistura de Dados: As horas extras, ausências e atestados dessas pessoas que sumiram são indevidamente somadas "na conta" da primeira pessoa da lista.

---------------------------------------------------------

ANÁLISE 2 - INCONSISTÊNCIAS INTRA-PERFIL NAS DUAS PLANILHAS

Para garantir que o problema era apenas a sobreposição de cadastros, realizamos uma varredura analítica nos atributos internos dos colaboradores em ambas as planilhas. O resultado apontou que, mesmo ignorando a colisão de nomes diferentes, os dados essenciais da mesma pessoa estão corrompidos.

Exemplos práticos dos erros na base:

1. Conflito Múltiplo de Cargo (21 ocorrências graves)
A base lista a MESMA pessoa com cargos diferentes em linhas diferentes da tabela.
Exemplo: Cadastro 11 | JOSE LEITE DA SILVA aparece ao mesmo tempo como "ANALISTA DE COMPRAS JUNIOR" e "PINTOR DE OBRAS".

2. Falha de Atribuição Financeira (145 ocorrências)
A base exporta dezenas de funcionários ativos com o campo Salário nulo ou não atualizado.
Exemplo: Cadastro 11 | O salário do JOSE LEITE DA SILVA não subiu, permanecendo cravado em 0.00 na extração atual.

3. Conflito de Lotação / Centro de Custo
A base acusa lotações simultâneas inválidas.
Exemplo: Cadastro 9999 | FERNANDO PEREIRA DA COSTA está lotado ao mesmo tempo na "DIRETORIA GERAL" e em "DESPESAS COM PESSOAL - ADMINISTRAÇÃO".

---------------------------------------------------------

CONCLUSÃO FINAL: POR QUE NÃO PODEMOS TRABALHAR COM ESSAS PLANILHAS?

As duas planilhas disponibilizadas atualmente pelo sistema do RH ("Extrato Diário" e "Listagem Detalhada") são tecnicamente inviáveis para atuarem como fonte de verdade para o Dashboard de People Analytics, pelos seguintes motivos estruturais:

1. Falsa Chave Única (Destruição da Integridade):
A premissa básica de qualquer cruzamento de dados é que cada indivíduo possua um ID exclusivo. A reutilização de matrículas (Cadastros 1, 5, 11, etc.) destrói a integridade das métricas, forçando o painel a misturar atestados, punições e horas extras de pessoas totalmente diferentes como se fossem a mesma entidade.

2. Histórico Flutuante em Campos Estáticos:
Quando um funcionário muda de cargo, a extração do RH apenas lança linhas novas mantendo a ambiguidade ativa. O dashboard sofre sobrescrição randômica de perfil (podendo reverter o status de Analista de volta para Pintor de Obras) porque não existe uma data de demarcação ou hierarquia sobre qual cargo é o válido no presente.

3. Invalidação de KPIs Financeiros:
A quebra maciça no campo Salário (com 145 ocorrências de funcionários com salários R$ 0,00) impossibilita qualquer cálculo atuarial ou de custos reais da Folha de Pagamento.

Veredito da Auditoria: Para que o People Analytics opere com exatidão, a plataforma de origem do RH necessita ser higienizada para garantir que o "Cadastro" (Matrícula) seja exclusivo, sequencial e intransferível, além de consolidar uma visão estática confiável do cargo atualizado e do salário do colaborador.
"""

    requests = []
    if end_index > 1:
        requests.append({
            'deleteContentRange': {
                'range': {
                    'startIndex': 1,
                    'endIndex': end_index
                }
            }
        })
        
    requests.append({
        'insertText': {
            'location': {
                'index': 1,
            },
            'text': report_text
        }
    })

    print("Substituindo relatorio completo com a Analise 1 e Analise 2 no Google Docs...")
    try:
        service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': requests}).execute()
        print("Sucesso! Relatorio atualizado no Google Docs.")
    except Exception as e:
        print(f"Erro ao inserir no docs: {e}")

if __name__ == '__main__':
    main()
