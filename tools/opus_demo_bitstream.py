#!/usr/bin/env python3
"""Validate and inspect opus_demo .bit packet streams."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


MAX_PACKET_BYTES = 1500


class BitstreamError(Exception):
    """Raised when an opus_demo .bit stream is malformed."""


@dataclass(frozen=True)
class OpusDemoPacket:
    index: int
    length: int
    final_range: int
    payload_offset: int
    payload: bytes


@dataclass(frozen=True)
class BitstreamSummary:
    packet_count: int
    payload_bytes: int
    max_packet_bytes: int
    last_final_range: int


def _read_exact(handle, path: Path, offset: int, size: int, field: str) -> bytes:
    data = handle.read(size)
    if len(data) != size:
        raise BitstreamError(
            f"{path}: truncated {field} at byte {offset}: expected {size} byte(s), got {len(data)}"
        )
    return data


def iter_packets(path: Path, max_packet_bytes: int = MAX_PACKET_BYTES) -> Iterator[OpusDemoPacket]:
    """Yield packets from an opus_demo .bit file.

    opus_demo writes each packet as a 32-bit big-endian byte length, a 32-bit
    big-endian decoder final range, then the raw Opus packet payload.
    """

    offset = 0
    index = 0
    with path.open("rb") as handle:
        while True:
            length_bytes = handle.read(4)
            if not length_bytes:
                break
            if len(length_bytes) != 4:
                raise BitstreamError(
                    f"{path}: truncated packet length at byte {offset}: "
                    f"expected 4 byte(s), got {len(length_bytes)}"
                )

            length = int.from_bytes(length_bytes, "big")
            if length <= 0:
                raise BitstreamError(f"{path}: packet {index}: length must be > 0")
            if length > max_packet_bytes:
                raise BitstreamError(
                    f"{path}: packet {index}: length {length} exceeds max {max_packet_bytes}"
                )

            final_range_offset = offset + 4
            final_range = int.from_bytes(
                _read_exact(handle, path, final_range_offset, 4, "packet final range"),
                "big",
            )
            payload_offset = offset + 8
            payload = _read_exact(handle, path, payload_offset, length, "packet payload")

            yield OpusDemoPacket(
                index=index,
                length=length,
                final_range=final_range,
                payload_offset=payload_offset,
                payload=payload,
            )
            offset = payload_offset + length
            index += 1

    if index == 0:
        raise BitstreamError(f"{path}: empty opus_demo bitstream")


def summarize_bitstream(path: Path, max_packet_bytes: int = MAX_PACKET_BYTES) -> BitstreamSummary:
    packet_count = 0
    payload_bytes = 0
    largest = 0
    last_final_range = 0

    for packet in iter_packets(path, max_packet_bytes=max_packet_bytes):
        packet_count += 1
        payload_bytes += packet.length
        largest = max(largest, packet.length)
        last_final_range = packet.final_range

    return BitstreamSummary(
        packet_count=packet_count,
        payload_bytes=payload_bytes,
        max_packet_bytes=largest,
        last_final_range=last_final_range,
    )


def _cmd_summary(args: argparse.Namespace) -> int:
    summary = summarize_bitstream(args.bitstream, max_packet_bytes=args.max_packet_bytes)
    print(
        f"ok: {args.bitstream}: packets={summary.packet_count} "
        f"payload_bytes={summary.payload_bytes} max_packet_bytes={summary.max_packet_bytes} "
        f"last_final_range=0x{summary.last_final_range:08x}"
    )
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bitstream", type=Path, help="opus_demo .bit file")
    parser.add_argument(
        "--max-packet-bytes",
        type=int,
        default=MAX_PACKET_BYTES,
        help=f"maximum accepted packet payload length, default {MAX_PACKET_BYTES}",
    )
    parser.set_defaults(func=_cmd_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BitstreamError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
