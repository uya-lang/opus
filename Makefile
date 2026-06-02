SHELL := /bin/bash

BUILD_DIR := build
BIN_DIR := bin
LOCAL_UYA := /media/winger/_dde_data/winger/uya/uya/bin/uya
UYA ?= $(shell if command -v uya >/dev/null 2>&1; then command -v uya; elif test -x "$(LOCAL_UYA)"; then printf '%s' "$(LOCAL_UYA)"; else printf '%s' uya; fi)

.PHONY: all check clean require-uya

all: require-uya
	@printf '%s\n' "No default build target yet. Use make check once the smoke target is added."

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
	@$(UYA) --version >/dev/null
	@printf '%s\n' "check: scaffold OK"

require-uya:
	@if ! command -v "$(UYA)" >/dev/null 2>&1 && ! test -x "$(UYA)"; then \
		printf '%s\n' "UYA compiler not found. Set UYA=/path/to/uya or install uya in PATH." >&2; \
		exit 127; \
	fi

clean:
	rm -rf $(BUILD_DIR)/* $(BIN_DIR)/* .uyacache
