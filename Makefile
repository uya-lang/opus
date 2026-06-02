SHELL := /bin/bash

BUILD_DIR := build
BIN_DIR := bin
SMOKE_SRC := src/opus/main.uya
SMOKE_BIN := $(BUILD_DIR)/opus-smoke
ENTROPY_DECODE_BENCH_SRC := bench/entropy_decode.uya
ENTROPY_DECODE_BENCH_BIN := $(BUILD_DIR)/entropy-decode-bench
TEST_SRCS := tests/scaffold_modules.uya tests/core_types.uya tests/core_constants.uya tests/core_errors.uya tests/core_qformat.uya tests/core_saturate.uya tests/core_bitops.uya tests/dsp_filters.uya tests/dsp_resampler.uya tests/dsp_pitch.uya tests/dsp_window.uya tests/dsp_mdct.uya tests/packet_toc.uya tests/entropy_range_dec.uya tests/entropy_range_enc.uya tests/celt_mode.uya tests/celt_rate.uya tests/celt_cwrs.uya tests/celt_deemphasis.uya tools/check_tables.uya
LOCAL_UYA := /media/winger/_dde_data/winger/uya/uya/bin/uya
UYA ?= $(shell if command -v uya >/dev/null 2>&1; then command -v uya; elif test -x "$(LOCAL_UYA)"; then printf '%s' "$(LOCAL_UYA)"; else printf '%s' uya; fi)

.PHONY: all bench check clean require-uya smoke test

all: smoke

check: require-uya
	@printf '%s\n' "Checking Opus scaffold..."
	@test -d src/opus
	@test -d src/opus/core
	@test -d src/opus/packet
	@test -d src/opus/entropy
	@test -d tests
	@test -d tests/vectors
	@test -d bench
	@test -d tools
	@test -d bin
	@test -d build
	@rg -q 'RFC 6716' docs/references.md
	@rg -q 'Decoder Conformance' docs/conformance.md
	@$(UYA) check $(SMOKE_SRC)
	@$(UYA) --version >/dev/null
	@printf '%s\n' "check: scaffold OK"

smoke: require-uya
	@mkdir -p $(BUILD_DIR)
	@$(UYA) build $(SMOKE_SRC) -o $(SMOKE_BIN)
	@$(SMOKE_BIN) >/dev/null
	@printf '%s\n' "smoke: build OK"

test: check
	@for test_src in $(TEST_SRCS); do \
		printf 'test: %s\n' "$$test_src"; \
		$(UYA) test "$$test_src" --project-root .; \
	done
	@python3 tools/check_tables.py

bench: require-uya
	@mkdir -p $(BUILD_DIR)
	@$(UYA) build $(ENTROPY_DECODE_BENCH_SRC) --project-root . -o $(ENTROPY_DECODE_BENCH_BIN)
	@$(ENTROPY_DECODE_BENCH_BIN)

require-uya:
	@if ! command -v "$(UYA)" >/dev/null 2>&1 && ! test -x "$(UYA)"; then \
		printf '%s\n' "UYA compiler not found. Set UYA=/path/to/uya or install uya in PATH." >&2; \
		exit 127; \
	fi

clean:
	rm -rf $(BUILD_DIR)/* $(BIN_DIR)/* .uyacache
