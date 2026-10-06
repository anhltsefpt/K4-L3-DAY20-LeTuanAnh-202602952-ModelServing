# 02 - Continuous batching under load (u50)

Host `Darwin-arm64` · `--parallel 4` · 28 samples over
60s at 2.0s intervals · raw CSV: `02-server-metrics-u50.csv`

| Gauge | Peak observed |
|:--|--:|
| `n_busy_slots_per_decode` (avg/decode) | 3.97 of 4 slots (99%) |
| `requests_processing` | 4 |
| `requests_deferred` | 46 |
| `kv_cache_usage_ratio` | n/a — not exported by llama.cpp `b10488` |
| `tokens_predicted_total` (final) | 19222 |

Highest sampled value was **3.97 of 4** slots. Note this gauge is llama.cpp's *average* busy slots per decode step, so the number below is the highest average we sampled, not an instantaneous maximum batch width. A peak near 1 means
requests were served one at a time -- either the load was too light to overlap, or
they arrived too far apart. A peak approaching `--parallel` means the scheduler was
genuinely packing concurrent requests into shared decode steps.
`requests_deferred` went above zero: more requests arrived than there were slots, so some waited. That wait is the queue time in your P95.

## Nhận xét

**Batch width đỉnh: 3.97/4 slot.** Continuous batching hoạt động thật: gần như mọi decode step
đều gộp đủ 4 request. Tính từ CSV metrics: tokens_predicted / n_decode ≈ **4.01 token mỗi decode
step**, khoảng 40 step/s, tổng **161.7 tok/s**. Khi chỉ có 1 request, server sinh 123 tok/s,
nên batching tăng throughput tổng khoảng 1.31×.

**So với effective concurrency trong `02-server-results.md` (40.0):** hai con số trông lệch nhau
10 lần, nhưng thực ra không mâu thuẫn, vì chúng đo hai thứ khác nhau:
- `n_busy_slots_per_decode` ≈ 4 là số request **đang được tính toán** trong mỗi step. Con số này
  bị chặn trên bởi `--parallel 4`.
- Effective concurrency = 40 (Little's Law, RPS × latency) là tổng số request **trong hệ thống**,
  gồm ~4 request đang chạy và ~36 request đang xếp hàng. `requests_deferred` có lúc lên tới 46,
  cùng bậc với con số này (46 là đỉnh lấy mẫu, còn 36 là trung bình).

Muốn biết **batch width**, tôi tin gauge của server vì đó là số đo trực tiếp từ scheduler.
Muốn biết **tải và thời gian chờ**, tôi tin Little's Law. Ghép hai con số lại cho ra kết luận:
server luôn chạy hết công suất 4 slot, và phần tải thừa chỉ biến thành hàng đợi.
