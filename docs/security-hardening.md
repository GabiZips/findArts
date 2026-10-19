# Correções de segurança e confiabilidade

## Mudanças implementadas

- **Sessão local:** abrir `/` cria um cookie HttpOnly/SameSite Strict por processo.
  APIs privadas exigem essa sessão, inclusive em loopback. `/api/health` continua
  disponível para diagnóstico. O modo LAN mantém seu token separado.
- **Host:** apenas localhost/loopback e, no modo LAN, endereços IP privados são
  aceitos. Um domínio externo não é autorizado por possuir Origin igual ao Host.
- **Interface desktop:** dados de artistas, grupos, tags, IDs e caminhos não
  são interpolados em código de eventos. Links externos aceitam apenas HTTP(S).
- **Imagens:** o transporte conecta ao IP público validado e preserva hostname,
  SNI e verificação do certificado TLS. O transporte de imagens não usa proxies
  do ambiente. Credenciais Danbooru só acompanham HTTPS para o host exato da API.
- **Busca:** JSON e SSE compartilham plano de consultas, overrides por fonte,
  deduplicação, blacklist, score mínimo e política obrigatória de exclusão de IA.
- **Pareamento:** respostas são lidas com limite durante a transferência;
  redirecionamentos são recusados. O Android captura falhas no recebimento e na
  persistência e limpa o estado ocupado inclusive em cancelamento.
- **Privacidade Android:** imagens NSFW/sensíveis ocultas não são carregadas nem
  compostas. A mesma proteção é usada em cards, visualizador e capas de coleção,
  independentemente do suporte a blur do sistema (Android 10–16).
- **Galeria Android:** transferência para arquivo temporário privado com limite
  de tamanho, até três operações simultâneas e serialização por arte. A exclusão
  mantém o registro quando o provedor retorna erro. Arquivos já ausentes podem
  ser removidos da biblioteca e baixados novamente.
- **CI:** inclui testes de segurança JavaScript e testes/lint/build debug Android
  em PRs, sem acesso à chave de assinatura. Dependabot acompanha Gradle.

## Uso de scripts locais

Clientes HTTP que antes chamavam a API diretamente precisam primeiro fazer um
GET em `/` e manter os cookies recebidos. Nunca copie esse cookie para outro
site. O cookie expira na prática ao encerrar o processo; reabra a interface se
receber 401. A sessão local não substitui a proteção do usuário/sistema operacional.

## Validação automatizada

Execute com dados de teste, sem reutilizar o diretório pessoal de downloads:

```text
python -m unittest discover -s tests -v
python -m ruff check .
node --test tests/frontend_security.test.js
```

No diretório `android-native`, com Java compatível e Android SDK 36:

```text
gradlew testDebugUnitTest lintDebug assembleDebug assembleRelease
```

Os testes de backend incluem uma sessão HTTP real em loopback, sem contas nem
chamadas às fontes. Os testes de transporte verificam IP conectado, TLS/SNI,
alteração de DNS, redirecionamentos e credenciais HTTP. Os de Android verificam
limites de cópia, concorrência, cancelamento, exclusão e política de privacidade.

## Verificação manual antes de publicar

- Android 10/11 e 15/16: nenhuma imagem sensível aparece antes de revelar,
  inclusive em capas; navegação lateral e zoom continuam funcionando.
- Parear, cancelar e tentar novamente; simular falha de armazenamento.
- Baixar, apagar pela galeria do sistema e baixar de novo; negar uma exclusão
  e confirmar que a arte continua listada no ArtFinder.
- Testar abertura do executável em instalação limpa e atualização com dados
  existentes. Validar assinatura e versão de cada artefato antes da Release.

Compilação/testes/lint não substituem testes visuais em dispositivo. Nenhum
resultado desta etapa afirma ausência de todas as vulnerabilidades possíveis.

## Próximas etapas separadas

1. Migrar galeria/coleções Android de JSON/DataStore para Room, com backup,
   migração transacional, testes de restauração e paginação. Não alterar os
   dados existentes silenciosamente.
2. Adotar armazenamento de credenciais do sistema no desktop com migração
   explícita de `.env` e estratégia compatível com Windows/Linux.
3. Centralizar o catálogo de mapeamentos de fontes consumido por Python/Kotlin
   e ampliar testes de contrato. O bloqueio de IA depende dos metadados recebidos;
   nenhuma heurística de tags garante detecção de conteúdo não identificado.
4. Acrescentar testes instrumentados/visuais Android e reduzir progressivamente
   o JavaScript embutido e as responsabilidades restantes de `app.py`.
