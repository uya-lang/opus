# Uya Compiler Bugs

This file tracks Uya compiler defects triggered by this project. Each entry
must contain a minimal reproduction, the exact compiler version, the command
that fails, the expected behavior, the actual behavior, and the current status.

Compiler baseline:

- Path: `/media/winger/_dde_data/winger/uya/uya/bin/uya`
- Minimum version: `v0.9.9`
- Baseline commit: `7fa4e34d248088e2c5dda14f61cc6df060e1e775`

## Entry Format

```text
## BUG-YYYYMMDD-N

Status: open | fixed | workaround | invalid
Compiler: vX.Y.Z, commit <hash>
Command:
  <uya command>

Minimal reproduction:
  <path under tests/compiler_repros/ or inline snippet>

Expected:
  <expected compiler/runtime behavior>

Actual:
  <observed failure, diagnostic, crash, or wrong code>

Notes:
  <workaround, upstream issue link, or follow-up>
```

## Known Bugs

No Uya compiler bug has been confirmed by this project yet.
