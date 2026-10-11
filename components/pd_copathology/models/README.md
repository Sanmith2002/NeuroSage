# Trained models

No trained model binaries are stored here yet.

Final models will eventually be versioned under:

```
models/final/vX.Y/
```

Each version is expected to hold the fitted model, the preprocessing pipeline,
the feature list, the configuration it was trained with, and a short model
card.

The storage and version-control strategy for large model binaries (for example
Git LFS, DVC, or release assets) has not been decided. Until it is, do not
commit model binaries to this repository.
