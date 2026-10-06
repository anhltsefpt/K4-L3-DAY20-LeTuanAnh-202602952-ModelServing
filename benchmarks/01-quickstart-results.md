# 01 - Measure: latency baseline

Model `Qwen3.5 0.8B` · host `Darwin-arm64` · llama.cpp `b10488`
Settings: `threads=10` `ngl=99` `ctx=2048`
`max_tokens=64` · warm-up discarded
Completed requests: `Q4_K_M` 10/10 · `UD-Q2_K_XL` 10/10

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
|:--|--:|--:|--:|--:|--:|--:|
| Q4_K_M | 0.50 | 2097 | 54 / 63 | 8.1 / 8.6 | 562 / 592 / 592 | 123.4 |
| UD-Q2_K_XL | 0.39 | 2045 | 52 / 55 | 8.2 / 8.3 | 568 / 579 / 579 | 122.0 |

- **TTFT** = prefill. Short prompts keep it small; long-context RAG is where it explodes.
- **TPOT** = per-output-token decode cost, bounded by memory bandwidth. `decode tok/s = 1000 / TPOT_p50`.
- `UD-Q2_K_XL` and `Q4_K_M` decode within 2% of each other here, for 0.11 GB difference on disk.

## Nhận xét: 2-bit vs 4-bit

**Tốc độ: 2-bit không nhanh hơn.** Decode 122.0 tok/s (Q2) so với 123.4 tok/s (Q4), TPOT
P50 8.2 so với 8.1 ms, TTFT 52 so với 54 ms. Mọi chênh lệch đều dưới 2%, nằm trong nhiễu đo.
File chỉ nhỏ hơn 22% (0.39 so với 0.50 GB).

**Vì sao khác với kỳ vọng "ít bit hơn → đọc ít byte hơn → decode nhanh hơn":**
- Model quá nhỏ nên chưa chạm trần memory bandwidth. Mỗi token phải đọc khoảng 0.5 GB
  weights, nhân 123 tok/s ≈ 60 GB/s, thấp hơn nhiều so với băng thông unified memory của
  Apple Silicon. Thời gian mỗi token (~8 ms) chủ yếu là overhead cố định: dispatch kernel
  Metal (`ngl=99`), đồng bộ CPU↔GPU, sampling. Phần này không giảm khi file nhỏ đi.
- Dequantize Q2_K tốn nhiều phép tính hơn Q4_K trên mỗi weight, nên ăn mất phần byte đã
  tiết kiệm.
- `UD` (Unsloth Dynamic) giữ embedding và các layer nhạy cảm ở số bit cao hơn, nên lượng
  byte giảm chỉ 22% chứ không phải ~50%.

**Chất lượng: 2-bit giảm rõ.** Tôi hỏi cả hai bản cùng 4 câu, `temperature=0`,
`max_tokens=200` (script: `scripts/compare_quality.py`):

| Câu hỏi | Q4_K_M | UD-Q2_K_XL |
|:--|:--|:--|
| Thủ đô Việt Nam | Sai ("Hàn Quốc") | Đúng "Hà Nội", sau đó lặp "chính trị…" tới hết token |
| Toán: 50.000 − 3×12.000 | Đúng hướng (36.000 → trừ), bị cắt bởi max_tokens | Sai và tự mâu thuẫn (1.200 rồi 7.400 đồng) |
| Hàm Python `is_prime` | Đúng, kiểm tra tới √n | Sai logic (`i*i == n`), lỗi `__main` |
| Giải thích memory-bound (EN) | Mạch lạc, chưa chính xác | Lặp nguyên một câu 5 lần |

Bản 2-bit bị repetition loop và sai suy luận/code nhiều lần. Bản 4-bit cũng sai câu
kiến thức, nhưng lỗi đó là do model 0.8B quá nhỏ chứ không phải do quantization.

**Kết luận: trên máy này, 2-bit không đáng dùng.** Không được thêm tốc độ, chỉ tiết kiệm
0.11 GB RAM, mà chất lượng giảm rõ. 2-bit chỉ đáng cân nhắc khi model lớn không vừa RAM,
hoặc khi decode thực sự bị giới hạn bởi memory bandwidth (model nhiều tỉ tham số).
