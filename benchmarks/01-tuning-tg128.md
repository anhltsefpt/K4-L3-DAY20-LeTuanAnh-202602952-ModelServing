# 01 - Tune: thread-count sweep

Model `Qwen3.5-0.8B-Q4_K_M.gguf` · host `Darwin-arm64` · llama.cpp `b10488`
CPU: **10 physical · 10 logical** cores · `ngl=99` · metric `tg128`

| threads (-t) | tg128 (tok/s) | vs best |
|:--|--:|--:|
| 1 | 125.1 | 97% |
| 5 | 127.2 | 98% |
| 10 | 129.4 | 100% |
| 20 | 89.7 | 69% |

**Best**: `-t 10` at 129.4 tok/s
**Slowest tested**: `-t 20` at 89.7 tok/s (1.44x spread)
**Against the physical-core default** (`-t 10`, 129.4 tok/s): 1.00x

Use this in your run:

```bash
LAB_N_THREADS=10 make bench
```

## Giải thích

**Hình dạng đường cong: gần như phẳng từ 1 đến 10 thread, rồi rơi mạnh ở 20 thread.**
Cụ thể là 125.1 → 127.2 → 129.4 tok/s (1 → 10 thread chỉ +3.4%), sau đó tụt còn 89.7 tok/s
(69%) ở 20 thread. Đỉnh nằm đúng ở số core vật lý (10), nhưng hầu như không có "knee" phía trước
đỉnh. Chỉ 1 thread đã đạt 97% tốc độ tối đa.

**Vì sao đường cong phẳng, khác với kỳ vọng "càng nhiều core càng nhanh cho tới số core vật lý":**
chạy với `ngl=99` nghĩa là toàn bộ layer được offload lên GPU qua Metal. Phép nhân ma trận và việc
đọc weights khi decode chạy trên GPU, không chạy trên CPU thread. CPU thread chỉ làm phần việc
nhỏ: dựng compute graph, dispatch kernel Metal và sampling. Vì vậy 1 thread đã gần đủ. Thời gian
mỗi token (~7.7 ms) bị chặn bởi GPU và overhead dispatch, không phải bởi số thread. Kiểm chứng
bằng `ngl=0` (`01-ngl-cpu-vs-gpu.md`): khi CPU phải tự làm toàn bộ việc tính toán, decode chỉ còn
65 tok/s. Thread count chỉ quan trọng trong cấu hình đó.

**Vì sao 20 thread chậm đi 31%:** M1 Pro có 10 core (8 P-core + 2 E-core) và không có
SMT/hyper-threading, nên 20 thread là oversubscription: 2 thread tranh nhau 1 core. Trong
llama.cpp, các thread đồng bộ ở barrier sau mỗi op. Chỉ cần một thread bị OS tạm ngưng
(preempt) là cả nhóm phải chờ, kèm thêm chi phí context switch. Các thread thừa còn chiếm CPU
của thread driver Metal, làm chậm cả việc dispatch kernel lên GPU.

**Nhiễu giữa các lần đo:** lần chạy `make tune` trước cho 111.4 tok/s ở 1 thread, lần này là
125.1. Chênh lệch giữa 1 và 10 thread (~3%) vì vậy nằm trong nhiễu đo. Chỉ có cú rơi ở 20 thread
(−31%) là lặp lại ổn định qua cả hai lần.

**Before/after:** cấu hình tốt nhất `-t 10` là mặc định, nên speedup = **1.00×**. So với cấu hình
tệ nhất `-t 20` (89.7 tok/s) thì gấp **1.44×**. Bài học: khi đã offload hết lên GPU, thread count
không phải knob quan trọng, miễn là đừng vượt quá số core vật lý.
