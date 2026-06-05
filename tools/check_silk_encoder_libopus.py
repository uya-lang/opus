#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_UYA = ROOT.parent / "uya" / "bin" / "uya"
TOOL_SRC = ROOT / "tools" / "encode_silk_basic_packet.uya"
TOOL_BIN = ROOT / "build" / "uopus-encode-silk-basic-packet"


def uya_command() -> str:
    configured = os.environ.get("UYA")
    if configured:
        return configured
    if LOCAL_UYA.exists():
        return str(LOCAL_UYA)
    return "uya"


def run_checked(command: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=capture_output,
    )
    if completed.returncode != 0:
        if completed.stdout:
            sys.stdout.buffer.write(completed.stdout)
        if completed.stderr:
            sys.stderr.buffer.write(completed.stderr)
        raise SystemExit(completed.returncode)
    return completed


def build_packet_tool() -> None:
    TOOL_BIN.parent.mkdir(parents=True, exist_ok=True)
    run_checked([
        uya_command(),
        "build",
        str(TOOL_SRC),
        "--project-root",
        ".",
        "-o",
        str(TOOL_BIN),
    ])


def generate_packet() -> bytes:
    completed = run_checked([str(TOOL_BIN)], capture_output=True)
    packet = completed.stdout
    if len(packet) <= 1:
        raise SystemExit(f"encoder emitted too-short SILK packet: {len(packet)} byte(s)")
    if packet[0] != 72:
        raise SystemExit(f"encoder emitted unexpected SILK TOC byte: {packet[0]}")
    return packet


def load_libopus() -> ctypes.CDLL:
    for name in ("libopus.so.0", "libopus.so"):
        try:
            return ctypes.CDLL(name)
        except OSError:
            pass
    raise SystemExit("libopus runtime not found: expected libopus.so.0 or libopus.so")


def libopus_error_message(opus: ctypes.CDLL, code: int) -> str:
    try:
        opus.opus_strerror.argtypes = [ctypes.c_int]
        opus.opus_strerror.restype = ctypes.c_char_p
        message = opus.opus_strerror(code)
    except AttributeError:
        return str(code)
    if message is None:
        return str(code)
    return message.decode("utf-8", errors="replace")


def decode_with_libopus(packet: bytes) -> None:
    opus = load_libopus()
    opus.opus_decoder_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    opus.opus_decoder_create.restype = ctypes.c_void_p
    opus.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
    opus.opus_decoder_destroy.restype = None
    opus.opus_decode.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int16),
        ctypes.c_int,
        ctypes.c_int,
    ]
    opus.opus_decode.restype = ctypes.c_int

    err = ctypes.c_int(0)
    decoder = opus.opus_decoder_create(16000, 1, ctypes.byref(err))
    if not decoder or err.value != 0:
        raise SystemExit(f"opus_decoder_create failed: {libopus_error_message(opus, err.value)}")

    try:
        packet_buf = (ctypes.c_ubyte * len(packet)).from_buffer_copy(packet)
        pcm = (ctypes.c_int16 * 320)()
        decoded = opus.opus_decode(decoder, packet_buf, len(packet), pcm, 320, 0)
        if decoded != 320:
            raise SystemExit(
                f"libopus rejected encoder SILK packet: {decoded} "
                f"({libopus_error_message(opus, decoded)})"
            )
    finally:
        opus.opus_decoder_destroy(decoder)


def main() -> int:
    build_packet_tool()
    packet = generate_packet()
    decode_with_libopus(packet)
    print(f"check_silk_encoder_libopus: OK ({len(packet)} byte packet decoded to 320 samples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
