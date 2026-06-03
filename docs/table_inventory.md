# Opus Table Inventory

Baseline: Xiph.Org Opus `v1.5.2`, peeled commit `ddbe48383984d56acd9e1ab6a090c54ca6b735a6`.

Hash format: `tools/check_tables.py` rolling hash, modulo `1_000_000_007`, multiplier `131`, seed `2166136261 % mod`. Signed integer tables are normalized by adding the offset shown before hashing.

| Uya table | Source | Element type | Q-format / unit | Length | Hash | Hash offset |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `CELT_EBAND_5MS` | `celt/modes.c` `eband5ms` | `i16` | MDCT bin band edge | 22 | 417698738 | 32768 |
| `CELT_BAND_ALLOCATION_Q5` | `celt/modes.c` `band_allocation` | `byte` | 1/32 bit/sample | 231 | 305564943 | 0 |
| `CELT_LOGN400` | `celt/static_modes_fixed.h` `logN400` | `i16` | logN, Q0 | 21 | 874482495 | 32768 |
| `CELT_PULSE_CACHE_INDEX50` | `celt/static_modes_fixed.h` `cache_index50` | `i16` | pulse cache offsets by LM/band | 105 | 433495822 | 32768 |
| `CELT_PULSE_CACHE_BITS50` | `celt/static_modes_fixed.h` `cache_bits50` | `byte` | Q3 pulse bit cost rows | 392 | 822794778 | 0 |
| `CELT_PULSE_CACHE_CAPS50` | `celt/static_modes_fixed.h` `cache_caps50` | `byte` | Q3 allocation caps by LM/channel/band | 168 | 474607814 | 0 |
| `CELT_TF_SELECT_TABLE` | `celt/celt.c` `tf_select_table` | `i8` | TF resolution delta | 32 | 428578013 | 32768 |
| `CELT_TRIM_ICDF` | `celt/celt.h` `trim_icdf` | `byte` | iCDF, `ftb=7` | 11 | 441834106 | 0 |
| `CELT_SPREAD_ICDF` | `celt/celt.h` `spread_icdf` | `byte` | iCDF, `ftb=5` | 4 | checked by shape | 0 |
| `CELT_TAPSET_ICDF` | `celt/celt.h` `tapset_icdf` | `byte` | iCDF, `ftb=2` | 3 | checked by shape | 0 |
| `CELT_SMALL_ENERGY_ICDF` | `celt/quant_bands.c` `small_energy_icdf` | `byte` | iCDF, `ftb=2` | 3 | checked by shape | 0 |
| `CELT_TO_OPUS_BANDWIDTH_TABLE` | `celt/celt.h` `toOpusTable` | `byte` | TOC mapping byte | 20 | 745419304 | 0 |
| `CELT_FROM_OPUS_BANDWIDTH_TABLE` | `celt/celt.h` `fromOpusTable` | `byte` | TOC mapping byte | 16 | 111883760 | 0 |
| `CELT_WINDOW_120_Q15` | `celt/static_modes_fixed.h` `window120` | `i16` | Q15 window coefficient | 120 | 992882619 | 32768 |
| `EC_TELL_FRAC_CORRECTION_Q15` | `celt/entcode.c` `correction` | `u32` | Q15 correction | 8 | 253150762 | 0 |
| `EC_BINARY_ICDF` | local entropy helper | `byte` | iCDF, `ftb=8` | 2 | checked by shape | 0 |
| `EC_UNIFORM_3_ICDF` | local entropy helper / SILK uniform | `byte` | iCDF, `ftb=8` | 3 | checked by shape | 0 |
| `EC_UNIFORM_4_ICDF` | local entropy helper / SILK uniform | `byte` | iCDF, `ftb=8` | 4 | checked by shape | 0 |
| `SILK_STEREO_PRED_QUANT_Q13` | `silk/tables_other.c` | `i16` | Q13 predictor | 16 | 953048638 | 32768 |
| `SILK_STEREO_PRED_JOINT_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 25 | 695407113 | 0 |
| `SILK_STEREO_ONLY_CODE_MID_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 2 | checked by shape | 0 |
| `SILK_LBRR_FLAGS_2_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 3 | checked by shape | 0 |
| `SILK_LBRR_FLAGS_3_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 7 | checked by shape | 0 |
| `SILK_LSB_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 2 | checked by shape | 0 |
| `SILK_LTP_SCALE_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 3 | checked by shape | 0 |
| `SILK_TYPE_OFFSET_VAD_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 4 | checked by shape | 0 |
| `SILK_TYPE_OFFSET_NO_VAD_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 2 | checked by shape | 0 |
| `SILK_NLSF_INTERPOLATION_FACTOR_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 5 | checked by shape | 0 |
| `SILK_QUANTIZATION_OFFSETS_Q10` | `silk/tables_other.c` | `i16` | Q10 offset | 4 | checked by source | 32768 |
| `SILK_LTP_SCALES_Q14` | `silk/tables_other.c` | `i16` | Q14 scale | 3 | checked by source | 32768 |
| `SILK_UNIFORM3_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 3 | checked by shape | 0 |
| `SILK_UNIFORM4_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 4 | checked by shape | 0 |
| `SILK_UNIFORM5_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 5 | checked by shape | 0 |
| `SILK_UNIFORM6_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 6 | checked by shape | 0 |
| `SILK_UNIFORM8_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 8 | checked by shape | 0 |
| `SILK_NLSF_EXT_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 7 | checked by shape | 0 |
| `SILK_PITCH_LAG_ICDF` | `silk/tables_pitch_lag.c` | `byte` | iCDF, `ftb=8` | 32 | 133391234 | 0 |
| `SILK_PITCH_DELTA_ICDF` | `silk/tables_pitch_lag.c` | `byte` | iCDF, `ftb=8` | 21 | 232661751 | 0 |
| `SILK_PITCH_CONTOUR_ICDF` | `silk/tables_pitch_lag.c` | `byte` | iCDF, `ftb=8` | 34 | 937829793 | 0 |
| `SILK_PITCH_CONTOUR_NB_ICDF` | `silk/tables_pitch_lag.c` | `byte` | iCDF, `ftb=8` | 11 | checked by shape | 0 |
| `SILK_PITCH_CONTOUR_10_MS_ICDF` | `silk/tables_pitch_lag.c` | `byte` | iCDF, `ftb=8` | 12 | checked by shape | 0 |
| `SILK_PITCH_CONTOUR_10_MS_NB_ICDF` | `silk/tables_pitch_lag.c` | `byte` | iCDF, `ftb=8` | 3 | checked by shape | 0 |
| `SILK_PITCH_CONTOUR_OFFSETS` | `silk/pitch_est_tables.c` | `i16` | decoder contour offsets, flattened by subframe | 210 | checked by boundary decode tests | 32768 |
| `SILK_TRANSITION_LP_B_Q28` | `silk/tables_other.c` | `i32` | Q28, flattened `[5][3]` | 15 | 258613290 | 2147483648 |
| `SILK_TRANSITION_LP_A_Q28` | `silk/tables_other.c` | `i32` | Q28, flattened `[5][2]` | 10 | 268602790 | 2147483648 |
| `SILK_LSB_ICDF` | `silk/tables_other.c` | `byte` | iCDF, `ftb=8` | 2 | 64130662 | 0 |
| `SILK_MAX_PULSES_TABLE` | `silk/tables_pulses_per_block.c` | `byte` | max pulses per rate group | 4 | 294670020 | 0 |
| `SILK_PULSES_PER_BLOCK_ICDF` | `silk/tables_pulses_per_block.c` | `byte` | iCDF, `ftb=8`, flattened `[10][18]` | 180 | 400107309 | 0 |
| `SILK_RATE_LEVELS_ICDF` | `silk/tables_pulses_per_block.c` | `byte` | iCDF, `ftb=8`, flattened `[2][9]` | 18 | 217345873 | 0 |
| `SILK_SHELL_CODE_TABLE0` | `silk/tables_pulses_per_block.c` | `byte` | iCDF split table, `ftb=8` | 152 | 635112220 | 0 |
| `SILK_SHELL_CODE_TABLE1` | `silk/tables_pulses_per_block.c` | `byte` | iCDF split table, `ftb=8` | 152 | 794520531 | 0 |
| `SILK_SHELL_CODE_TABLE2` | `silk/tables_pulses_per_block.c` | `byte` | iCDF split table, `ftb=8` | 152 | 611988706 | 0 |
| `SILK_SHELL_CODE_TABLE3` | `silk/tables_pulses_per_block.c` | `byte` | iCDF split table, `ftb=8` | 152 | 524016143 | 0 |
| `SILK_SHELL_CODE_TABLE_OFFSETS` | `silk/tables_pulses_per_block.c` | `usize` | offsets by total pulse count | 17 | 711768652 | 0 |
| `SILK_SIGN_ICDF` | `silk/tables_pulses_per_block.c` | `byte` | sign iCDF, `ftb=8`, flattened `[6][7]` | 42 | 281612844 | 0 |
| `SILK_LSF_COS_TAB_Q12` | `silk/table_LSF_cos.c` | `i16` | LSF cosine approximation, Q12 | 129 | 518643764 | 32768 |
| `SILK_LTP_PER_INDEX_ICDF` | `silk/tables_LTP.c` | `byte` | periodicity index iCDF, `ftb=8` | 3 | 402142135 | 0 |
| `SILK_LTP_GAIN_ICDF_0` | `silk/tables_LTP.c` | `byte` | LTP gain table 0 iCDF, `ftb=8` | 8 | 31249073 | 0 |
| `SILK_LTP_GAIN_ICDF_1` | `silk/tables_LTP.c` | `byte` | LTP gain table 1 iCDF, `ftb=8` | 16 | 97972471 | 0 |
| `SILK_LTP_GAIN_ICDF_2` | `silk/tables_LTP.c` | `byte` | LTP gain table 2 iCDF, `ftb=8` | 32 | 503242496 | 0 |
| `SILK_LTP_VQ_0_Q7` | `silk/tables_LTP.c` | `i16` | flattened LTP gain codebook 0, Q7 | 40 | 538968179 | 32768 |
| `SILK_LTP_VQ_1_Q7` | `silk/tables_LTP.c` | `i16` | flattened LTP gain codebook 1, Q7 | 80 | 969848199 | 32768 |
| `SILK_LTP_VQ_2_Q7` | `silk/tables_LTP.c` | `i16` | flattened LTP gain codebook 2, Q7 | 160 | 297113135 | 32768 |
| `SILK_NLSF_CB1_NB_MB_Q8` | `silk/tables_NLSF_CB_NB_MB.c` | `byte` | NLSF first-stage vectors, Q8 | 320 | 529135816 | 0 |
| `SILK_NLSF_CB1_NB_MB_WGHT_Q9` | `silk/tables_NLSF_CB_NB_MB.c` | `i16` | NLSF first-stage weights, Q9 | 320 | 666379621 | 32768 |
| `SILK_NLSF_CB1_ICDF_NB_MB` | `silk/tables_NLSF_CB_NB_MB.c` | `byte` | NLSF first-stage iCDF, `ftb=8` | 64 | 705421896 | 0 |
| `SILK_NLSF_CB2_SELECT_NB_MB` | `silk/tables_NLSF_CB_NB_MB.c` | `byte` | packed residual predictor/table selectors | 160 | 799560836 | 0 |
| `SILK_NLSF_CB2_ICDF_NB_MB` | `silk/tables_NLSF_CB_NB_MB.c` | `byte` | residual iCDF rows, `ftb=8` | 72 | 768604607 | 0 |
| `SILK_NLSF_PRED_NB_MB_Q8` | `silk/tables_NLSF_CB_NB_MB.c` | `byte` | residual predictor coefficients, Q8 | 18 | 790540935 | 0 |
| `SILK_NLSF_DELTA_MIN_NB_MB_Q15` | `silk/tables_NLSF_CB_NB_MB.c` | `i16` | minimum NLSF spacing, Q15 | 11 | 421289952 | 32768 |
| `SILK_NLSF_CB1_WB_Q8` | `silk/tables_NLSF_CB_WB.c` | `byte` | NLSF first-stage vectors, Q8 | 512 | 453859076 | 0 |
| `SILK_NLSF_CB1_WB_WGHT_Q9` | `silk/tables_NLSF_CB_WB.c` | `i16` | NLSF first-stage weights, Q9 | 512 | 749453744 | 32768 |
| `SILK_NLSF_CB1_ICDF_WB` | `silk/tables_NLSF_CB_WB.c` | `byte` | NLSF first-stage iCDF, `ftb=8` | 64 | 455523979 | 0 |
| `SILK_NLSF_CB2_SELECT_WB` | `silk/tables_NLSF_CB_WB.c` | `byte` | packed residual predictor/table selectors | 256 | 872852904 | 0 |
| `SILK_NLSF_CB2_ICDF_WB` | `silk/tables_NLSF_CB_WB.c` | `byte` | residual iCDF rows, `ftb=8` | 72 | 988960415 | 0 |
| `SILK_NLSF_PRED_WB_Q8` | `silk/tables_NLSF_CB_WB.c` | `byte` | residual predictor coefficients, Q8 | 30 | 95660651 | 0 |
| `SILK_NLSF_DELTA_MIN_WB_Q15` | `silk/tables_NLSF_CB_WB.c` | `i16` | minimum NLSF spacing, Q15 | 17 | 6214487 | 32768 |

## Deferred Table Families

The following upstream table families are required for later decoder conformance, but are intentionally not imported in this table-only step because their correct validation depends on the module that consumes them. They are inventoried here so later tasks have a fixed source path and verification target.

| Family | Upstream source | Primary consumer | Import target | Verification requirement |
| --- | --- | --- | --- | --- |
| CELT PVQ row data | `celt/cwrs.c` `CELT_PVQ_U_DATA`, `CELT_PVQ_U_ROW` | PVQ/CWRS | `src/opus/celt/cwrs.uya` or `src/opus/celt/tables.uya` | exhaustive small-dimension CWRS plus hash/length for imported rows |
| CELT FFT bit reversal | `celt/static_modes_fixed.h` `fft_bitrev480`, `fft_bitrev240`, `fft_bitrev120`, `fft_bitrev60` | MDCT/FFT | `src/opus/dsp/mdct.uya` or `src/opus/celt/tables.uya` | FFT permutation golden tests and table hash |
| CELT FFT twiddles | `celt/static_modes_fixed.h` `fft_twiddles48000_960`; NE10 variants are architecture-specific and out of first portable backend scope | MDCT/FFT | `src/opus/dsp/mdct.uya` | scalar FFT/MDCT golden tests and table hash |
| CELT MDCT twiddles | `celt/static_modes_fixed.h` `mdct_twiddles960` | MDCT | `src/opus/dsp/mdct.uya` | IMDCT golden tests and overlap-add golden tests |
| CELT coarse energy probability model | `celt/quant_bands.c` `e_prob_model`, `pred_coef`, `beta_coef`, `beta_intra` | energy band quantization | `src/opus/celt/quant_bands.uya` | coarse/fine energy decode vectors and hash/shape checks |
| CELT band decode helper tables | `celt/bands.c` `ordery_table`, `exp2_table8`, `bit_interleave_table`, `bit_deinterleave_table`; `celt/vq.c` `SPREAD_FACTOR` | PVQ band shape decode | `src/opus/celt/quant_bands.uya` or `src/opus/celt/cwrs.uya` | PVQ/band-shape roundtrip and hash/length checks |
| CELT pitch/deemphasis helper constants | `celt/pitch.c` `second_check`; `celt/celt.c` gain tables; `celt/celt_decoder.c` `sinc_filter` | pitch, deemphasis, PLC-adjacent decode | `src/opus/dsp/pitch.uya`, `src/opus/celt/mode.uya`, or decoder modules | targeted DSP golden tests before decoder integration |
| SILK gain tables | `silk/tables_gain.c` | gain decode | `src/opus/silk/tables.uya` plus gain module | gain index decode golden tests, table hash/length |
| SILK pulse shell tables | `silk/tables_pulses_per_block.c`, `silk/shell_coder.c` | pulse decode | `src/opus/silk/tables.uya` plus pulse module | pulse shell decode vectors and iCDF shape checks |
| SILK pitch estimation tables | `silk/pitch_est_tables.c` | encoder-side or later analysis work | encoder/analysis module, not decoder-first path | defer until encoder quality tasks; hash/length if imported |
| SILK resampler ROM | `silk/resampler_rom.c`, `silk/resampler_rom.h` | resampler | `src/opus/dsp/resampler.uya` | resampler golden tests for every supported conversion |
| SILK sigmoid/VAD/control rate tables | `silk/sigm_Q15.c`, `silk/VAD.c`, `silk/control_SNR.c` | encoder/VAD/control | encoder/control modules | defer until encoder/control tasks; hash/length if imported |

Acceptance status: table errors are now caught before full decode by `make test`, which runs `tools/check_tables.uya` for Uya-visible smoke checks and `tools/check_tables.py` for exact source-table length, hash, iCDF shape, and monotonicity checks.
