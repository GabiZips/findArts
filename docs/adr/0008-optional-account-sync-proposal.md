# ADR 0008: sincronização opcional por conta

Status: **Proposta, não implementada nem autorizada para implantação**
Data: 2026-10-18

## Contexto

O pareamento atual transfere tags e credenciais diretamente na rede local,
sem conta e sem guardar dados em servidor do projeto (ADR 0005). Contas podem
permitir sincronização entre redes, mas criam um serviço que exige operação,
custo, exclusão/exportação de dados, recuperação e resposta a incidentes.

## Recomendação

Publicar primeiro o produto local, mantendo o pareamento. Contas não são
pré-requisito para tornar o código público e não devem ser obrigatórias.

Uma futura primeira versão de sync deve transferir somente tags, grupos e
preferências selecionadas. Excluir estado de revelação, cookies, histórico,
imagens e credenciais de fontes por padrão. Tags e coleções também podem ser
dados sensíveis; documentar exatamente o que é enviado e pedir consentimento.

## Onde os dados ficariam

- Autenticação: provedor gerenciado com login por navegador do sistema,
  Authorization Code + PKCE, sessões revogáveis e opção de MFA/passkeys.
- Sincronização: API autenticada e banco remoto com registros isolados por
  usuário. A autorização é feita no servidor, nunca apenas na interface.
- Dispositivos: cópia local continua funcionando offline; conflitos usam
  revisão/versionamento, sem substituir a configuração silenciosamente.
- Backups: criptografados, retenção definida e exclusão documentada.

Não foi escolhido provedor. Hospedar no próprio PC não oferece disponibilidade
confiável; usar GitHub como banco de configurações/segredos não é adequado.

## Credenciais das fontes são outra decisão

Login seguro não torna automaticamente seguro guardar tokens de terceiros.
Criptografia no servidor com a chave no mesmo serviço ainda permite que esse
serviço leia os dados. Para um cofre sincronizado, avaliar criptografia de ponta
a ponta: criptografar no dispositivo, servidor guarda apenas ciphertext, chaves
protegidas pelo sistema operacional e autorização explícita de novos dispositivos.

Essa opção exige projeto independente de recuperação, revogação, rotação de
chaves, dispositivos perdidos, metadados, conflitos e revisão criptográfica.
Não improvisar um protocolo ou derivar a chave diretamente da senha de login.
Perda da chave sem mecanismo de recuperação pode tornar os dados irrecuperáveis.

## Alternativas

1. Pareamento local: menor superfície de ataque e nenhum servidor; exige mesma rede.
2. Backup criptografado manual: útil entre PCs, mas precisa de formato e recuperação definidos.
3. Conta com sync opcional: conveniente, com custo operacional e risco adicional.

## Condições antes de implementar contas

- Aprovação do escopo, provedor, orçamento e política de dados.
- Threat model e testes de acesso entre usuários, expiração e revogação.
- Plano de exportação/exclusão, recuperação e restauração de backups.
- Revisão de obrigações de privacidade aplicáveis e dos termos das fontes.
- Nenhuma chave administrativa embutida no APK/EXE.

Referências: [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
e [Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html).
