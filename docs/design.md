# 纯 Uya 重构 Opus 详细设计

状态：设计版 v0.1
目标实现语言：纯 Uya
目标项目：`opus`
核心目标：用 Uya 从零实现可互操作、可验证、可优化的 Opus 编解码器核心。

命名冻结：

- 项目名称：`opus`。
- Uya 库/模块根名称：`opus`，源码根固定为 `src/opus/`。
- CLI 工具名称：`uopusdec`、`uopusenc`、`uopusinfo`，输出路径固定为 `bin/`。
- `opusdec`、`opusenc`、`opusinfo` 只作为外部参考工具名称或源码文件名使用，避免和系统 libopus CLI 混淆。

参考规范：

- RFC 6716: Definition of the Opus Audio Codec, https://www.rfc-editor.org/rfc/rfc6716
- RFC 8251: Updates to the Opus Audio Codec, https://www.rfc-editor.org/rfc/rfc8251
- RFC 7845: Ogg Encapsulation for the Opus Audio Codec, https://www.rfc-editor.org/rfc/rfc7845
- RFC 7587: RTP Payload Format for the Opus Speech and Audio Codec, https://www.rfc-editor.org/rfc/rfc7587
- libopus upstream/API 文档，https://opus-codec.org/docs/

## 1. 项目定位

本项目不是对 libopus 的 C 代码做逐文件搬运，而是用 Uya 重新表达 Opus 的规范模型、状态机、定点算术、码流解析和编解码管线。

一句话目标：

> 在保持 Opus 码流互操作和解码行为一致的前提下，把历史 C 实现重构为模块边界清晰、内存模型显式、测试可分层推进的纯 Uya 实现。

第一阶段的成功标准：

- 能解析 RFC 6716 定义的合法 Opus packet。
- 能通过官方/自建 decoder conformance vectors。
- 对 decoder 输出做到 bit-exact 或在规范允许的误差内一致。
- 对错误包、截断包、非法 padding、非法 frame count 给出稳定错误。
- 核心编解码路径不依赖 libopus、C/C++/Rust/Go/Python 业务实现。

第二阶段的成功标准：

- 提供可用 encoder，覆盖 VoIP、music、low-delay 三类应用。
- 输出码流能被 libopus、浏览器/WebRTC、FFmpeg、GStreamer 等解码。
- 在语音质量、音乐质量、延迟和 CPU 成本之间提供可调策略。
- 支持 Ogg Opus 文件读写和 RTP/WebRTC payload 基础互操作。

## 2. 范围和非目标

### 2.1 范围

必须实现：

- Opus packet TOC 和 frame parser。
- Range arithmetic entropy decoder/encoder。
- SILK-only decoder 和 encoder。
- CELT-only decoder 和 encoder。
- Hybrid decoder 和 encoder。
- Mono/stereo packet 支持。
- PLC packet loss concealment。
- In-band FEC/LBRR 解码路径。
- Repacketizer。
- Multistream API，支持 surround mapping 的基础结构。
- Ogg Opus 封装读写。
- RTP Opus payload parser/writer。
- 兼容 libopus 主要 public API 语义的 Uya 原生 API。

优先但可分期实现：

- DTX。
- 音频带宽自动检测。
- 复杂度调节。
- CELT/SILK SIMD 热路径。
- 浮点输入输出便捷 API。
- WebAssembly/embedded profile。

### 2.2 非目标

第一版不做：

- 不把 libopus C 源码嵌入项目作为核心实现。
- 不用外部 C 库完成 SILK/CELT 算法主体。
- 不追求初版 encoder 与 libopus 做逐样本一致；encoder 只要求码流合法、质量逐步逼近。
- 不先做完整 C ABI 复刻；先冻结 Uya API，再按需要提供兼容薄层。
- 不把 Ogg/RTP/WebRTC 网络栈混入 codec core。

## 3. 纯 Uya 实现约束

核心实现必须是 Uya。C99 后端只是 Uya 编译产物，不是业务实现语言。

允许边界：

- Uya 标准库中的内存、IO、数学、测试、线程、时间等基础能力。
- OS/libc FFI 仅用于文件读写、时间、随机测试输入、命令行工具、测试 harness。
- 可选 differential test 工具可以调用系统安装的 `opus_demo`、`opusenc`、`opusdec` 或 libopus CLI，但它们不能进入核心库依赖。

禁止边界：

- 禁止在 `src/opus/**` 中用 C/C++/Rust/Go/Python 实现编解码主体。
- 禁止把 libopus 作为运行时依赖。
- 禁止用浮点近似替换规范要求的定点解码路径。
- 禁止在 packet parser 中容忍非规范输入后继续产生未定义状态。

Uya 特性使用原则：

- 使用 `!T` 表达所有可恢复错误：非法码流、截断、参数越界、内存不足、状态错误。
- 使用固定数组保存 codec 常量、band table、CDF table、窗函数、MDCT twiddle。
- 使用切片 `&[T]` / `&[const T]` 表达输入输出 buffer，禁止热路径隐式分配。
- 使用 `struct` 显式承载 decoder/encoder state，禁止全局可变状态。
- 使用 `defer`/显式 release 管理 arena、文件句柄和测试资源。
- 使用 `@vector` 作为后期 SIMD 优化出口，标量实现必须先保持正确。
- 使用 `interface` 抽象 packet source、PCM sink、container reader/writer，但 codec core 不依赖容器接口。

## 4. Opus 基础模型

Opus packet 由一个 TOC byte 加上一个或多个 compressed frames 构成。TOC byte 包含：

- `config`: 5 bits，决定 mode、bandwidth、frame duration。
- `s`: 1 bit，单声道或立体声。
- `c`: 2 bits，决定 packet frame layout。

Opus 有三类编码模式：

- SILK-only：线性预测语音编码，主要服务窄带到宽带语音。
- CELT-only：MDCT/频域编码，主要服务音乐和低延迟。
- Hybrid：低频使用 SILK，高频使用 CELT，用于宽带以上语音/音乐过渡场景。

音频带宽：

- NB: narrowband，约 4 kHz。
- MB: mediumband，约 6 kHz。
- WB: wideband，约 8 kHz。
- SWB: super-wideband，约 12 kHz。
- FB: fullband，约 20 kHz。

规范 frame duration：

- 2.5 ms。
- 5 ms。
- 10 ms。
- 20 ms。
- 40 ms。
- 60 ms。

工程中统一使用 48 kHz 作为 decoder PCM 主路径。常量：

```text
MAX_CHANNELS = 2
MAX_FRAME_MS = 60
MAX_PACKET_MS = 120
MAX_FRAME_SAMPLES_48K = 2880
MAX_PACKET_SAMPLES_48K = 5760
MAX_FRAME_BYTES = 1275
```

## 5. 架构总览

```text
┌────────────────────────────────────────────────────────────┐
│ Public API                                                  │
│ decoder / encoder / repacketizer / multistream              │
└──────────────────────────────┬─────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────┐
│ Packet Layer                                                │
│ TOC parser / frame split / padding / validation             │
└──────────────────────────────┬─────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────┐
│ Codec Dispatch                                              │
│ SILK-only / CELT-only / Hybrid / PLC / FEC                  │
└───────────────┬──────────────────────────────┬─────────────┘
                │                              │
┌───────────────▼──────────────┐ ┌─────────────▼─────────────┐
│ SILK                          │ │ CELT                       │
│ LP decoder/encoder            │ │ MDCT/PVQ decoder/encoder   │
└───────────────┬──────────────┘ └─────────────┬─────────────┘
                │                              │
┌───────────────▼──────────────────────────────▼─────────────┐
│ Common DSP                                                  │
│ fixed-point math / resampler / filters / MDCT / entropy     │
└──────────────────────────────┬─────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────┐
│ Platform Boundary                                           │
│ Ogg / RTP / CLI / tests / benches / optional FFI wrappers    │
└────────────────────────────────────────────────────────────┘
```

架构原则：

- Packet parser 只负责把 packet 拆成 frame，不解码音频。
- Entropy coder 是独立基础库，SILK/CELT 只能通过清晰 API 消费。
- SILK 和 CELT 互不直接依赖，通过 hybrid glue 组合。
- Decoder state 和 encoder state 分离，避免为 encoder 复杂度污染 decoder。
- 所有规范表以 Uya 常量表表达，不从外部文件动态加载。
- 所有跨模块数据结构必须有明确 Q-format、单位和取值范围。

## 6. 建议源码布局

```text
src/
  opus/
    main.uya                         # 可选 CLI 入口或 smoke 入口
    core/
      constants.uya                  # 全局常量
      errors.uya                     # error 命名
      types.uya                      # Bandwidth/Mode/Application 等公共类型
      qformat.uya                    # Q-format 类型别名与说明
      saturate.uya                   # 定点饱和 arithmetic
      bitops.uya                     # clz/celt_ilog/bit packing helper
      buffer.uya                     # PCM/packet buffer helper
    packet/
      toc.uya                        # TOC parse/config table
      frame.uya                      # packet frame split
      repacketizer.uya               # repacketizer
      validate.uya                   # packet legality check
    entropy/
      range_dec.uya                  # range decoder
      range_enc.uya                  # range encoder
      cdf.uya                        # CDF helper
      laplace.uya                    # Laplace entropy helper
      uint.uya                       # uniform/logp/icdf helpers
    dsp/
      math.uya                       # multiply/shift/round/mac
      filters.uya                    # biquad/FIR/IIR/LPC helpers
      pitch.uya                      # pitch correlation/search shared pieces
      resampler.uya                  # SILK/CELT sample-rate conversion
      mdct.uya                       # CELT MDCT
      fft.uya                        # small FFT backend if needed
      bands.uya                      # CELT band layout utilities
      window.uya                     # overlap/window tables
    silk/
      tables.uya
      state.uya
      decoder.uya
      decoder_control.uya
      entropy_decode.uya
      nlsf.uya
      lpc.uya
      ltp.uya
      pitch.uya
      pulses.uya
      shell_coder.uya
      stereo.uya
      plc.uya
      fec.uya
      encoder.uya
      analysis.uya
      nsq.uya
      vad.uya
    celt/
      tables.uya
      mode.uya
      state.uya
      decoder.uya
      encoder.uya
      bands.uya
      cwrs.uya
      quant_bands.uya
      rate.uya
      pitch.uya
      mdct_bridge.uya
      plc.uya
      postfilter.uya
      deemphasis.uya
    hybrid/
      decoder.uya
      encoder.uya
      glue.uya
      delay.uya
    api/
      decoder.uya
      encoder.uya
      multistream.uya
      ctl.uya
      pcm.uya
    container/
      ogg_opus.uya
      rtp_opus.uya
    cli/
      opusinfo.uya
      opusdec.uya
      opusenc.uya
tests/
  test_packet_*.uya
  test_entropy_*.uya
  test_silk_*.uya
  test_celt_*.uya
  test_decode_vectors.uya
  vectors/
bench/
  bench_decode_*.uya
  bench_entropy_*.uya
docs/
  design.md
  todo.md
```

模块依赖方向：

```text
api -> packet -> entropy
api -> silk -> entropy + dsp + core
api -> celt -> entropy + dsp + core
api -> hybrid -> silk + celt + dsp + core
container -> api + packet
cli -> api + container
tests -> all
```

`core`、`entropy`、`dsp` 不能依赖 `api`、`container`、`cli`。

## 7. 公共 API 设计

### 7.1 类型

```uya
export enum OpusMode {
    SilkOnly,
    CeltOnly,
    Hybrid
}

export enum OpusBandwidth {
    Narrowband,
    Mediumband,
    Wideband,
    SuperWideband,
    Fullband
}

export enum OpusApplication {
    Voip,
    Audio,
    RestrictedLowDelay
}

export struct PacketInfo {
    mode: OpusMode,
    bandwidth: OpusBandwidth,
    channels: i32,
    frame_count: i32,
    frame_duration_samples_48k: i32,
    packet_duration_samples_48k: i32,
    has_padding: bool
}
```

### 7.2 Decoder API

```uya
export struct OpusDecoderConfig {
    sample_rate_hz: i32,             // 8000/12000/16000/24000/48000
    channels: i32,                   // 1 or 2
    enable_fec: bool
}

export struct OpusDecoder {
    config: OpusDecoderConfig,
    active_mode: OpusMode,
    silk: SilkDecoderState,
    celt: CeltDecoderState,
    hybrid: HybridGlueState,
    sample_path: DecoderSamplePath,
    last_packet: LastPacketState
}

export fn decoder_init(config: OpusDecoderConfig) !OpusDecoder;

export fn decoder_get_packet_info(packet: &[const byte]) !PacketInfo;

export fn decoder_decode_i16(
    decoder: &OpusDecoder,
    packet: &[const byte],
    pcm: &[i16],
    frame_size: i32,
    decode_fec: bool
) !i32;
```

返回值为实际写入的每声道 sample 数。`pcm` 使用 interleaved layout：

```text
mono:   s0, s1, s2, ...
stereo: l0, r0, l1, r1, ...
```

Decoder state 布局约束：

- `OpusDecoder` 不保存完整的第三份 hybrid codec state；hybrid 只保存 delay、budget split、merge 等 glue state，并复用 SILK/CELT state。
- 大型临时数组进入 mode state 或 `DecoderScratch`，初始化后复用，单次 decode 不清零无关 mode 的大 buffer。
- 如果后续需要支持更紧的 embedded profile，`SilkDecoderState`/`CeltDecoderState` 可以拆成 history state 与 scratch，scratch 由调用方或 decoder pool 提供。

采样率路径：

- codec 内部优先按 packet 对应的原生路径工作；SILK-only 不应先无条件升到 48 kHz 再降到 API 输出采样率。
- Hybrid/CELT merge 需要 48 kHz glue buffer 时，只在 glue 边界做一次转换。
- `sample_rate_hz == 48000` 是零额外重采样 fast path；其他输出采样率最多经过一次 final resample。

空 packet 或丢包路径：

- `packet.len == 0` 表示 packet loss concealment。
- `decode_fec == true` 时尝试使用下一包中的 FEC/LBRR 信息恢复上一帧。
- 如果没有可用 FEC，则走 PLC。

### 7.3 Encoder API

```uya
export struct OpusEncoderConfig {
    sample_rate_hz: i32,
    channels: i32,
    application: OpusApplication,
    bitrate_bps: i32,
    complexity: i32,
    signal_hint: OpusSignalHint,
    bandwidth: OpusBandwidth,
    use_vbr: bool,
    use_inband_fec: bool,
    packet_loss_perc: i32,
    dtx: bool
}

export struct OpusEncoder {
    config: OpusEncoderConfig,
    analysis: EncoderAnalysisState,
    silk: SilkEncoderState,
    celt: CeltEncoderState,
    hybrid: HybridEncoderState
}

export fn encoder_init(config: OpusEncoderConfig) !OpusEncoder;

export fn encoder_encode_i16(
    encoder: &OpusEncoder,
    pcm: &[const i16],
    frame_size: i32,
    packet_out: &[byte]
) !i32;
```

初版 encoder 可按 profile 分级：

- `EncoderLevel.Basic`: 固定 bandwidth、固定 mode、合法码流优先。
- `EncoderLevel.Practical`: VBR、语音/音乐粗分类、基本 FEC。
- `EncoderLevel.Quality`: 完整 rate control、mode switching、复杂度调节。

### 7.4 CTL API

Uya 不需要完全复刻 libopus 的 integer CTL 宏风格。建议提供类型安全配置接口：

```uya
export fn encoder_set_bitrate(encoder: &OpusEncoder, bitrate_bps: i32) !void;
export fn encoder_set_complexity(encoder: &OpusEncoder, complexity: i32) !void;
export fn encoder_set_inband_fec(encoder: &OpusEncoder, enabled: bool) !void;
export fn encoder_set_packet_loss_perc(encoder: &OpusEncoder, perc: i32) !void;
export fn decoder_set_gain_q8(decoder: &OpusDecoder, gain_q8: i32) !void;
```

后续如果需要 C ABI，可在 `api/ctl_compat.uya` 中提供兼容枚举。

## 8. Packet Layer 设计

### 8.1 TOC config 表

`packet/toc.uya` 用常量表描述 32 个 config：

```text
config 0..3:   SILK NB,  10/20/40/60 ms
config 4..7:   SILK MB,  10/20/40/60 ms
config 8..11:  SILK WB,  10/20/40/60 ms
config 12..13: Hybrid SWB, 10/20 ms
config 14..15: Hybrid FB,  10/20 ms
config 16..19: CELT NB,  2.5/5/10/20 ms
config 20..23: CELT WB,  2.5/5/10/20 ms
config 24..27: CELT SWB, 2.5/5/10/20 ms
config 28..31: CELT FB,  2.5/5/10/20 ms
```

建议结构：

```uya
export struct TocConfig {
    mode: OpusMode,
    bandwidth: OpusBandwidth,
    frame_duration_samples_48k: i32,
    silk_frame_ms: i32,
    celt_size_code: i32
}
```

### 8.2 Frame split

TOC 的 `c` 字段决定 frame layout：

- Code 0: 1 frame，剩余 packet 全部属于该 frame。
- Code 1: 2 frames，CBR，两个 frame 等长。
- Code 2: 2 frames，VBR，第一个 frame 长度显式编码。
- Code 3: arbitrary number of frames，支持 padding、VBR/CBR 标志、frame count。

`PacketFrames` 不复制 frame payload，只保存切片：

```uya
export struct PacketFrame {
    data: &[const byte]
}

export struct PacketFrames {
    info: PacketInfo,
    frames: [PacketFrame: MAX_FRAMES_PER_PACKET],
    frame_count: i32
}
```

校验规则：

- packet 至少 1 byte。
- frame count 不能让 packet 总 duration 超过 120 ms。
- 每个 frame 长度必须在规范允许范围内。
- padding 字节只能以规范方式出现。
- VBR length 编码必须 canonical，不能越界读取。
- frame split 完成后不能遗留未消费 payload。

## 9. Entropy Range Coder

Opus 使用 range coder 编码大部分 SILK/CELT side information 和量化符号。Uya 实现必须和规范算法保持整数行为一致。

### 9.1 Decoder state

```uya
export struct EntropyDecoder {
    buf: &[const byte],
    storage: i32,
    end_offs: i32,
    end_window: u32,
    nend_bits: i32,
    nbits_total: i32,
    offs: i32,
    rng: u32,
    val: u32,
    ext: u32,
    error: bool
}
```

核心 API 分两层：初始化和最终校验返回 Uya error；符号级热路径只更新 `error` 标志，避免每个 entropy symbol 都走 `!T` 错误传播。

```uya
export fn ec_dec_init(buf: &[const byte]) !EntropyDecoder;
export fn ec_decode(dec: &EntropyDecoder, ft: u32) u32;
export fn ec_decode_bin(dec: &EntropyDecoder, bits: i32) u32;
export fn ec_dec_update(dec: &EntropyDecoder, fl: u32, fh: u32, ft: u32) void;
export fn ec_dec_icdf(dec: &EntropyDecoder, icdf: &[const u8], ftb: i32) i32;
export fn ec_dec_bit_logp(dec: &EntropyDecoder, logp: i32) bool;
export fn ec_dec_uint(dec: &EntropyDecoder, ft: u32) u32;
export fn ec_dec_bits(dec: &EntropyDecoder, bits: i32) u32;
export fn ec_tell(dec: &EntropyDecoder) i32;
export fn ec_tell_frac(dec: &EntropyDecoder) i32;
export fn ec_dec_check(dec: &EntropyDecoder) !void;
```

热路径约束：

- 解码函数发现截断、非法 `ft`、越界 raw bits 时设置 `dec.error = true`，并返回有界默认值。
- SILK/CELT frame 解码在消费关键 side information 后检查一次 `ec_dec_check`，public API 返回 `OpusRangeCoderError`。
- 如果某个调用点必须立即停止以保护输出 buffer，可在模块边界手动检查 `dec.error`，但不把 `!T` 放进 inner loop。

### 9.2 Encoder state

Encoder 与 decoder 共用概率表 helper，但状态独立：

```uya
export struct EntropyEncoder {
    buf: &[byte],
    storage: i32,
    offs: i32,
    end_offs: i32,
    end_window: u32,
    nend_bits: i32,
    nbits_total: i32,
    rng: u32,
    val: u32,
    rem: i32,
    ext: i32,
    error: bool
}
```

### 9.3 验证策略

必须先完成 entropy coder 的独立 roundtrip：

- `ec_enc_uint`/`ec_dec_uint`。
- `ec_enc_icdf`/`ec_dec_icdf`。
- `ec_enc_bit_logp`/`ec_dec_bit_logp`。
- raw bits at end of stream。
- boundary cases：空 buffer、1 byte buffer、最大 `ft`、接近 range normalization 边界。

只有 entropy coder 稳定后，才允许进入 SILK/CELT 主体调试。

## 10. Common DSP 和定点算术

### 10.1 Q-format 约定

所有定点值必须在字段名或注释中标明 Q-format。

推荐约定：

```text
q7   : i16/i32, 7 fractional bits
q8   : i16/i32, 8 fractional bits
q10  : i16/i32, 10 fractional bits
q12  : i16/i32, 12 fractional bits
q14  : i16/i32, 14 fractional bits
q15  : i16/i32, 15 fractional bits
q16  : i32, 16 fractional bits
q24  : i32, 24 fractional bits
q31  : i32, 31 fractional bits
```

命名规则：

- 变量名后缀使用 `_q8`、`_q15`、`_q16`。
- 函数名中包含输出 Q-format，例如 `mul_q15_to_q15`。
- 表名包含 Q-format，例如 `silk_lsf_cos_table_q12`。

### 10.2 饱和 arithmetic

`core/saturate.uya` 提供唯一入口：

```uya
export fn sat16(x: i32) i16;
export fn sat32(x: i64) i32;
export fn add_sat16(a: i16, b: i16) i16;
export fn add_sat32(a: i32, b: i32) i32;
export fn sub_sat32(a: i32, b: i32) i32;
export fn mul_16_16(a: i16, b: i16) i32;
export fn mul_32_32_q31(a: i32, b: i32) i32;
export fn rshift_round(x: i32, shift: i32) i32;
```

规则：

- 禁止热路径散落手写 magic shift。
- 禁止隐式依赖 C signed overflow。
- 对所有可能溢出的加减乘先定义饱和或 wrapping 语义。
- `i64` 中间量只在必要处使用，避免无意识拖慢 embedded profile。

### 10.3 表和代码生成

Opus 有大量 CDF、窗函数、band table、codebook 表。Uya 项目中必须以 `.uya` 常量表保存。

允许后续增加生成器：

```text
tools/gen_tables.uya
tools/check_tables.uya
```

生成器输出必须纳入版本库，并由测试校验 hash，避免运行时依赖生成。

## 11. SILK Decoder 设计

SILK 负责语音低频和中频部分，核心是线性预测、长期预测、脉冲解码和 LPC synthesis。

### 11.1 状态结构

```uya
export struct SilkDecoderState {
    fs_khz: i32,
    nb_subfr: i32,
    frame_length: i32,
    subfr_length: i32,
    lpc_order: i32,
    prev_gain_q16: i32,
    first_frame_after_reset: bool,
    loss_count: i32,
    last_sigtype: i32,
    lag_prev: i32,
    out_buf: [i16: SILK_MAX_FRAME_LENGTH],
    s_lpc_q14: [i32: SILK_MAX_LPC_ORDER],
    s_ltp_q16: [i32: SILK_MAX_LTP_BUF_LENGTH],
    plc: SilkPlcState,
    stereo: SilkStereoState
}
```

### 11.2 解码流程

每个 SILK frame：

1. 初始化/更新 frame 参数：采样率、subframe count、LPC order。
2. 解码 VAD/LBRR flags。
3. 解码 side information：
   - signal type。
   - quantization offset type。
   - gain indices。
   - NLSF indices。
   - pitch lag 和 contour。
   - LTP coefficients。
   - LTP scaling。
   - seed。
4. 解码 pulses：
   - rate level。
   - sum pulses per shell block。
   - shell coder。
   - LSB extension。
   - sign decode。
5. 反量化和重建 excitation。
6. LTP synthesis。
7. LPC synthesis。
8. stereo mid/side reconstruction。
9. 必要时做一次 resample/upmix：SILK-only 走 API 目标采样率 fast path，Hybrid 才进入 48 kHz glue buffer。
10. 更新 PLC/FEC state。

### 11.3 模块职责

`silk/entropy_decode.uya`：

- 只从 `EntropyDecoder` 读取 side info。
- 不执行 synthesis。
- 输出 `SilkDecoderControl`。

`silk/pulses.uya` 和 `silk/shell_coder.uya`：

- 解码 pulse counts。
- 解码 shell blocks。
- 解码 signs。
- 输出 excitation index buffer。

`silk/nlsf.uya`：

- NLSF entropy decode。
- NLSF stabilization。
- NLSF -> LPC coefficient conversion。
- interpolation。

`silk/ltp.uya`：

- LTP coefficient decode。
- LTP scaling。
- long-term prediction synthesis。

`silk/lpc.uya`：

- short-term LPC synthesis。
- bandwidth expansion。
- residual energy helper。

`silk/plc.uya`：

- lost frame concealment。
- random excitation。
- pitch-based extrapolation。
- energy decay。

`silk/fec.uya`：

- LBRR data detection。
- delayed FEC decode。
- integration with packet loss API。

### 11.4 SILK Encoder

初版 SILK encoder 分三层：

- Level 1：合法码流 encoder，只支持固定 WB/20ms/mono，质量先不追求。
- Level 2：语音可用 encoder，加入 VAD、pitch analysis、gain control、NLSF quantization。
- Level 3：质量 encoder，加入 rate-distortion search、LBRR、DTX、stereo。

关键模块：

- `silk/vad.uya`: voice activity detection。
- `silk/analysis.uya`: LPC/NLSF/pitch/gain analysis。
- `silk/nsq.uya`: noise shaping quantizer。
- `silk/encoder.uya`: mode decision 和 entropy encode。

## 12. CELT Decoder 设计

CELT 负责低延迟频域编码和高频部分，核心是 MDCT、band energy、PVQ/cwrs、bit allocation 和 overlap-add。

### 12.1 状态结构

```uya
export struct CeltDecoderState {
    channels: i32,
    start_band: i32,
    end_band: i32,
    overlap: i32,
    downsample: i32,
    mode: CeltMode,
    old_ebands_q8: [i16: CELT_MAX_BANDS * MAX_CHANNELS],
    old_band_e_q8: [i16: CELT_MAX_BANDS * MAX_CHANNELS],
    old_loge_q8: [i16: CELT_MAX_BANDS * MAX_CHANNELS],
    preemph_mem: [i32: MAX_CHANNELS],
    decode_mem: [i32: CELT_DECODE_MEM * MAX_CHANNELS],
    rng: u32,
    loss_count: i32
}
```

### 12.2 解码流程

每个 CELT frame：

1. 根据 TOC 和 packet budget 初始化 mode、LM、M、short blocks。
2. 解码 transient flag。
3. 解码 intra-energy flag。
4. 解码 coarse energy。
5. 解码 TF changes。
6. 解码 spreading decision。
7. 执行 bit allocation。
8. 解码 fine energy。
9. 解码 pulse/cwrs PVQ band shape。
10. 解码 anti-collapse 信息。
11. 解码 final fine energy。
12. denormalize bands。
13. inverse MDCT。
14. overlap-add。
15. deemphasis。
16. 更新 loss concealment state。

### 12.3 模块职责

`celt/mode.uya`：

- frame size、overlap、eBands、allocation vectors。
- 禁止动态构建不可变 mode 表。

`celt/quant_bands.uya`：

- coarse energy decode/encode。
- fine energy decode/encode。
- energy prediction state。

`celt/rate.uya`：

- bit allocation。
- pulses per band。
- remaining bits accounting。

`celt/cwrs.uya`：

- algebraic codebook encode/decode。
- `icwrs`/`encode_pulses`/`decode_pulses`。

`celt/bands.uya`：

- band normalization/denormalization。
- folding。
- stereo intensity。
- anti-collapse。

`celt/mdct_bridge.uya`：

- glue 到 `dsp/mdct.uya`。
- 管理 overlap/window。

`celt/plc.uya`：

- frequency-domain PLC。
- pitch-based concealment。

### 12.4 CELT Encoder

CELT encoder 难点在 rate allocation、PVQ search 和 transient decision。分阶段：

- Basic：固定 CELT-only FB/20ms，简单能量量化和合法 PVQ。
- Practical：支持 2.5/5/10/20ms、VBR、瞬态检测、stereo intensity。
- Quality：接近 libopus 的 mode switching、pitch/postfilter、复杂度选项。

## 13. Hybrid Glue

Hybrid 模式把 SILK 低频和 CELT 高频组合。设计上要把它作为独立模块，不让 SILK/CELT 相互穿透。

`hybrid/decoder.uya` 负责：

- 解析 hybrid config。
- 为 SILK 分配低频 frame budget。
- 为 CELT 分配高频 range decoder budget。
- 管理 SILK/CELT 采样率和延迟补偿。
- 合成低频和高频输出。
- 处理 hybrid mode 下的 PLC/FEC 状态。

关键风险：

- SILK 与 CELT 内部延迟不同。
- 高低频交界处能量不连续会产生明显伪影。
- FEC 只覆盖部分语音信息时，hybrid output 需要稳定 fallback。
- mode switching 需要平滑历史状态。

## 14. Multistream 和 Surround

Multistream 作为 API 层功能，不进入单流 codec core。

```uya
export struct MultistreamDecoder {
    stream_count: i32,
    coupled_count: i32,
    channel_count: i32,
    mapping: [u8: OPUS_MAX_CHANNELS],
    decoders: MultistreamDecoderPool
}
```

`MultistreamDecoderPool` 只为实际 `stream_count` 持有 decoder slots，初始化时不得清零或构造 `OPUS_MAX_STREAMS` 个完整 `OpusDecoder`。在不允许 heap 的 profile 中，pool 由调用方提供固定容量 storage；通用 API 可以在 init 阶段分配一次，但 decode 热路径保持零分配。

职责：

- 根据 mapping family 拆分 packet。
- 对 coupled stream 输出 stereo。
- 对 uncoupled stream 输出 mono。
- 按 mapping 重排到最终 interleaved PCM。

优先支持：

- mapping family 0: mono/stereo。
- mapping family 1: Vorbis channel order surround。
- mapping family 255: explicit mapping。

## 15. Ogg Opus

Ogg Opus 是容器层，放在 `container/ogg_opus.uya`。

必须支持：

- `OpusHead` 解析/编码。
- `OpusTags` 解析/编码。
- pre-skip。
- granule position。
- end trimming。
- page lacing。
- CRC 校验。
- chained logical bitstreams 的基本处理。

不允许：

- Ogg parser 直接访问 SILK/CELT state。
- container error 与 codec bitstream error 混淆。

## 16. RTP Opus

RTP payload 层放在 `container/rtp_opus.uya`。

必须支持：

- payload packet 解析和输出。
- maxptime/ptime 约束校验。
- DTX 空帧语义。
- FEC decode hint。
- stereo/sprop-stereo 参数映射。

RTP header 本身可由上层网络库管理，本模块只处理 Opus payload 和 SDP 参数 helper。

## 17. 内存模型

### 17.1 热路径零分配

Decoder/encoder 初始化后，单次 decode/encode 不应 heap allocate。

规则：

- packet parser 返回输入 packet 的切片视图。
- frame 临时 buffer 使用 state 内固定数组或调用方 scratch。
- MDCT、resampler、PLC 历史 buffer 在 state 中持有。
- Ogg/RTP/CLI 可以使用 arena，但 codec core 不依赖 arena。

### 17.2 Buffer ownership

输入：

- `packet: &[const byte]` 由调用者拥有。
- `pcm_in: &[const i16]` 由调用者拥有。

输出：

- `pcm_out: &[i16]` 由调用者提供，codec 写入。
- `packet_out: &[byte]` 由调用者提供，encoder 写入。

状态：

- `OpusDecoder`/`OpusEncoder` 可按值初始化，但热路径通过 `&` 传入。
- 状态结构不保存调用者 packet/pcm slice 的长期引用。

### 17.3 State footprint 和 scratch

State 布局必须把常驻 history 和大块临时 scratch 分开：

- 单流 decoder 只保留 mode switching 和 PLC/FEC 必需的 history。
- Hybrid glue 不复制 SILK/CELT 的长历史 buffer。
- Multistream 按实际 stream 数持有 decoder slots，不能因为 `OPUS_MAX_STREAMS` 的上限放大普通 mono/stereo 场景的初始化和 cache 成本。
- 大块 scratch 在 decoder/encoder init 或 caller-provided storage 中准备好，decode/encode 中复用，不按 frame 清零整块 buffer。

## 18. 错误模型

统一在 `core/errors.uya` 命名：

```uya
error OpusBadArg;
error OpusBufferTooSmall;
error OpusInvalidPacket;
error OpusInvalidFrameCount;
error OpusInvalidFrameSize;
error OpusInvalidPadding;
error OpusInvalidToc;
error OpusRangeCoderError;
error OpusUnsupportedConfig;
error OpusUnimplemented;
error OpusInternalInvariant;
```

约定：

- 参数错误返回 `OpusBadArg`。
- 输出 buffer 不够返回 `OpusBufferTooSmall`。
- 输入 packet 非法返回 `OpusInvalidPacket` 或更具体错误。
- 规范支持但当前阶段未实现返回 `OpusUnimplemented`。
- 代码不变量被破坏返回 `OpusInternalInvariant`，并在测试中视为 bug。

## 19. 测试策略

测试按层推进：

```text
packet parser tests
  -> entropy coder roundtrip
  -> fixed-point math golden tests
  -> CELT unit tests
  -> SILK unit tests
  -> full decoder vectors
  -> PLC/FEC behavior tests
  -> encoder legality tests
  -> container interoperability tests
  -> fuzz/property tests
```

### 19.1 Conformance vectors

建议目录：

```text
tests/vectors/
  rfc6716/
  upstream/
  generated/
```

每条 vector 保存：

- 输入 packet stream。
- 采样率。
- channel count。
- decode_fec 参数。
- 期望 PCM hash。
- 可选逐样本 PCM。

### 19.2 Differential tests

允许测试工具调用 libopus CLI 生成对照：

- `tools/diff_decode.sh`：Uya decoder vs opusdec。
- `tools/diff_encode_decode.sh`：Uya encoder 输出 -> opusdec。
- `tools/gen_vectors_from_wav.sh`：从 WAV 生成合法 packet corpus。

这些工具只能出现在 `tools/` 或 `tests/`，不能被 `src/opus/**` import。

### 19.3 Fuzz/property

Packet parser fuzz：

- 任意 byte slice 输入不会崩溃。
- 成功 parse 后 frame slice 总长度不越界。
- 非法 padding/length 必须返回错误。

Entropy fuzz：

- 随机符号序列 encode 再 decode 一致。
- 随机截断 bitstream 不越界。

Decoder robustness：

- 任意 packet decode 不得越界写 PCM。
- 错误返回后 decoder state 必须仍可继续处理下一包，除非文档明确 state reset。

## 20. 性能设计

第一目标是正确性，第二目标是热路径结构不阻断优化。

性能原则：

- 标量实现先稳定。
- 所有热路径函数保持小而纯，便于后续 `@vector` 或 backend 优化。
- 避免在 inner loop 使用接口动态分派。
- 避免 decoder 中使用 arena 或 heap。
- 常量表按 cache locality 分组。
- 逐步用 benchmark 标记瓶颈，不预先大面积手写优化。
- 从 packet+entropy 阶段开始记录基线，避免等 full decoder 完成后才发现 API 或 state 布局阻断优化。

Benchmark：

```text
bench_entropy_decode
bench_packet_parse
bench_celt_mdct_20ms
bench_celt_decode_fb_20ms
bench_silk_decode_wb_20ms
bench_decode_music_48k_stereo
bench_decode_voice_16k_mono
```

基线记录：

- 每个 benchmark 记录编译器版本、backend、优化级别、CPU/平台、输入 corpus、运行次数。
- 至少记录 ns/packet、ns/sample、real-time factor、alloc count、peak scratch bytes；可用时额外记录 cycles/sample 和 top functions。
- `bench_packet_parse` 与 `bench_entropy_decode` 在 M1 阶段就接入 `make bench`，CELT/SILK milestone 完成时分别补齐对应整帧 benchmark。
- 性能回退超过当前 baseline 10% 时，需要在 PR/commit 中解释原因或更新 baseline 文档。

后期 SIMD 候选：

- CELT MDCT/IMDCT。
- CELT band normalization。
- pitch correlation。
- FIR/IIR filters。
- stereo interleave/deinterleave。
- saturating sample conversion。

## 21. 编码器路线

Encoder 的复杂度显著高于 decoder，因此必须分层交付。

### 21.1 Basic Encoder

目标：

- 输出合法 Opus packet。
- 支持 mono/stereo、20ms、固定 bitrate。
- 支持 CELT-only fullband 音乐路径。
- 支持 SILK-only wideband 语音路径的最小实现。

不要求：

- 最优音质。
- 全自动 mode switching。
- 复杂 VBR。

### 21.2 Practical Encoder

目标：

- VBR。
- 简单语音/音乐检测。
- 基于 bitrate 的 bandwidth/mode decision。
- in-band FEC。
- DTX。
- complexity 0..10。

### 21.3 Quality Encoder

目标：

- 更接近 libopus 的 rate-distortion decision。
- 更稳定 transient handling。
- 更优 stereo/intensity decision。
- 更好的 low bitrate speech quality。
- 针对 WebRTC/streaming/archival 给出 profile。

## 22. 命令行工具

建议提供三个 CLI：

```text
bin/uopusdec
bin/uopusenc
bin/uopusinfo
```

`uopusdec`：

- 输入 `.opus`/raw packet stream。
- 输出 WAV/raw PCM。
- 支持 `--rate`、`--channels`、`--fec`。

`uopusenc`：

- 输入 WAV/raw PCM。
- 输出 Ogg Opus。
- 支持 `--bitrate`、`--vbr`、`--application`、`--complexity`。

`uopusinfo`：

- 打印 Ogg Opus headers、duration、stream count、mapping、packet stats。

CLI 是测试和示范工具，不应成为核心 API 依赖。

## 23. 兼容性策略

### 23.1 Decoder

Decoder 目标是规范一致。只要输入 packet 合法，就应稳定输出 PCM。

验收：

- RFC/upstream vectors。
- 随机 packet corpus。
- Ogg Opus real-world corpus。
- RTP packet sequence corpus。

### 23.2 Encoder

Encoder 初期目标是互操作：

- libopus 能解。
- 浏览器/WebRTC 能解。
- FFmpeg/GStreamer 能解。
- 自己的 decoder 能解。

音质通过 staged benchmark 和主观样本逐步推进。

### 23.3 API

Uya API 优先类型安全。C ABI 兼容层后置。

最终可提供：

- `opus_decoder_create` 风格 wrapper。
- `opus_decode` 风格 wrapper。
- `opus_encoder_create` 风格 wrapper。
- `opus_encode` 风格 wrapper。
- 常见 `OPUS_SET_*`/`OPUS_GET_*` 兼容入口。

## 24. 风险和缓解

### 24.1 Bit-exact 风险

风险：定点 arithmetic、shift、溢出、rounding 与规范/C 实现不一致。

缓解：

- 每个 DSP primitive 写 golden test。
- 禁止隐式 signed overflow。
- 所有 Q-format 函数集中实现。
- 先 decoder，后 encoder。

### 24.2 表迁移风险

风险：CDF/codebook/window 表抄写错误，导致深层 decode 失败。

缓解：

- 每个表记录来源章节或 upstream 名称。
- 表文件测试 hash。
- 生成器和人工表双向校验。

### 24.3 Uya 编译器成熟度风险

风险：大型定点项目可能触发泛型、数组、接口、C99 后端问题。

缓解：

- 热路径少用复杂泛型和接口。
- 大表拆模块。
- 每个模块先有小测试。
- 发现编译器问题时添加最小 repro 到 `docs/uya-compiler-bugs.md`。

### 24.4 Encoder 质量风险

风险：合法 encoder 容易，优秀 encoder 难。

缓解：

- 明确 Basic/Practical/Quality 分层。
- decoder conformance 不受 encoder 进度影响。
- 先用 objective metrics 和互操作测试，再做主观调音。

## 25. 里程碑定义

M0：文档和骨架。

- `docs/design.md`、`docs/todo.md`。
- `src/opus/**` 空模块骨架。
- 最小 Makefile。

M1：Packet + entropy。

- TOC/frame parser 完整。
- range coder roundtrip。
- packet fuzz 不崩溃。

M2：CELT-only decoder。

- 支持 CELT-only NB/WB/SWB/FB。
- 支持 2.5/5/10/20ms。
- 通过 CELT decoder vectors。

M3：SILK-only decoder。

- 支持 NB/MB/WB。
- 支持 10/20/40/60ms。
- 支持 mono/stereo。
- 通过 SILK decoder vectors。

M4：Hybrid decoder。

- 支持 SWB/FB hybrid。
- 通过 full Opus decoder vectors。

M5：PLC/FEC/repacketizer/multistream。

- packet loss concealment。
- in-band FEC decode。
- repacketizer。
- mapping family 0/1。

M6：Basic encoder。

- 合法 CELT/SILK packet 输出。
- libopus 可解。
- 自解 roundtrip。

M7：Ogg/RTP/CLI。

- Ogg Opus decode/encode。
- RTP payload parse/write。
- `uopusdec`/`uopusenc`/`uopusinfo`。

M8：Performance + quality。

- benchmark 覆盖。
- SIMD 热点。
- Practical/Quality encoder。
