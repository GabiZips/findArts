# ArtFinder para Android

Cliente nativo em Kotlin, Jetpack Compose e Material 3. O APK não incorpora
Python, WebView nem depende de um servidor ArtFinder na internet.

## Estrutura

```text
app/src/main/java/io/github/gabizips/artfinder/
├── data/          persistência, pareamento e acesso às fontes
├── model/         modelos imutáveis compartilhados pela interface
├── ui/component/  componentes reutilizáveis e diálogos
├── ui/screen/     telas principais
├── ui/theme/      cores, tipografia e formas
├── MainActivity.kt
└── MainViewModel.kt
```

## Build local

Requer Java 17, Android SDK 36 e `ANDROID_HOME` configurado.

```powershell
cd android-native
.\gradlew.bat testDebugUnitTest lintDebug assembleRelease
```

O build local de release não é o APK público assinado. A assinatura estável e a
inspeção do pacote acontecem no workflow protegido do GitHub. Consulte
[docs/android-signing.md](../docs/android-signing.md).

## Regras da interface

- A navegação principal tem Pesquisa, Tags, Galeria e Configurações.
- Conteúdo NSFW respeita a preferência global de blur e exige revelação por arte.
- O filtro de arte marcada como gerada por IA é obrigatório.
- Guardar adiciona à biblioteca; Baixar publica uma cópia em
  `Pictures/ArtFinder` via MediaStore.
- Credenciais ficam protegidas pelo Android Keystore.
