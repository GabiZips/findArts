# 0010 — Desktop nativo com Qt Widgets

Status: implementado. A publicação de novos instaladores depende do workflow de release.

## Problema e decisão

O usuário pediu uma interface realmente nativa no PC. O redesenho de HTML/CSS
continuava dependendo de um WebView. O launcher desktop passa a executar uma
`QApplication` e uma `QMainWindow` com PySide6. Listas, diálogos, menus, teclado,
imagens, animações e vídeos são desenhados por Qt, sem renderizador HTML.

Foi escolhido Qt Widgets para aproveitar os componentes de desktop maduros e
reutilizar o código Python. Uma reescrita das fontes em Rust, Go ou C++ não é
necessária para essa mudança de interface. QML pode ser considerado para
animações ou componentes futuros, sem alterar a fronteira do serviço.

## Componentes

```text
desktop.py
  ├─ serviço FastAPI privado, em 127.0.0.1 e porta aleatória
  │    └─ fontes / política de conteúdo / SQLite / downloads / cofre
  └─ QApplication → NativeWindow
       ├─ ApiClient → QNetworkAccessManager, cookie da sessão local
       ├─ ArtworkModel + delegate → galeria virtualizada
       ├─ diálogos Qt → categorias, coleções, busca, filtros, credenciais
       └─ QGraphicsView / QMovie / QMediaPlayer → mídia
```

As chamadas de rede são assíncronas. A busca consome eventos SSE, mantém os
resultados recebidos e cancela com `QNetworkReply.abort()`. Uma geração de busca
impede que respostas antigas alterem uma busca nova. Existe fallback para a
resposta JSON quando o serviço não tem SSE.

O cliente obtém o cookie da sessão no endpoint de bootstrap existente. O HTML
retornado é descartado, nunca renderizado. As imagens continuam passando pelo
proxy com a validação de destino existente; URLs externas só são abertas
explicitamente pelo usuário e somente para os esquemas HTTP/HTTPS.

As miniaturas são carregadas sob demanda, com até seis solicitações simultâneas
e cache limitado a 160 entradas. Prévias NSFW ficam ocultas por padrão e nem são
solicitadas antes de revelação explícita. O visualizador não inicia vídeos
automaticamente. Mídia original é carregada em memória; streaming progressivo
de vídeos grandes e pré-carregamento de imagens vizinhas ficam para evolução.

## Dados e distribuição

Nenhuma migração de categorias, banco, downloads ou cofre é necessária. Somente
as preferências visuais nativas usam um novo `native-ui.ini`. Configurações do
antigo localStorage não são importadas. A interface web continua disponível
para execução de `app.py`; o Android não foi modificado.

Dependências: PySide6 Essentials e Addons, sem dependência de WebEngine.
PyInstaller exclui explicitamente os módulos de navegador. Os locks Windows e
Linux preservam hashes; o Linux usa alvo manylinux 2.34, compatível com o Ubuntu
22.04 do workflow. O smoke test empacotado verifica Qt, mídia e pareamento.
No Windows, o pacote usa a ICU fornecida pelo sistema (Windows 10+). O spec
exclui cópias de ICU encontradas no PATH: uma cópia do Poppler com símbolos
versionados causou WinError 127 ao carregar Qt no primeiro teste empacotado.
O verificador de distribuição rejeita esse conflito e um navegador embutido.

## Verificação

`tests/test_native_ui.py` usa o serviço real com banco temporário e fontes
simuladas. Cobre busca, cookie local, cancelamento, filtros, identidades de
arquivos baixados, salvamento, avaliações, categorias e revelação de NSFW.
Defina `ARTFINDER_NATIVE_SCREENSHOTS` para salvar capturas com dados sintéticos.
`ARTFINDER_TEST_VIDEO` pode apontar para um vídeo sintético local para testar
reprodução efetiva (e não apenas a importação do componente). Esse teste também
verifica GIF animado e garante que o vídeo espere uma ação antes de reproduzir.
Sem essa variável, somente esse teste opcional de codec é pulado.

```powershell
venv\Scripts\python -m unittest discover -s tests -p test_native_ui.py -v
venv\Scripts\python -m PyInstaller --noconfirm --clean --distpath dist/native artfinder.spec
```

Testes de fontes simuladas não comprovam disponibilidade das APIs externas,
autenticação real nem compatibilidade de todos os codecs em outras máquinas.

## Biblioteca e direção visual

A interface PC usa navegação lateral com coleções, grade virtualizada com
controle de tamanho e painel de detalhes redimensionável. O painel respeita a
mesma proteção de prévias NSFW do visualizador. A busca direta por tags conserva
a busca avançada em janela. Tamanho das miniaturas, visibilidade dos detalhes
e tema são persistidos; quatro temas mantêm suas chaves anteriores.

Referências de interação: [Eagle](https://eagle.cool/support/get-started)
(biblioteca, barra de ferramentas e inspetor) e
[PureRef](https://www.pureref.com/handbook/canvas/) (prioridade visual às artes).
Nenhuma imagem gerada por IA integra a interface. As capturas dos testes usam
figuras geométricas sintéticas somente como fixtures, nunca como conteúdo do app.
