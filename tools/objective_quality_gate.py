#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, InvalidOperation
from pathlib import Path


class ObjectiveQualityGateError(Exception):
    """Raised when objective quality bench output cannot be evaluated."""


@dataclass(frozen=True)
class QualityRow:
    case: str
    variant: str
    mse_q8: int
    snr_q8: int


def _parse_fields(line: str) -> dict[str, str]:
    parts = [part.strip() for part in line.split(",")]
    if not parts or parts[0] != "objective_quality":
        raise ObjectiveQualityGateError(f"not an objective_quality row: {line}")

    fields: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            raise ObjectiveQualityGateError(f"malformed field in row: {part}")
        key, value = part.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def _parse_int(fields: dict[str, str], field: str, line: str) -> int:
    value = fields.get(field)
    if value is None:
        raise ObjectiveQualityGateError(f"missing {field} in row: {line}")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ObjectiveQualityGateError(f"invalid integer field {field}: {value}") from exc
    if parsed < 0:
        raise ObjectiveQualityGateError(f"negative field {field}: {value}")
    return parsed


def parse_rows(text: str) -> dict[tuple[str, str], QualityRow]:
    rows: dict[tuple[str, str], QualityRow] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("objective_quality"):
            continue
        fields = _parse_fields(line)
        case = fields.get("case")
        variant = fields.get("variant")
        if not case:
            raise ObjectiveQualityGateError(f"missing case in row: {line}")
        if not variant:
            raise ObjectiveQualityGateError(f"missing variant in row: {line}")
        row = QualityRow(
            case=case,
            variant=variant,
            mse_q8=_parse_int(fields, "mse_q8", line),
            snr_q8=_parse_int(fields, "snr_q8", line),
        )
        key = (row.case, row.variant)
        if key in rows:
            raise ObjectiveQualityGateError(f"duplicate row for case={row.case} variant={row.variant}")
        rows[key] = row

    if not rows:
        raise ObjectiveQualityGateError("no objective_quality rows found")
    return rows


def _threshold_decimal(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ObjectiveQualityGateError(f"invalid improvement percent: {value}") from exc
    if parsed < 0 or parsed >= 100:
        raise ObjectiveQualityGateError("improvement percent must be >= 0 and < 100")
    return parsed


def required_mse_q8(baseline_mse_q8: int, improvement_percent: Decimal) -> int:
    scaled = Decimal(baseline_mse_q8) * (Decimal(100) - improvement_percent) / Decimal(100)
    return int(scaled.to_integral_value(rounding=ROUND_FLOOR))


def evaluate(
    rows: dict[tuple[str, str], QualityRow],
    baseline_variant: str,
    practical_variant: str,
    min_mse_improvement_percent: Decimal,
    min_snr_improvement_q8: int,
) -> tuple[bool, list[str]]:
    cases = sorted({case for case, _variant in rows})
    if not cases:
        raise ObjectiveQualityGateError("no objective quality cases found")

    messages: list[str] = []
    all_passed = True
    for case in cases:
        baseline = rows.get((case, baseline_variant))
        practical = rows.get((case, practical_variant))
        if baseline is None:
            raise ObjectiveQualityGateError(f"missing baseline row for case={case} variant={baseline_variant}")
        if practical is None:
            raise ObjectiveQualityGateError(f"missing practical row for case={case} variant={practical_variant}")

        required_mse = required_mse_q8(baseline.mse_q8, min_mse_improvement_percent)
        required_snr = baseline.snr_q8 + min_snr_improvement_q8
        mse_passed = practical.mse_q8 <= required_mse
        snr_passed = practical.snr_q8 >= required_snr
        if mse_passed and snr_passed:
            messages.append(
                f"PASS {case}: baseline mse_q8={baseline.mse_q8}, practical mse_q8={practical.mse_q8}, "
                f"required practical mse_q8 <= {required_mse}; baseline snr_q8={baseline.snr_q8}, "
                f"practical snr_q8={practical.snr_q8}, required practical snr_q8 >= {required_snr}"
            )
        else:
            all_passed = False
            messages.append(
                f"FAIL {case}: baseline mse_q8={baseline.mse_q8}, practical mse_q8={practical.mse_q8}, "
                f"requires practical mse_q8 <= {required_mse}; baseline snr_q8={baseline.snr_q8}, "
                f"practical snr_q8={practical.snr_q8}, requires practical snr_q8 >= {required_snr}"
            )
    return all_passed, messages


def _read_input(path: Path | None) -> str:
    if path is None:
        return sys.stdin.read()
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ObjectiveQualityGateError(f"cannot read input: {path}") from exc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Evaluate objective quality bench baseline/practical rows.")
    parser.add_argument("--input", type=Path, help="Read objective bench output from a file instead of stdin.")
    parser.add_argument("--baseline-variant", default="baseline_complexity0")
    parser.add_argument("--practical-variant", default="practical_complexity10")
    parser.add_argument("--min-mse-improvement-percent", default="1.0")
    parser.add_argument("--min-snr-improvement-q8", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        threshold = _threshold_decimal(args.min_mse_improvement_percent)
        if args.min_snr_improvement_q8 < 0:
            raise ObjectiveQualityGateError("min-snr-improvement-q8 must be non-negative")
        rows = parse_rows(_read_input(args.input))
        passed, messages = evaluate(
            rows,
            args.baseline_variant,
            args.practical_variant,
            threshold,
            args.min_snr_improvement_q8,
        )
    except ObjectiveQualityGateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for message in messages:
        print(message)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
