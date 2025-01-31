import pexpect
from src.config.logging_config import logger

def send_with_pexpect(endpoint_url, certificate_path, senha_cert, xml_data):
    """Automatiza o envio usando pexpect para manipular entrada de senha."""
    try:
        command = f'curl -X POST --cert {certificate_path} --data-binary "@-" {endpoint_url}'
        
        # Iniciar o processo com pexpect
        child = pexpect.spawn(command)
        
        # Esperar a solicitação da senha do certificado
        child.expect("Enter PEM pass phrase:")
        
        # Enviar a senha do certificado
        child.sendline(senha_cert)
        
        # Enviar o conteúdo do XML via stdin
        child.send(xml_data)
        child.sendeof()

        # Esperar o final do processo e capturar a saída
        child.expect(pexpect.EOF)
        return child.before.decode()

    except pexpect.exceptions.ExceptionPexpect as e:
        logger.error(f"Erro ao enviar com pexpect: {e}")
        raise