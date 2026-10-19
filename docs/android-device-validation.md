# Validação Android em aparelho

O APK local de teste usa o identificador `io.github.gabizips.artfinder.debug`
e aparece como **ArtFinder Preview**. Pode coexistir com a versão de distribuição;
mantém configurações, credenciais e galeria interna separadas. Não desinstale
o app normal para testar. Arquivos baixados para a galeria pública continuam
visíveis aos demais apps de fotos.

Pacote local: `dist/review/ArtFinder-Preview.apk`. É um build debug, não uma
release assinada com a chave de distribuição. A configuração exige Android 10
ou mais recente; isso não comprova funcionamento em todas as versões.

## Roteiro no celular

1. Instalar Preview ao lado do app atual. Confirmar que abre e começa sem tags.
2. Parear por código com o PC. Confirmar tags e fontes configuradas, sem expor
   o código em screenshots ou mensagens públicas.
3. Pesquisar com uma fonte e uma página; depois testar várias fontes. Conferir
   mensagens quando faltar autenticação ou quando a rede bloquear uma fonte.
4. Tocar numa arte protegida: revelar sem ampliar. Tocar novamente: abrir.
   Ocultar, passar à próxima arte e reativar proteção global; conferir blur.
5. Testar zoom, arrasto lateral, voltar, rotação e barras de sistema.
6. Guardar numa coleção e baixar uma imagem de teste. Conferir a diferença
   entre galeria interna e Fotos/Galeria do aparelho.
7. Encerrar e reabrir: tags e coleções devem permanecer. Revelações temporárias
   não devem ser restauradas.

Registrar modelo, Android, etapa, resultado e mensagem de erro. Evitar dados
pessoais e credenciais nos registros.

## Atualização

Para validar atualização real, instalar uma segunda versão assinada com a mesma
chave e identificador por cima da primeira. Confirmar tags, coleções, preferências
e autenticação. Reinstalar o mesmo APK não comprova migração entre versões.

Sem aparelho conectado, compilação, lint e testes unitários não comprovam
gestos, permissões nem integração com a galeria do sistema.
