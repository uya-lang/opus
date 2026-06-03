# Benchmark Baseline

This file records benchmark environment and result format. The scaffold stage
does not report performance numbers.

## Machine

- Host: `winger-PC`
- OS/kernel: `Linux 6.12.65-amd64-desktop-rolling x86_64`
- CPU: `Intel(R) Xeon(R) CPU E5-2696 v4 @ 2.20GHz`
- Cores/threads: `22 cores / 44 threads`
- L3 cache: `55 MiB`

## Toolchain

- Uya path: `/media/winger/_dde_data/winger/uya/uya/bin/uya`
- Uya version: `v0.9.9`
- Uya baseline commit: `7fa4e34d248088e2c5dda14f61cc6df060e1e775`
- C compiler: `cc (Deepin 12.3.0-17deepin17) 12.3.0`

## Backend And Optimization

Baseline rows must record:

- backend: native Uya executable or Uya C99 backend;
- Uya optimization: `-O0`, `-O1`, `-O2`, or `-O3`;
- C compiler flags when using `--c99`;
- safety proof setting;
- input corpus or generated symbol distribution;
- sample count or symbol count;
- wall-clock timing source;
- allocation count source.

## Result Format

```text
date, commit, target, backend, opt, input, samples_or_symbols, time_ns, ns_per_unit, allocations, notes
```

## Current Results

```text
date, commit, target, backend, opt, input, samples_or_symbols, time_ns, ns_per_unit, allocations, notes
2026-06-02, working-tree, entropy_decode, Uya C99 backend, default, deterministic range symbols ft=2..33, 1024000 symbols, 51839000, 50 ns/symbol, 0, static buffers; checksum printed to keep decode work live
2026-06-03, working-tree, mdct_scalar_20ms, Uya C99 backend, default, deterministic 480-bin q15 coefficients, 61440 samples, 76875000, 1251 ns/sample, 0, 64 scalar IMDCT transforms; twiddle init outside timed loop; checksum=14796472906345177792
2026-06-03, working-tree, silk_decode_wb_20ms_mono, Uya C99 backend, default, deterministic SILK WB/20ms mono packet, 40960 samples, 8367000, 204 ns/sample, 0, 128 frames; packet_bytes=384; checksum=12485468123856353425
```
