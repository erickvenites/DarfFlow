import fs from 'fs';
import { SignedXml } from 'xml-crypto';
import forge from 'node-forge';
import https from 'https';

/**
 * Assina um XML existente e envia para a Receita Federal.
 * @param {string} xmlPath - Caminho do arquivo XML existente.
 * @param {string} password - Senha do certificado.
 * @param {string} certificatePath - Caminho do certificado do usuário.
 */
async function signAndSendXml(xmlPath, password, certificatePath) {
  // Ler a chave privada e descriptografar
  const privateKeyPem = fs.readFileSync(certificatePath, 'utf8');
  const privateKey = forge.pki.privateKeyFromPem(privateKeyPem, password);
  const privateKeyPemNoPassphrase = forge.pki.privateKeyToPem(privateKey);

  // Ler o certificado
  const certificate = fs.readFileSync(certificatePath);
  const certBase64 = certificate.toString('base64').replace(/\n/g, '');

  // Configuração da assinatura
  const sig = new SignedXml({
    privateKey: privateKeyPemNoPassphrase,
    publicCert: certBase64,
  });

  sig.getKeyInfoContent = function () {
    return `
      <X509Data>
        <X509Certificate>${certBase64}</X509Certificate>
      </X509Data>
    `;
  };

  sig.addReference({
    xpath: "//*[local-name(.)='evtRetPJ']",
    transforms: [
      "http://www.w3.org/2000/09/xmldsig#enveloped-signature",
      "http://www.w3.org/2001/10/xml-exc-c14n#",
    ],
    digestAlgorithm: "http://www.w3.org/2001/04/xmlenc#sha256",
  });

  // Ler o XML existente
  const xmlFile = fs.readFileSync(xmlPath, 'utf-8');

  // Realizar a assinatura
  sig.canonicalizationAlgorithm =
    "http://www.w3.org/2001/10/xml-exc-c14n#WithComments";
  sig.signatureAlgorithm = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256";

  sig.computeSignature(xmlFile);
  const signatureXml = sig.getSignedXml();

  // Inserir a assinatura entre as tags </evtRetPJ> e </Reinf>
  const updatedXml = xmlFile.replace(
    '</evtRetPJ>',
    `</evtRetPJ>${signatureXml}`
  );

  // Salvar o XML assinado em um novo arquivo
  const signedXmlPath = 'file_signed.xml';
  fs.writeFileSync(signedXmlPath, updatedXml, 'utf-8');

  // Configurações do envio
  const options = {
    hostname: 'reinf.receita.economia.gov.br',
    port: 443,
    path: '/recepcao/lotes',
    method: 'POST',
    headers: {
      'Content-Type': 'application/xml',
    },
    key: privateKeyPemNoPassphrase,
    cert: certificate,
    passphrase: password,
  };

  // Enviar o XML assinado
  const req = https.request(options, (res) => {
    let data = '';

    res.on('data', (chunk) => {
      data += chunk;
    });

    res.on('end', () => {
      if (res.statusCode === 200 || res.statusCode === 201) {
        console.log('XML assinado e enviado com sucesso!', res.statusCode, data);
      } else {
        console.error(`Erro ao enviar o XML: ${res.statusCode} - ${data}`);
      }
    });
  });

  req.on('error', (error) => {
    console.error('Erro ao enviar o XML:', error.message);
  });

  req.write(updatedXml);
  req.end();
}

// Exemplo de uso
const xmlFilePath = 'schemas/evt4020.xml'; // Caminho do XML já minificado
const password = '123456';
const certificatePath = 'certificado/certificate_user.pem';

signAndSendXml(xmlFilePath, password, certificatePath);
