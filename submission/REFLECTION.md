# Reflection — Day 20 Lab (Personal Report)

> **Đây là báo cáo cá nhân.** Số liệu của bạn **không** so sánh được với bạn cùng lớp
> — chỉ so **before vs after trên chính máy bạn**. Rubric chấm độ rõ ràng của setup,
> đo lường và **lập luận**, không chấm tốc độ tuyệt đối.
>
> `make verify` sẽ fail nếu còn placeholder chưa điền. Đó là cố ý.

**Họ Tên:** Lê Tuấn Anh
**MSSV:** 2A202602952
**Cohort:** A20-K4
**Ngày submit:** 2026-10-06

---

## 1. Hardware & runtime  *(rubric 1, 2 — 10 điểm)*

> Từ `make probe`. Paste output hoặc điền tay.

- **OS:** macOS (Darwin 25.4.0, arm64)
- **CPU:** Apple M1 Pro
- **Cores:** 10 physical / 10 logical (8 P-core + 2 E-core, không có SMT)
- **CPU extensions:** NEON
- **RAM:** 16 GB (unified memory)
- **Accelerator:** Apple Metal (GPU tích hợp của M1 Pro, `ngl=99`)
- **llama.cpp asset đã tải:** `llama-b10488-bin-macos-arm64.tar.gz` (prebuilt, không compile)
- **Model đã dùng:** Qwen3.5 0.8B (`LAB_MODEL=qwen35-0.8b`)
- **Quantization:** Q4_K_M + UD-Q2_K_XL (từ `models/active.json`)

**Chạy ở đâu:** laptop của tôi (MacBook Pro M1 Pro). Không dùng Colab/Kaggle.

**Setup story** (≤ 80 chữ): `make probe` đề xuất Gemma 4 E2B vì máy đủ RAM, nhưng tôi chọn
Qwen3.5 0.8B (~0.9 GB) để tải nhanh và có nhiều thời gian đo hơn. Prebuilt binary Metal chạy
ngay, không cần compile. Không có bước nào fail. Lưu ý duy nhất: `make load-report` phải chạy
**sau** khi locust kết thúc hẳn, nếu không report sẽ đọc CSV dở dang.

---

## 2. Đo lường  *(rubric 3, 4, 5 — 20 điểm)*

> Paste bảng từ `benchmarks/01-quickstart-results.md` (`make bench` tự sinh).

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
|---|--:|--:|--:|--:|--:|--:|
| Q4_K_M | 0.50 | 2097 | 54 / 63 | 8.1 / 8.6 | 562 / 592 / 592 | 123.4 |
| UD-Q2_K_XL | 0.39 | 2045 | 52 / 55 | 8.2 / 8.3 | 568 / 579 / 579 | 122.0 |

**Quan sát** (≤ 60 chữ): 2-bit **không nhanh hơn** (122.0 so với 123.4 tok/s, chênh dưới 2%).
Model 0.5 GB chưa chạm trần memory bandwidth, và dequantize Q2_K tốn tính toán hơn. Đã hỏi cùng
4 câu trên cả hai bản (`temperature=0`): 4-bit đúng 2/4, 2-bit đúng 0/4 (sai toán, code sai,
lặp vô hạn). **Không đáng dùng.**

---

## 3. Serving under load  *(rubric 8, 9, 10 — 20 điểm)*

> Từ `benchmarks/02-server-results.md` (`make load-report`).

| Users | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|--:|--:|--:|--:|--:|--:|--:|
| 10 | 2.78 | 2600 | 4000 | 4300 | 7.4 | 0.0% |
| 50 | 2.79 | 16000 | 18000 | 19000 | 40.0 | 0.0% |

- **Offered load tăng 5×, throughput thực tăng:** 1.00×
- **P95 tăng:** 4.50×
- **Effective concurrency ở 50 users:** 40.0 so với `--parallel` = 4 slots

**Peak `llamacpp:n_busy_slots_per_decode`** (từ `make metrics` khi `make load-50` đang
chạy): 3.97 / 4 slots

**Saturation reading** (≤ 80 chữ): Server bão hoà ngay từ 10 users. RPS đi ngang ở ~2.8, và
effective concurrency 7.4 đã vượt 4 slot. Phần P95 tăng thêm là **queue time**: theo Little's
Law, ở 50 users có ~4 request đang chạy (4 / 2.79 ≈ 1.4 s compute) và ~36 request đang chờ
(≈ 12.9 s), cộng lại khớp với latency trung bình 14.3 s. `requests_deferred` lên tới 46 cũng
xác nhận điều này. Knob đổi trước: `--parallel` 4 → 8 (kèm `ctx-size` 4096), vì slot đầy còn GPU
vẫn dư băng thông.

---

## 4. Integration  *(rubric 12, 13 — 15 điểm)*

> Từ `make pipeline`. Nói thật cái nào real, cái nào stub — stub **không** mất điểm.

| Day | Piece | Real hay stub? |
|---|---|---|
| N16 Cloud/IaC | Chạy local trên laptop, không có hạ tầng cloud | stub |
| N17 Data pipeline | Tài liệu là `TOY_DOCS` hard-code trong `pipeline.py` | stub |
| N18 Lakehouse | List Python trong bộ nhớ, không có lakehouse | stub |
| N19 Vector + features | Keyword overlap, không có embedding hay vector index | stub |
| N20 Serving | `llama-server` | real |

**Latency split** (mean của 3 query, từ output của `pipeline.py`):

- embed: 0.0 ms
- retrieve: 0.0 ms
- llm: 1240.4 ms
- **stage chiếm nhiều nhất:** llm (100% của total)

**Reflection** (≤ 60 chữ): Bottleneck là LLM, đúng kỳ vọng vì embed/retrieve đang là stub (bằng
0 ms không có nghĩa là miễn phí trong hệ thống thật). Trong LLM, decode chiếm ~91% (~7.7
ms/token), prefill chỉ ~9%. Muốn giảm 2×: giảm số token output (system prompt yêu cầu trả lời
ngắn, `max_tokens` 200 → 100), vì latency ≈ prefill + N_out × TPOT.

---

## 5. The single change that mattered most  *(rubric 11 — 10 điểm)*

> **Phần quan trọng nhất của report.** Không cần bonus track: `make tune` đã cho bạn
> một before/after thật (`benchmarks/01-tuning-tg128.md`). Đổi quantization,
> `LAB_N_CTX`, hay `--parallel` rồi đo lại cũng được.

**Change:** offload toàn bộ model lên GPU Metal, `-ngl 0` → `-ngl 99`
(`llama-bench`, `-t 10`, chi tiết: `benchmarks/01-ngl-cpu-vs-gpu.md`)

```
before:  ngl=0  (CPU only)   prefill 372 tok/s  · decode  65.1 tok/s
after:   ngl=99 (Metal GPU)  prefill 2325 tok/s · decode 129.7 tok/s
speedup: prefill 6.25× · decode 1.99×
```

**Tại sao nó work:**

Cùng một thay đổi nhưng hai pha được lợi rất khác nhau: prefill nhanh hơn 6.25×, decode chỉ
nhanh hơn 2×. Sự chênh lệch này chính là cơ chế. **Prefill là compute-bound:** 512 token của prompt
được xử lý cùng lúc thành phép nhân ma trận × ma trận. Mỗi weight đọc từ bộ nhớ được dùng lại
512 lần, nên nút thắt là số phép tính mỗi giây. GPU 16-core của M1 Pro có số đơn vị tính (ALU)
nhiều hơn hẳn 10 core CPU dùng NEON, nên prefill tăng gần bằng tỉ lệ sức tính giữa hai bên.

**Decode là memory-bandwidth-bound:** mỗi token mới phải đọc lại toàn bộ ~0.5 GB weights chỉ để
làm phép nhân ma trận × vector, mỗi weight chỉ dùng một lần. Lúc này sức tính không còn quan
trọng, chỉ có tốc độ đọc bộ nhớ. CPU đạt 65 tok/s × 0.5 GB ≈ 32 GB/s, GPU đạt 130 × 0.5 ≈ 65 GB/s.
Điều bất ngờ là CPU và GPU trên Apple Silicon **dùng chung một unified memory**, nên lý ra băng
thông như nhau. Decode vẫn nhanh gấp 2× vì cụm CPU không kéo được hết băng thông của bộ nhớ chung
(ít luồng truy cập đồng thời, cộng thêm chi phí đồng bộ thread ở barrier sau mỗi op), còn GPU có
hàng nghìn luồng đọc song song. Đây cũng là lý do `make tune` cho đường cong phẳng (1.00×): khi
`ngl=99` thì CPU thread gần như không làm gì. Và 2-bit không giúp được gì ở §2, vì với GPU decode
model này vẫn mới dùng ~65 GB/s, chưa tới trần băng thông. Mỗi token còn bị chi phối bởi overhead
dispatch kernel, không chỉ bởi số byte phải đọc.

---

## 6. Bonus  *(optional — tối đa 10 điểm)*

> Bỏ trống nếu không làm. Xem `docs/bonus/README.md`. Đừng làm hết — **một** finding sâu
> ăn điểm hơn năm bảng nông.

**Đã làm:** Không làm bonus track.

---

## 7. Điều làm bạn ngạc nhiên nhất  *(optional)*

Lượng tử hoá 2-bit, thứ deck nói sẽ giúp decode nhanh hơn, lại không nhanh hơn chút nào trên máy
này, mà chất lượng giảm rõ. Ngược lại, chỉ một flag `-ngl` đã tạo ra speedup 6× cho prefill. Knob
"đúng" phụ thuộc vào việc pha nào đang bị chặn bởi cái gì.

---

## 8. Self-check trước khi push

- [x] `hardware.json` committed
- [x] `models/active.json` committed
- [x] `benchmarks/01-quickstart-results.md` committed (`make bench`)
- [x] `benchmarks/01-tuning-tg128.md` committed (`make tune`)
- [x] `benchmarks/02-server-results.md` committed (`make load-report`)
- [x] `benchmarks/02-server-batching-u50.md` hoặc `-metrics-u50.csv` committed (`make metrics`)
- [x] `benchmarks/locust-10_stats.csv` + `locust-50_stats.csv` committed (`make load-10` / `load-50`)
- [x] `benchmarks/03-integration-results.md` committed (`make pipeline`)
- [x] Mọi section **"required — replace this line"** trong các file `benchmarks/*.md`
      đã được thay bằng nhận xét của bạn
- [x] 5 screenshots trong `submission/screenshots/`
- [ ] `make verify` → **exit 0**
- [ ] Repo tên đúng mẫu `K4-L3-DAY20-HoVaTen-MSSV-ModelServing` (xem `docs/SUBMISSION.md`)
- [ ] Repo GitHub ở chế độ **public**
- [ ] Đã push và paste public URL vào VinUni LMS **trước 23:59 (UTC+7) ngày làm lab**
- [x] **Không** commit `models/*.gguf`, `runtime/` hay `.env` (đã có trong `.gitignore`)

**Quan trọng:** repo phải **public** đến khi điểm được công bố. Private → grader không
xem được → 0 điểm.

---

## 9. Khai báo sử dụng AI  *(xem `docs/RULES.md` §3)*

Dùng **Claude Code** để: giải thích yêu cầu lab và các khái niệm (TTFT/TPOT, Little's Law,
continuous batching); viết script `scripts/compare_quality.py` để so chất lượng 2-bit vs 4-bit;
chạy `llama-bench` cho thí nghiệm `ngl=0` vs `ngl=99`; soạn nháp các phần nhận xét trong
`benchmarks/*.md` và REFLECTION từ số liệu tôi đã đo. Mọi số liệu đều sinh từ máy của tôi. Tôi đã
đọc lại và kiểm tra các lập luận trước khi nộp.
