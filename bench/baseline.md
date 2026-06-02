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

No baseline result is recorded until a benchmark target measures real codec or
entropy work.
