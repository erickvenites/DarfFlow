import requests

def enviar_arquivo_xml(caminho_arquivo, url_endpoint, caminho_certificado):
    # Define o arquivo XML como payload
    with open(caminho_arquivo, 'rb') as arquivo:
        xml_conteudo = arquivo.read()

    headers = {
        'Content-Type': 'application/xml'  # Define explicitamente o tipo de conteúdo
    }

    # Envia o arquivo para o endpoint com o certificado SSL
    try:
        response = requests.post(
            url_endpoint, 
            data=xml_conteudo,  # Envia o conteúdo do XML como 'data'
            headers=headers,     # Passa o cabeçalho com o Content-Type correto
            cert=caminho_certificado  # Usa o certificado SSL
        )
        
        # Verifica se o envio foi bem-sucedido
        if response.status_code == 200:
            print("Arquivo enviado com sucesso!")
            print("Resposta do servidor:", response.text)
        else:
            print("Falha ao enviar o arquivo. Código de status:", response.status_code)
            print("Resposta do servidor:", response.text)
    except requests.exceptions.SSLError as e:
        print("Erro de SSL:", e)
    except Exception as e:
        print("Erro ao enviar o arquivo:", e)

# Exemplo de uso
caminho_do_arquivo_xml = 'uploads/temp/DADM/4020/evento4020-08-10-2024-1/evento-lote-1.xml'
url_do_endpoint = 'https://pre-reinf.receita.economia.gov.br/recepcao/lotes'  # Endpoint da Receita Federal
caminho_certificado = 'docs/certificate2.pem'  # Caminho para o certificado SSL do cliente

enviar_arquivo_xml(caminho_do_arquivo_xml, url_do_endpoint, caminho_certificado)
