# 纯 Uya 重构 Opus TODO

本文是用纯 Uya 重构 Opus 的分阶段执行清单。除测试工具、系统 FFI 和 Uya C99 后端外，核心编解码实现不引入非 Uya 业务代码。

## 0. 文档与约束

- [x] 创建详细设计文档：`docs/design.md`。
- [x] 创建分阶段 TODO 文档：`docs/todo.md`。
- [x] 冻结项目名称、库名称和 CLI 名称。
- [x] 明确第一版目标：decoder conformance 优先，encoder 质量后置。
- [x] 确认 Uya 编译器路径和最低版本。
- [x] 建立 `docs/references.md`，记录 RFC 6716/RFC 8251/RFC 7845/RFC 7587 和 upstream 表来源。
- [x] 建立 `docs/uya-compiler-bugs.md`，保存本项目触发的 Uya 编译器最小复现。
- [x] 建立 `docs/conformance.md`，定义 bit-exact、误差容忍、测试 corpus 来源和验收命令。

## 1. 工程骨架

- [x] 创建 `src/opus/` 模块根。
- [x] 创建 `src/opus/core/`。
- [x] 创建 `src/opus/packet/`。
- [x] 创建 `src/opus/entropy/`。
- [x] 创建 `src/opus/dsp/`。
- [x] 创建 `src/opus/silk/`。
- [x] 创建 `src/opus/celt/`。
- [x] 创建 `src/opus/hybrid/`。
- [x] 创建 `src/opus/api/`。
- [x] 创建 `src/opus/container/`。
- [x] 创建 `src/opus/cli/`。
- [x] 创建 `tests/`。
- [x] 创建 `tests/vectors/`。
- [x] 创建 `bench/`。
- [x] 创建 `tools/`。
- [x] 创建 `bin/` 和 `build/` 输出目录，并加入忽略规则。
- [x] 创建 Makefile 或 uyabuild 配置。
- [x] 提供 `make check`。
- [x] 提供 `make test`。
- [x] 提供 `make bench` 占位。
- [x] 创建 `bench/baseline.md`，记录机器、编译器、backend、优化级别和基线格式。
- [x] 提供最小 smoke 文件，确认 Uya 编译器可构建项目。

验收标准：

- [x] `make check` 在空实现阶段可以运行并给出清晰结果。
- [x] 任何新增模块都有对应最小测试入口。
- [x] `make bench` 在空实现阶段输出稳定占位结果，不伪造性能数字。

## 2. Core 类型和常量

- [x] 实现 `core/types.uya`。
- [x] 定义 `OpusMode`。
- [x] 定义 `OpusBandwidth`。
- [x] 定义 `OpusApplication`。
- [x] 定义 `OpusSignalHint`。
- [x] 定义 `PacketInfo`。
- [x] 定义 `OpusDecoderConfig`。
- [x] 定义 `OpusEncoderConfig`。
- [x] 实现 `core/constants.uya`。
- [x] 定义 `MAX_CHANNELS`。
- [x] 定义 `MAX_FRAME_MS`。
- [x] 定义 `MAX_PACKET_MS`。
- [x] 定义 `MAX_FRAME_SAMPLES_48K`。
- [x] 定义 `MAX_PACKET_SAMPLES_48K`。
- [x] 定义 `MAX_FRAME_BYTES`。
- [x] 实现 `core/errors.uya`。
- [x] 实现参数校验 helper。
- [x] 测试非法采样率。
- [x] 测试非法声道数。
- [x] 测试 frame size 边界。

验收标准：

- [x] core 模块不依赖 packet/silk/celt/api。
- [x] 所有公共错误名稳定。

## 3. Packet Parser

- [x] 实现 `packet/toc.uya`。
- [x] 建立 32 项 TOC config 表。
- [x] 实现 TOC byte 解析。
- [x] 实现 `config -> mode/bandwidth/frame_duration` 映射。
- [x] 实现 mono/stereo bit 解析。
- [x] 实现 code 0 frame split。
- [x] 实现 code 1 CBR two-frame split。
- [x] 实现 code 2 VBR two-frame split。
- [x] 实现 code 3 arbitrary-frame split。
- [x] 实现 padding 解析和校验。
- [x] 实现 VBR frame length 编码解析。
- [x] 实现 packet duration <= 120ms 校验。
- [x] 实现 `decoder_get_packet_info` 的 packet-only 版本。
- [x] 测试 32 个 TOC config。
- [x] 测试 code 0/1/2/3 合法包。
- [x] 测试非法空包。
- [x] 测试非法 padding。
- [x] 测试截断 VBR length。
- [x] 测试 packet duration 超限。
- [x] Fuzz packet parser，确认不越界。

验收标准：

- [x] Parser 不复制 frame payload。
- [x] 任意 byte slice 输入都只返回成功或 Uya 错误，不崩溃。

## 4. Entropy Range Coder

- [x] 实现 `entropy/range_dec.uya` 状态。
- [x] 实现 `ec_dec_init`。
- [x] 实现 range normalization。
- [x] 实现 `ec_decode`。
- [x] 实现 `ec_decode_bin`。
- [x] 实现 `ec_dec_update`。
- [x] 实现 `ec_dec_icdf`。
- [x] 实现 `ec_dec_bit_logp`。
- [x] 实现 `ec_dec_uint`。
- [x] 实现 `ec_dec_bits`。
- [x] 实现 `ec_tell`。
- [x] 实现 `ec_tell_frac`。
- [x] 实现 `ec_dec_check`，把热路径 `error` 标志转换成 public error。
- [x] 确认 entropy symbol hot API 不返回 `!T`，错误先写入 state。
- [x] 实现 `entropy/range_enc.uya` 状态。
- [x] 实现 `ec_enc_init`。
- [x] 实现 `ec_encode`。
- [x] 实现 `ec_enc_icdf`。
- [x] 实现 `ec_enc_bit_logp`。
- [x] 实现 `ec_enc_uint`。
- [x] 实现 `ec_enc_bits`。
- [x] 实现 `ec_enc_done`。
- [x] 实现 CDF helper。
- [x] 实现 Laplace helper。
- [x] 测试 uint roundtrip。
- [x] 测试 icdf roundtrip。
- [x] 测试 bit_logp roundtrip。
- [x] 测试 raw end bits。
- [x] 测试 1 byte buffer 边界。
- [x] 测试随机符号序列 roundtrip。
- [x] 测试截断 bitstream 错误。
- [x] benchmark entropy decode，记录 ns/symbol 和 alloc count。

验收标准：

- [x] Entropy coder 独立测试全部通过后，才进入 SILK/CELT 主体。
- [x] `ec_tell_frac` 与参考 vectors 一致。
- [x] Range coder hot loop 无 heap 分配、无 interface 动态分派、无逐 symbol `!T` 错误传播。

## 5. 定点算术和 DSP 基础

- [x] 实现 `core/qformat.uya`。
- [x] 实现 `core/saturate.uya`。
- [x] 实现 `sat16`。
- [x] 实现 `sat32`。
- [x] 实现 saturating add/sub。
- [x] 实现 common multiply helpers。
- [x] 实现 rounded shift helpers。
- [x] 实现 `core/bitops.uya`。
- [x] 实现 `celt_ilog`。
- [x] 实现 `clz` fallback。
- [x] 实现 `dsp/filters.uya` 基础 FIR/IIR helper。
- [x] 实现 `dsp/resampler.uya` 占位接口。
- [x] 实现 `dsp/pitch.uya` 基础 correlation helper。
- [x] 实现 `dsp/window.uya` 表结构。
- [x] 为每个 saturating primitive 写边界测试。
- [x] 为每个 Q-format primitive 写 golden test。
- [x] 检查所有 hot path 禁止 signed overflow 依赖。

验收标准：

- [x] 定点 helper 是算术入口，SILK/CELT 不散落重复 magic shift。
- [x] 所有 Q-format 表和变量命名带清晰后缀或注释。

## 6. 表迁移和校验

- [x] 盘点 RFC/upstream 必需表。
- [x] 创建 `silk/tables.uya`。
- [x] 创建 `celt/tables.uya`。
- [x] 创建 `entropy/cdf.uya`。
- [x] 创建 `dsp/window.uya` 表。
- [x] 创建 `docs/table_inventory.md`。
- [x] 为每个表记录来源、元素类型、Q-format、长度。
- [x] 编写 `tools/check_tables.uya` 或等价测试。
- [x] 测试表长度。
- [x] 测试表 hash。
- [x] 测试关键表单调性/边界。

备注：本轮已迁移并校验 decoder 早期路径需要的 CELT/SILK/entropy/window 表；FFT/MDCT twiddle、pulse cache、完整 NLSF codebook 等大生成表随后续 CELT/SILK 模块的 golden test 导入，避免脱离使用点提前落入不可验证的静态数据。

验收标准：

- [x] 表错误能在单元测试中快速定位，而不是等 full decode 才暴露。

## 7. CELT 基础

- [x] 实现 `celt/mode.uya`。
- [x] 实现 CELT mode 常量。
- [x] 实现 eBands 查询。
- [x] 实现 frame size/LM 映射。
- [x] 实现 `celt/rate.uya` bit allocation 初版。
- [x] 实现 `celt/cwrs.uya`。
- [x] 实现 `icwrs`。
- [x] 实现 pulse encode/decode roundtrip。
- [x] 实现 `dsp/mdct.uya` 标量 IMDCT。
- [x] 实现 overlap-add。
- [x] 实现 deemphasis。
- [x] 测试 mode table。
- [x] 测试 cwrs 小维度 exhaustive。
- [x] 测试 MDCT/IMDCT golden。
- [x] benchmark MDCT 标量版本。

验收标准：

- [x] CELT 基础模块不依赖 SILK。
- [x] cwrs 和 MDCT 可独立调试。

## 8. CELT-only Decoder

- [x] 实现 `celt/state.uya`。
- [x] 实现 `celt/quant_bands.uya` coarse energy decode。
- [x] 实现 fine energy decode。
- [x] 实现 TF changes decode。
- [x] 实现 spreading decision decode。
- [x] 实现 bit allocation integration。
- [x] 实现 PVQ band shape decode。
- [x] 实现 stereo intensity decode。
- [x] 实现 anti-collapse decode。
- [x] 实现 denormalize bands。
- [x] 实现 IMDCT integration。
- [x] 实现 CELT-only mono decode。
- [x] 实现 CELT-only stereo decode。
- [x] 支持 NB/WB/SWB/FB。
- [x] 支持 2.5ms。
- [x] 支持 5ms。
- [x] 支持 10ms。
- [x] 支持 20ms。
- [x] 测试 CELT-only conformance vectors。
- [x] 测试随机合法 CELT packets 不崩溃。
- [x] benchmark CELT-only FB/20ms stereo decode。

验收标准：

- [x] CELT-only decoder 通过目标 vectors。
- [x] 丢包前后的 state 更新稳定。

## 9. SILK 基础

- [x] 实现 `silk/state.uya`。
- [x] 实现 `silk/decoder_control.uya`。
- [x] 实现 SILK frame 参数初始化。
- [x] 实现 `silk/shell_coder.uya`。
- [x] 实现 shell decode。
- [x] 实现 pulse sign decode。
- [x] 实现 `silk/nlsf.uya`。
- [x] 实现 NLSF decode。
- [x] 实现 NLSF stabilization。
- [x] 实现 NLSF -> LPC。
- [x] 实现 `silk/lpc.uya`。
- [x] 实现 LPC synthesis。
- [x] 实现 `silk/ltp.uya`。
- [x] 实现 LTP coefficient decode。
- [x] 实现 LTP synthesis。
- [x] 实现 `silk/stereo.uya`。
- [x] 测试 shell coder vectors。
- [x] 测试 NLSF stabilization。
- [x] 测试 LPC synthesis golden。
- [x] 测试 LTP synthesis golden。

验收标准：

- [x] SILK 基础模块可独立跑 unit tests。
- [x] 所有 Q-format 在结构体字段中明确。

## 10. SILK-only Decoder

- [x] 实现 `silk/entropy_decode.uya`。
- [x] 解码 VAD flags。
- [x] 解码 LBRR flags。
- [x] 解码 signal type。
- [x] 解码 quantization offset。
- [x] 解码 gains。
- [x] 解码 NLSF indices。
- [x] 解码 pitch lag。
- [x] 解码 pitch contour。
- [x] 解码 LTP coefficients。
- [x] 解码 LTP scaling。
- [x] 解码 random seed。
- [x] 解码 pulse blocks。
- [x] 实现 excitation reconstruction。
- [x] 集成 LTP/LPC synthesis。
- [x] 实现 mono decode。
- [x] 实现 stereo mid/side reconstruction。
- [x] 支持 NB。
- [x] 支持 MB。
- [x] 支持 WB。
- [x] 支持 10ms。
- [x] 支持 20ms。
- [x] 支持 40ms。
- [x] 支持 60ms。
- [x] 测试 SILK-only conformance vectors。
- [x] benchmark SILK WB/20ms mono decode。

验收标准：

- [x] SILK-only decoder 通过目标 vectors。
- [x] 连续 frame 解码 state 与单帧测试一致。

## 11. PLC 和 FEC

- [x] 实现 `silk/plc.uya`。
- [x] 实现 SILK lost-frame concealment。
- [x] 实现 SILK energy decay。
- [x] 实现 SILK pitch extrapolation。
- [x] 实现 `silk/fec.uya`。
- [x] 实现 LBRR packet 检测。
- [x] 实现 delayed FEC decode。
- [x] 实现 `celt/plc.uya`。
- [x] 实现 CELT frequency-domain PLC 初版。
- [x] 实现 decoder API 中的 empty packet PLC。
- [x] 实现 `decode_fec` 参数语义。
- [x] 测试单包丢失。
- [x] 测试连续丢包。
- [x] 测试有 FEC 的上一帧恢复。
- [x] 测试无 FEC fallback 到 PLC。

验收标准：

- [x] 丢包不会破坏后续正常 packet decode。
- [x] PLC/FEC 路径不越界写 PCM。

## 12. Hybrid Decoder

- [x] 实现 `hybrid/state.uya`。
- [x] 实现 `hybrid/delay.uya`。
- [x] 实现 SILK/CELT budget split。
- [x] 实现 SILK lowband decode glue。
- [x] 实现 CELT highband decode glue。
- [x] 实现 delay compensation。
- [x] 实现 high/low band merge。
- [x] 支持 Hybrid SWB 10ms。
- [x] 支持 Hybrid SWB 20ms。
- [x] 支持 Hybrid FB 10ms。
- [x] 支持 Hybrid FB 20ms。
- [x] 测试 hybrid conformance vectors。
- [x] 测试 mode switching 到/出 hybrid。

验收标准：

- [ ] Full Opus decoder vectors 通过。
- [x] Hybrid 状态不泄漏到 SILK/CELT 模块内部。

## 13. Public Decoder API

- [x] 实现 `api/decoder.uya`。
- [x] 实现 `decoder_init`。
- [x] 实现 `decoder_get_packet_info`。
- [x] 实现 `decoder_decode_i16`。
- [x] 实现 output sample rate 转换。
- [x] 实现 48 kHz output fast path。
- [x] 实现 SILK-only 原生采样率到目标采样率的一次转换路径。
- [x] 实现 mono/stereo output 校验。
- [x] 实现 buffer size 检查。
- [x] 实现 decoder reset。
- [ ] 实现 gain Q8 设置。
- [ ] 实现 packet loss API。
- [ ] 拆分 decoder 常驻 history 和 scratch。
- [ ] 确认 Hybrid glue 不复制 SILK/CELT 大型 history buffer。
- [ ] 写 API smoke tests。
- [ ] 写非法参数 tests。
- [ ] 写小型 raw packet stream decode test。

验收标准：

- [ ] 对外 API 不暴露 SILK/CELT 内部结构。
- [ ] 错误返回后 decoder 可继续使用。
- [ ] 单流 decoder 初始化不清零与当前 config 无关的大块 scratch。
- [ ] 非 48 kHz 输出最多经历一次 final resample。

## 14. Repacketizer

- [ ] 实现 `packet/repacketizer.uya`。
- [ ] 实现 add packet。
- [ ] 实现 frame duration 校验。
- [ ] 实现 get packet duration。
- [ ] 实现 output CBR/VBR packet。
- [ ] 实现 padding 添加/移除。
- [ ] 测试拼接同 config packets。
- [ ] 测试非法混合 config。
- [ ] 测试 120ms 超限。
- [ ] 测试输出 packet 可被 decoder 解析。

验收标准：

- [ ] Repacketizer 不解码音频。
- [ ] 输出 packet parser roundtrip 成功。

## 15. Multistream

- [ ] 实现 `api/multistream.uya`。
- [ ] 实现 mapping family 0。
- [ ] 实现 mapping family 1。
- [ ] 实现 mapping family 255。
- [ ] 实现 coupled stream decode。
- [ ] 实现 uncoupled stream decode。
- [ ] 实现 channel mapping reorder。
- [ ] 实现按实际 `stream_count` 持有 decoder slots 的 pool。
- [ ] 支持 caller-provided multistream decoder storage。
- [ ] 测试 mono。
- [ ] 测试 stereo。
- [ ] 测试 5.1 mapping。
- [ ] 测试非法 mapping。

验收标准：

- [ ] 单流 decoder 不依赖 multistream。
- [ ] Multistream 错误不会污染单流 decoder state。
- [ ] Multistream init 不构造或清零 `OPUS_MAX_STREAMS` 个完整 decoder。

## 16. Basic Encoder

- [ ] 实现 `api/encoder.uya`。
- [ ] 实现 `encoder_init`。
- [ ] 实现 encoder config 校验。
- [ ] 实现 `encoder_encode_i16` 框架。
- [ ] 实现 CELT-only Basic encoder。
- [ ] 支持 FB/20ms/stereo。
- [ ] 实现基本 energy quantization。
- [ ] 实现合法 PVQ 输出。
- [ ] 实现 range encode 集成。
- [ ] 实现 SILK-only Basic encoder 占位或最小合法路径。
- [ ] 支持 WB/20ms/mono。
- [ ] 输出 packet 可被 Uya decoder 解码。
- [ ] 输出 packet 可被 libopus 解码。
- [ ] 写 sine/music/voice smoke tests。

验收标准：

- [ ] Basic encoder 目标是合法互操作，不以音质作为首要验收。
- [ ] Encoder 输出永远不超过调用者 packet buffer。

## 17. Practical Encoder

- [ ] 实现 VBR bit allocation。
- [ ] 实现 bitrate 控制。
- [ ] 实现 bandwidth decision。
- [ ] 实现 mode decision。
- [ ] 实现 frame duration decision。
- [ ] 实现语音/音乐粗分类。
- [ ] 实现 SILK VAD。
- [ ] 实现 SILK pitch analysis。
- [ ] 实现 SILK gain control。
- [ ] 实现 SILK NLSF quantization。
- [ ] 实现 SILK NSQ。
- [ ] 实现 CELT transient detection。
- [ ] 实现 CELT stereo intensity decision。
- [ ] 实现 in-band FEC encoder。
- [ ] 实现 DTX。
- [ ] 实现 complexity 0..10 的主要开关。
- [ ] 建立 objective quality bench。
- [ ] 建立主观样本集。

验收标准：

- [ ] 在常见 bitrate 下质量明显优于 Basic encoder。
- [ ] Practical encoder 仍保持全部 decoder 互操作。

## 18. Ogg Opus

- [ ] 实现 `container/ogg_opus.uya`。
- [ ] 解析 `OpusHead`。
- [ ] 编码 `OpusHead`。
- [ ] 解析 `OpusTags`。
- [ ] 编码 `OpusTags`。
- [ ] 实现 Ogg page parser。
- [ ] 实现 lacing。
- [ ] 实现 CRC。
- [ ] 实现 granule position。
- [ ] 实现 pre-skip。
- [ ] 实现 end trimming。
- [ ] 实现 chained stream 基础处理。
- [ ] 测试读取真实 `.opus` 文件。
- [ ] 测试写出文件可被 opusinfo/ffmpeg 识别。
- [ ] 测试损坏 CRC。
- [ ] 测试截断 page。

验收标准：

- [ ] Container 错误和 codec bitstream 错误区分清楚。
- [ ] Ogg 层不访问 SILK/CELT 内部 state。

## 19. RTP Opus

- [ ] 实现 `container/rtp_opus.uya`。
- [ ] 实现 payload parser。
- [ ] 实现 payload writer。
- [ ] 实现 ptime/maxptime 校验。
- [ ] 实现 SDP fmtp 参数 helper。
- [ ] 实现 stereo/sprop-stereo 映射。
- [ ] 实现 FEC hint。
- [ ] 测试单 packet payload。
- [ ] 测试多 frame payload。
- [ ] 测试 DTX/空 payload 语义。
- [ ] 测试 maxptime 超限。

验收标准：

- [ ] RTP 模块只处理 Opus payload，不绑定具体网络栈。

## 20. CLI 工具

- [ ] 实现 `src/opus/cli/opusdec.uya`。
- [ ] 实现 raw packet decode。
- [ ] 实现 Ogg Opus decode。
- [ ] 实现 WAV/raw PCM 输出。
- [ ] 实现 `src/opus/cli/opusenc.uya`。
- [ ] 实现 WAV/raw PCM 输入。
- [ ] 实现 Ogg Opus 输出。
- [ ] 实现 bitrate/application/complexity 参数。
- [ ] 实现 `src/opus/cli/opusinfo.uya`。
- [ ] 打印 OpusHead。
- [ ] 打印 OpusTags。
- [ ] 打印 packet stats。
- [ ] 写 CLI golden tests。

验收标准：

- [ ] CLI 只依赖 public API 和 container，不绕过 core API。

## 21. Conformance 和 Differential

- [ ] 获取/整理 RFC/upstream decoder vectors。
- [ ] 定义 vector manifest 格式。
- [ ] 实现 vector runner。
- [ ] 记录 PCM hash。
- [ ] 支持逐样本 diff 输出。
- [ ] 支持误差统计。
- [ ] 实现 `tools/diff_decode.sh`。
- [ ] 实现 `tools/diff_encode_decode.sh`。
- [ ] 实现 corpus 批量 decode。
- [ ] 接入 `make conformance`。
- [ ] 接入 `make differential`。

验收标准：

- [ ] 每次 codec 行为变化都能定位到具体 vector。
- [ ] Differential 工具不进入 core 依赖。

## 22. Fuzz 和健壮性

- [ ] 实现 packet parser fuzz。
- [ ] 实现 entropy decode fuzz。
- [ ] 实现 full decoder malformed packet fuzz。
- [ ] 实现 Ogg page fuzz。
- [ ] 实现 RTP payload fuzz。
- [ ] 测试随机输入不崩溃。
- [ ] 测试错误后 decoder state 可恢复。
- [ ] 测试输出 buffer guard。
- [ ] 测试极小 packet buffer。
- [ ] 测试极小 PCM buffer。

验收标准：

- [ ] Fuzz 失败必须生成可复现 seed/case。
- [ ] 任意 malformed input 不允许越界读写。

## 23. 性能和优化

- [ ] 实现 `bench/bench_packet_parse.uya`。
- [ ] 实现 `bench/bench_entropy_decode.uya`。
- [ ] 实现 `bench/bench_celt_mdct_20ms.uya`。
- [ ] 实现 `bench/bench_celt_decode_fb_20ms.uya`。
- [ ] 实现 `bench/bench_silk_decode_wb_20ms.uya`。
- [ ] 实现 `bench/bench_decode_music_48k_stereo.uya`。
- [ ] 实现 `bench/bench_decode_voice_16k_mono.uya`。
- [ ] 建立 benchmark baseline 文档。
- [ ] M1 阶段接入 packet parse 和 entropy decode benchmark。
- [ ] M2/M3 阶段分别接入 CELT/SILK 整帧 decode benchmark。
- [ ] 记录 ns/packet、ns/sample、real-time factor、alloc count、peak scratch bytes。
- [ ] 建立性能回退阈值，超过 baseline 10% 需解释或更新 baseline。
- [ ] 标记 top 10 hot functions。
- [ ] 优化 range coder。
- [ ] 优化 MDCT。
- [ ] 优化 pitch correlation。
- [ ] 优化 FIR/IIR filters。
- [ ] 优化 sample conversion。
- [ ] 评估 `@vector` SIMD。
- [ ] 为 SIMD 和标量结果写一致性测试。

验收标准：

- [ ] 每项优化都有 benchmark 前后对比。
- [ ] SIMD 路径必须有标量 fallback。

## 24. C ABI 兼容层

- [ ] 设计 C ABI wrapper 边界。
- [ ] 实现 `opus_decoder_create` 风格 wrapper。
- [ ] 实现 `opus_decoder_destroy` 风格 wrapper。
- [ ] 实现 `opus_decode` 风格 wrapper。
- [ ] 实现 `opus_encoder_create` 风格 wrapper。
- [ ] 实现 `opus_encoder_destroy` 风格 wrapper。
- [ ] 实现 `opus_encode` 风格 wrapper。
- [ ] 实现常见 CTL 映射。
- [ ] 写 C smoke tests。
- [ ] 确认 wrapper 不影响 Uya 原生 API。

验收标准：

- [ ] C ABI 是薄层，不能把核心逻辑搬到 C。

## 25. 发布准备

- [ ] 整理 README。
- [ ] 整理 API 文档。
- [ ] 整理 conformance 报告。
- [ ] 整理 benchmark 报告。
- [ ] 整理 codec 限制列表。
- [ ] 建立版本号策略。
- [ ] 建立 changelog。
- [ ] 建立 release checklist。
- [ ] 准备示例音频和示例命令。
- [ ] 确认 license 和 RFC/upstream 表版权说明。

验收标准：

- [ ] 用户可以按 README 构建、运行测试、解码示例。
- [ ] 项目清楚说明当前支持范围和未支持范围。
