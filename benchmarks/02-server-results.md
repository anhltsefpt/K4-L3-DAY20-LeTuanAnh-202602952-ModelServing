# 02 - Serve: load test + saturation reading

Host `Darwin-arm64` · llama.cpp `b10488` ·
`--parallel 4` · `ctx=2048` · `threads=10` ·
`ngl=99`

| Users | Reqs | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 10 | 164 | 2.78 | 2600 | 4000 | 4300 | 7.4 | 0.0% |
| 50 | 165 | 2.79 | 16000 | 18000 | 19000 | 40.0 | 0.0% |

*Effective concurrency = RPS x average latency (Little's Law) -- how many requests were
really in flight, regardless of how many users locust simulated. It counts queued requests
too, so the occupancy/slot ratio can legitimately exceed 1.0; it is occupancy, not
utilisation. For true slot utilisation use the server's own gauges (`make metrics`).*

## What these two runs say

| Going from 10 to 50 users | |
|:--|--:|
| Offered load | 5x |
| Throughput actually delivered | **1.00x** (20% of linear) |
| P95 latency | **4.50x** |
| Effective concurrency at 50 users | 40.0 vs `--parallel 4` slots (occupancy/slot ratio 10.01) |

**Saturated.** Throughput delivered only 1.00x for 5x the offered load, and effective concurrency (40.0) is at or above all 4 decode slots. Saturation sets in somewhere at or below 50 users; the load you added beyond that point became queue time rather than throughput.

Throughput moved 1.00x while P95 moved 4.50x. That gap is the goodput argument: past saturation you buy throughput by spending latency, and if your SLO is a P95 target then the requests you added are no longer being served within it. (This lab does not fix an SLO number for you -- pick one in your write-up and state how much goodput you keep at it.)

## Nhận định: server bão hoà ở đâu

**Server đã bão hoà ngay từ 10 users, tức ngay khi số request đồng thời vượt 4 slot.**
Bằng chứng là 3 con số:

1. **RPS đi ngang:** 2.78 → 2.79 RPS (1.00×) dù tải tăng 5×. Throughput tối đa của server
   khoảng 2.8 RPS. Thêm user không thêm được throughput.
2. **Effective concurrency (Little's Law) vượt số slot từ 10 users:** L = λ × W =
   2.78 × 2.67 s ≈ 7.4 request đang "trong hệ thống", trong khi chỉ có 4 slot. Vậy khoảng 3.4
   request đã phải xếp hàng. Ở 50 users, L = 40 nghĩa là ~4 request đang chạy và ~36 request
   đang chờ.
3. **P95 phồng 4.5×** (4.0 s → 18 s), trong khi thời gian xử lý thật không đổi. Áp Little's Law
   cho riêng phần đang chạy: 4 slot / 2.79 RPS ≈ **1.4 s compute**. Phần còn lại là thời gian
   chờ: 36 / 2.79 ≈ **12.9 s queue**. Tổng ≈ 14.3 s, khớp với latency trung bình đo được (14.3 s).
   Gần 90% latency ở 50 users là **xếp hàng**, không phải tính toán.

Gauge của server xác nhận điều này (`02-server-batching-u50.md`): `n_busy_slots_per_decode`
đạt 3.97/4 và `requests_deferred` lên tới 46.

**Goodput @ SLO:** chọn SLO là P95 ≤ 5 s cho chat. Ở 10 users, P95 = 4.0 s và P99 = 4.3 s, nên
vẫn giữ được toàn bộ goodput (~2.78 RPS), dù đã sát ngưỡng. Ở 50 users, P50 đã là 16 s, chỉ vài
request đầu tiên (trước khi hàng đợi dâng lên, min 0.8 s) đạt SLO. **Goodput gần như về 0**,
dù RPS danh nghĩa không đổi.

**Knob tôi sẽ đổi đầu tiên: tăng `--parallel` (4 → 8), đồng thời tăng `--ctx-size` (2048 → 4096).**
- Vì sao `--parallel`: cả 4 slot đều đầy (3.97/4) và có 46 request bị defer. Nút thắt là số slot,
  không phải GPU. Đo dưới tải thấy server sinh 161.7 tok/s tổng, với khoảng 4 token mỗi decode
  step và ~40 step/s (~25 ms/step), so với 123 tok/s khi chỉ 1 request (~8 ms/step). Gộp 4 request
  vào một step chỉ làm mỗi step chậm khoảng 3×, nhưng throughput tổng vẫn tăng 1.31×, vì weights
  chỉ phải đọc một lần cho cả batch. GPU M1 Pro vẫn còn dư băng thông (decode 1 request chỉ dùng
  ~60 GB/s), nên batch rộng hơn có thể tiếp tục tăng tok/s tổng.
- Vì sao phải tăng `ctx-size` cùng lúc: context chia đều cho các slot (`n_ctx_slot = 512` hiện
  tại). Nếu lên 8 slot mà giữ 2048 thì mỗi slot chỉ còn 256 token, không đủ cho prompt long-rag.
- Vì sao không đổi thread hay quantization: `make tune` cho thấy thread count gần như không ảnh
  hưởng (1.00×), và 2-bit không nhanh hơn 4-bit trên máy này. Cả hai đều không chạm vào nút thắt
  thật, là hàng đợi trước 4 slot.
- Cái giá phải trả: mỗi request sẽ decode chậm hơn (TPOT tăng) khi batch rộng hơn. Ở mức tải vượt
  quá khả năng của server, cách duy nhất giữ SLO là **admission control**: giới hạn hàng đợi và
  trả 429 sớm, thay vì để request chờ 16 s.
