# Android signing

Every Android update for `io.github.gabizips.artfinder` must use the same
private signing key. The key is not committed to this public repository.

The GitHub Actions workflow reads it from these repository secrets:

- `ARTFINDER_ANDROID_KEYSTORE_BASE64`
- `ARTFINDER_ANDROID_KEYSTORE_PASSWORD`

The expected public certificate SHA-256 fingerprint is:

```text
e8d6011c9c44b130be635ec8973184d39681d711b7b5aee1ab15e7354b408567
```

The workflow signs the generated APK with `apksigner` and then fails if the
certificate does not match this fingerprint. Its temporary keystore is removed
from the runner after the signing step.

The maintainer's recovery copy is stored below `.local-secrets/android/` in the
local checkout. That directory is ignored by Git and must be backed up in a
secure location. Losing both that copy and the GitHub Secrets makes it
impossible to publish an in-place update for existing installations.

Version 0.2.2 starts this stable signing lineage. Older experimental APKs used
ephemeral debug certificates and cannot be upgraded in place to this lineage.
