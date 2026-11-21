# ArtFinder desktop em Rust

[Pesquisa de tecnologias e inventário da versão anterior](PARIDADE.md)

A versão nativa usa egui, SQLite e clientes HTTP escritos em Rust. No Windows, abra `target/release/artfinder-desktop.exe`. A primeira execução cria um perfil em `%LOCALAPPDATA%\ArtFinder-Rust`. Para usar outro diretório, defina `ARTFINDER_RUST_DIR`.

## Começar

1. Em **Configurações**, importe as categorias ou a biblioteca da instalação anterior, se quiser. A importação da biblioteca lê o banco anterior e copia as mídias disponíveis para o novo perfil.
2. Em **Credenciais**, escolha **Usar credenciais do arquivo .env do ArtFinder nesta sessão** para aproveitar a configuração antiga no Windows. Para uso persistente, salve cada campo no cofre do sistema. O aplicativo também aceita as variáveis de ambiente descritas no arquivo `.env.example` do projeto.
3. Em **Busca**, digite tags ou nomes de categorias. Separe consultas com ponto e vírgula. Escolha as fontes e o número de páginas ou marque **Até o fim**. As artes aparecem enquanto as páginas chegam. **Cancelar busca** conserva os resultados recebidos. **Carregar mais** retoma as consultas com páginas disponíveis.
4. Na busca, ajuste a grade entre **Compacta**, **Grande** e **Uma por linha**. Use **Guardar** para preservar a publicação ou **Baixar** para salvar o arquivo. Abra uma arte para ampliar e navegar com as setas. **Esc** fecha o visualizador. Vídeos salvos abrem no player do sistema.

## Biblioteca e filtros

Em **Filtros**, ajuste classificação, proteção de conteúdo, formato, período, orientação, resolução, pontuação e cor. Procure por artista, tags e fonte diretamente no campo de filtro. O filtro de cor usa as cinco cores mais frequentes da miniatura quantizada. Os resultados de busca ficam na sessão. Guardar, baixar ou adicionar a uma coleção registra a arte na biblioteca. A galeria identifica arquivos idênticos por SHA-256 e exibe imagens visualmente semelhantes pela distância entre seus hashes de diferença.

As configurações incluem categorias, ordem, favoritos, tags específicas por fonte, mapeamento de tags, bloqueios, reconciliação do índice e pareamento local. O código de pareamento permite uma transferência por até cinco minutos. O envio de credenciais é opcional.

## Compilar e testar

Execute nesta pasta com Rust estável e as ferramentas de compilação da plataforma.

```powershell
cargo build --release --locked
cargo test --release --locked
cargo test --release --locked live_sources -- --ignored --nocapture
cargo test --release --locked lan_roundtrip -- --ignored
cargo test --release --locked installed_library_import -- --ignored --nocapture
```

O teste online consulta Safebooru, Danbooru, Gelbooru, e621, Pixiv, Tumblr, Bluesky e DeviantArt. Cada fonte precisa devolver ao menos uma publicação utilizável, uma miniatura decodificável e um original válido. Configure as credenciais antes de rodar esse teste. O teste de pareamento requer uma interface de rede privada. O teste de importação usa uma biblioteca Windows já preenchida e grava em um diretório temporário.

A interface nativa chama os serviços Rust diretamente. O protocolo HTTP local do aplicativo Python, o APK Android e os instaladores da distribuição anterior são entregas separadas deste executável.
