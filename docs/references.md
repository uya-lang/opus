# Opus References

This file records normative specifications and upstream table sources used by
the Uya Opus implementation. Runtime code must not fetch these sources
dynamically; imported tables are checked into the repository and verified by
tests.

## Normative RFCs

- RFC 6716, Definition of the Opus Audio Codec:
  https://www.rfc-editor.org/rfc/rfc6716
- RFC 8251, Updates to the Opus Audio Codec:
  https://www.rfc-editor.org/rfc/rfc8251
- RFC 7845, Ogg Encapsulation for the Opus Audio Codec:
  https://www.rfc-editor.org/rfc/rfc7845
- RFC 7587, RTP Payload Format for the Opus Speech and Audio Codec:
  https://www.rfc-editor.org/rfc/rfc7587

## Upstream Baseline

The table migration baseline is the Xiph.Org Opus repository:

- Repository: https://github.com/xiph/opus
- Release tag: `v1.5.2`
- Tag object: `5ec2f3c915d0529b94a3a302969c673531654824`
- Peeled commit: `ddbe48383984d56acd9e1ab6a090c54ca6b735a6`

The current upstream `main` commit observed during setup was
`f8f99516092f4311a9b0784f190ff982df8eb2e6`. It is recorded for orientation
only; table imports must use the fixed `v1.5.2` commit unless a later TODO
explicitly updates this baseline.

## Decoder Vector Sources

Verified on 2026-06-04 from the official Opus test vector index:

- Index: https://opus-codec.org/testvectors/

Primary release decoder corpus:

- Name: Post-RFC8251 decoder bitstream vectors.
- Opus mirror:
  https://opus-codec.org/static/testvectors/opus_testvectors-rfc8251.tar.gz
- IETF source:
  https://www.ietf.org/proceedings/98/slides/materials-98-codec-opus-newvectors-00.tar.gz
- Archive SHA-256:
  `6b26a22f9ba87b2b836906a9bb7afec5f8e54d49553b1200382520ee6fedfa55`
- HTTP `Content-Length`: `74624664`.
- Archive root: `opus_newvectors/`.
- Contents observed: `testvector01..12.bit`, `testvector01..12.dec`, and
  `testvector01..12m.dec`.

Legacy decoder corpus for historical RFC6716 coverage:

- Name: Original RFC6716 decoder bitstream vectors.
- Opus mirror:
  https://opus-codec.org/static/testvectors/opus_testvectors.tar.gz
- IETF source:
  https://www.ietf.org/proceedings/83/slides/slides-83-codec-0.gz
- Archive SHA-256:
  `94ac78ca4f74c4e43bc9fe4ec1ad0aa36f38ab90f45b0727c40dd1e96096e767`
- HTTP `Content-Length`: `39001148`.
- Archive root: `opus_testvectors/`.
- Contents observed: `testvector01..12.bit` and `testvector01..12.dec`.

Reproducible fetch and verification commands:

```sh
mkdir -p build/vector_sources
curl -L --fail \
  -o build/vector_sources/opus_testvectors-rfc8251.tar.gz \
  https://opus-codec.org/static/testvectors/opus_testvectors-rfc8251.tar.gz
curl -L --fail \
  -o build/vector_sources/opus_testvectors.tar.gz \
  https://opus-codec.org/static/testvectors/opus_testvectors.tar.gz
sha256sum \
  build/vector_sources/opus_testvectors-rfc8251.tar.gz \
  build/vector_sources/opus_testvectors.tar.gz
tar -tzf build/vector_sources/opus_testvectors-rfc8251.tar.gz | sort
tar -tzf build/vector_sources/opus_testvectors.tar.gz | sort
```

The release manifest should import the post-RFC8251 corpus first. The original
RFC6716 corpus may be retained as an additional regression set, but it must not
replace the updated vectors.

## Table Source Inventory

The following upstream paths are the expected source of truth for table
migration. Generated Uya tables must record the exact upstream path, commit,
element type, Q-format or unit, length, and hash in `docs/table_inventory.md`.

- `celt/static_modes_fixed.h`: fixed-point CELT mode data, including eBands,
  allocation vectors, window metadata, and mode descriptors.
- `celt/static_modes_float.h`: float build companion for CELT mode data; use
  only to cross-check mode structure when fixed-point data is ambiguous.
- `celt/tables.c` and `celt/tables.h`: CELT window, log, bit allocation,
  pulse, and other codec tables.
- `celt/cwrs.c` and `celt/cwrs.h`: PVQ/CWRS combinatorial tables and helper
  constants.
- `silk/tables.h`: SILK table declarations and shared table shape.
- `silk/tables_*.c`: SILK entropy, NLSF, pulse, gain, pitch, LTP, stereo, and
  resampler tables.
- `silk/fixed/*.c` and `silk/float/*.c`: implementation-specific companion
  constants; fixed-point sources are authoritative for decoder conformance.
- `src/opus_multistream.c`, `src/mapping_matrix.c`, and related headers:
  channel mapping and multistream layout references for later API/container
  work.

## Precedence Rules

1. RFC 6716 and RFC 8251 define codec bitstream and decoder behavior.
2. RFC 7845 defines Ogg Opus container behavior.
3. RFC 7587 defines RTP payload behavior.
4. Xiph.Org Opus `v1.5.2` tables provide implementation constants when the RFC
   references generated or tabulated data.
5. If RFC text and upstream tables appear inconsistent, file an issue in
   `docs/uya-compiler-bugs.md` only for Uya compiler defects; specification or
   upstream interpretation questions belong in the relevant table inventory or
   conformance notes.
