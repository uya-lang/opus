#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = 1_000_000_007
INIT = 2_166_136_261 % MOD


def array_values(path: str, name: str) -> list[int]:
    text = (ROOT / path).read_text()
    match = re.search(rf"{name}: \[[^\]]+\] = \[(.*?)\];", text, re.S)
    if match is None:
        raise AssertionError(f"missing table {name}")
    body = re.sub(r"//.*", "", match.group(1))
    values = []
    for token in body.replace("\n", " ").split(","):
        token = token.strip()
        if token:
            values.append(int(token))
    return values


def rolling_hash(values: list[int], offset: int = 0) -> int:
    h = INIT
    for value in values:
        h = (h * 131 + value + offset + 1) % MOD
    return h


def assert_icdf(values: list[int], ftb: int = 8) -> None:
    prev = 1 << ftb
    assert values, "empty iCDF"
    for value in values:
        assert value < prev, f"iCDF is not strictly decreasing: {values}"
        prev = value
    assert prev == 0, f"iCDF does not end at zero: {values}"


TABLES = [
    ("src/opus/celt/tables.uya", "CELT_EBAND_5MS", 22, 417698738, 32768, None),
    ("src/opus/celt/tables.uya", "CELT_BAND_ALLOCATION_Q5", 231, 305564943, 0, None),
    ("src/opus/celt/tables.uya", "CELT_LOGN400", 21, 874482495, 32768, None),
    ("src/opus/celt/tables.uya", "CELT_TF_SELECT_TABLE", 32, 428578013, 32768, None),
    ("src/opus/celt/tables.uya", "CELT_TRIM_ICDF", 11, 441834106, 0, 7),
    ("src/opus/celt/tables.uya", "CELT_ENERGY_PROB_MODEL_Q8", 336, 265233239, 0, None),
    ("src/opus/celt/tables.uya", "CELT_TO_OPUS_BANDWIDTH_TABLE", 20, 745419304, 0, None),
    ("src/opus/celt/tables.uya", "CELT_FROM_OPUS_BANDWIDTH_TABLE", 16, 111883760, 0, None),
    ("src/opus/dsp/window.uya", "CELT_WINDOW_120_Q15", 120, 992882619, 32768, None),
    ("src/opus/entropy/cdf.uya", "EC_TELL_FRAC_CORRECTION_Q15", 8, 253150762, 0, None),
    ("src/opus/silk/tables.uya", "SILK_STEREO_PRED_QUANT_Q13", 16, 953048638, 32768, None),
    ("src/opus/silk/tables.uya", "SILK_STEREO_PRED_JOINT_ICDF", 25, 695407113, 0, 8),
    ("src/opus/silk/tables.uya", "SILK_PITCH_LAG_ICDF", 32, 133391234, 0, 8),
    ("src/opus/silk/tables.uya", "SILK_PITCH_DELTA_ICDF", 21, 232661751, 0, 8),
    ("src/opus/silk/tables.uya", "SILK_PITCH_CONTOUR_ICDF", 34, 937829793, 0, 8),
    ("src/opus/silk/tables.uya", "SILK_TRANSITION_LP_B_Q28", 15, 258613290, 2147483648, None),
    ("src/opus/silk/tables.uya", "SILK_TRANSITION_LP_A_Q28", 10, 268602790, 2147483648, None),
    ("src/opus/silk/tables.uya", "SILK_SHELL_CODE_TABLE0", 152, 635112220, 0, None),
    ("src/opus/silk/tables.uya", "SILK_SHELL_CODE_TABLE1", 152, 794520531, 0, None),
    ("src/opus/silk/tables.uya", "SILK_SHELL_CODE_TABLE2", 152, 611988706, 0, None),
    ("src/opus/silk/tables.uya", "SILK_SHELL_CODE_TABLE3", 152, 524016143, 0, None),
    ("src/opus/silk/tables.uya", "SILK_SHELL_CODE_TABLE_OFFSETS", 17, 711768652, 0, None),
    ("src/opus/silk/tables.uya", "SILK_SIGN_ICDF", 42, 281612844, 0, None),
]

EXTRA_ICDFS = [
    ("src/opus/celt/tables.uya", "CELT_SPREAD_ICDF", 5),
    ("src/opus/celt/tables.uya", "CELT_TAPSET_ICDF", 2),
    ("src/opus/celt/tables.uya", "CELT_SMALL_ENERGY_ICDF", 2),
    ("src/opus/silk/tables.uya", "SILK_LBRR_FLAGS_2_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_LBRR_FLAGS_3_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_LSB_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_TYPE_OFFSET_VAD_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_TYPE_OFFSET_NO_VAD_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_NLSF_INTERPOLATION_FACTOR_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_UNIFORM3_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_UNIFORM4_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_UNIFORM5_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_UNIFORM6_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_UNIFORM8_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_NLSF_EXT_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_PITCH_CONTOUR_NB_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_PITCH_CONTOUR_10_MS_ICDF", 8),
    ("src/opus/silk/tables.uya", "SILK_PITCH_CONTOUR_10_MS_NB_ICDF", 8),
]


def main() -> int:
    for path, name, expected_len, expected_hash, offset, ftb in TABLES:
        values = array_values(path, name)
        assert len(values) == expected_len, f"{name} length {len(values)} != {expected_len}"
        assert rolling_hash(values, offset) == expected_hash, f"{name} hash mismatch"
        if ftb is not None:
            assert_icdf(values, ftb)

    for path, name, ftb in EXTRA_ICDFS:
        assert_icdf(array_values(path, name), ftb)

    ebands = array_values("src/opus/celt/tables.uya", "CELT_EBAND_5MS")
    window = array_values("src/opus/dsp/window.uya", "CELT_WINDOW_120_Q15")
    assert all(ebands[i] <= ebands[i + 1] for i in range(len(ebands) - 1))
    assert all(window[i] <= window[i + 1] for i in range(len(window) - 1))
    assert (ebands[0], ebands[-1]) == (0, 100)
    assert (window[0], window[-1]) == (2, 32767)
    print("check_tables: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
