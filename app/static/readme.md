# Assinador Digital

Este módulo está em desenvolvimento e tem como objetivo automatizar o processo de assinatura de arquivos XML para envio. Com ele, o usuário não precisará lidar com a complexidade de baixar e assinar manualmente os XMLs, agilizando e simplificando o processo.

## Funcionalidades

- **Assinatura de XMLs:** Automatiza a assinatura digital de arquivos XML usando uma chave privada e certificado digital.
- **Minificação de XML:** Reduz o tamanho do arquivo XML para otimizar o envio.
- **Envio automático:** Faz o envio do XML assinado para o endpoint do eSocial/Reinf.
- **Tratamento de erros:** Retorna mensagens detalhadas em caso de falhas no processo.

## Tecnologias Utilizadas

- **Node.js**
- **xml-crypto:** Para realizar a assinatura digital do XML.
- **node-forge:** Para manipulação de certificados e chaves privadas.
- **xml-minifier:** Para compactar o XML.
- **https (módulo nativo do Node.js):** Para realizar requisições HTTPs.

## Pré-requisitos

1. **Node.js instalado:** Certifique-se de ter o Node.js instalado na máquina.
2. **Certificados e Chaves Privadas:**
   - Certificado digital (`certificate_user.pem`) e chave privada (`private_key_decrypted.pem`) localizados na pasta `certificado/`.
   - Chave privada sem senha, configurada para ser usada no processo de assinatura.
