# Subjective Samples

This directory stores the manifest for generated listening samples used while
tuning encoder quality. The repository keeps the sample definitions in source
control and generates WAV files on demand:

```bash
make subjective-samples
```

Generated WAV files are written to `build/subjective-samples/`.
