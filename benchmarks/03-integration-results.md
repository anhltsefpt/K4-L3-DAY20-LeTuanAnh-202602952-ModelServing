# 03 - Integrate: RAG pipeline run

Host `Darwin-arm64` · llama.cpp `b10488` ·
retrieval backend: **keyword overlap** · 3 queries

| Query | Contexts retrieved | embed (ms) | retrieve (ms) | llm (ms) | total (ms) |
|:--|--:|--:|--:|--:|--:|
| Why is goodput more useful than raw throughp... | goodput, paged, radix | 0.0 | 0.0 | 1831.6 | 1831.7 |
| What problem does PagedAttention actually so... | paged, radix, disagg | 0.0 | 0.0 | 660.9 | 660.9 |
| When does splitting prefill and decode help?... | disagg, radix, batching | 0.0 | 0.0 | 1228.6 | 1228.7 |

Mean per stage (ms): embed **0.0** · retrieve **0.0** ·
llm **1240.4** · total **1240.4**
Dominant stage: **llm** (100% of total)

## Answers returned

**Why is goodput more useful than raw throughput?**

> Based on the provided context, **Goodput is more useful than raw throughput** because it focuses on **requests per second (RPS) that met specific targets** rather than just the total capacity available.

Here is the breakdown based on the text:

*   **Goodput** counts only requests per second that met the **TTFT** (Target Throughput at Full Load) and **TPOT** (Target Throughput at Partial Load) ta

**What problem does PagedAttention actually solve?**

> PagedAttention solves the problem of **internal fragmentation in GPU memory** caused by storing the Key-Value (KV) cache in non-contiguous pages.

By partitioning the KV cache into separate pages, it allows the GPU to utilize more of its available memory, thereby reducing wasted memory that would otherwise be consumed by the internal fragmentation of contiguous memory blocks.

**When does splitting prefill and decode help?**

> Splitting prefill and decode helps when the **compute-bound prefill** requires a separate memory pool to be accessed, while the **memory-bound decode** can be handled efficiently by a shared pool.

Specifically, this optimization occurs when:
1.  **Prefill is Compute-Bound:** The prefilling phase requires significant memory bandwidth or dedicated compute resources that cannot be shared with the de


## Phần nào của N16–N19 là real

| Day | Piece | Real hay stub? |
|:--|:--|:--|
| N16 Cloud/IaC | Không có hạ tầng cloud. Toàn bộ chạy local trên MacBook | **stub** |
| N17 Data pipeline | Không có ingest. Tài liệu là `TOY_DOCS` hard-code trong `pipeline.py` | **stub** |
| N18 Lakehouse | Không có lakehouse. "Kho dữ liệu" là một list Python trong bộ nhớ | **stub** |
| N19 Vector + features | Không có vector index hay embedding server. `retrieve()` dùng **keyword overlap** | **stub** |
| N20 Serving | `llama-server` (Qwen3.5 0.8B Q4_K_M, Metal) | **real** |

**Stage chiếm nhiều thời gian nhất có đúng như kỳ vọng không?** Có, và đó là hệ quả trực tiếp
của việc stub. Embed và retrieve đo được 0.0 ms vì không có embedding model, và keyword overlap
trên vài tài liệu trong bộ nhớ chỉ mất micro-giây. Vì vậy LLM chiếm 100% của 1240 ms. Con số này
**không** có nghĩa embed và retrieve miễn phí trong một hệ thống thật. Khi có embedding model và
vector DB qua mạng, hai stage đó sẽ hiện ra trên bảng.

**Bên trong stage LLM, decode chiếm phần lớn.** Theo server timings: prefill mất 165 / 80 / 79 ms
(trung bình ~108 ms, ~9%), còn decode mất 1548 / 562 / 1129 ms (~91%). Query 1 chậm nhất vì sinh
đủ 200 token (chạm `max_tokens`, câu trả lời bị cắt), với ~7.7 ms/token, đúng bằng TPOT đo ở
`make bench`. Latency tỉ lệ gần như tuyến tính với số token output.

**Nếu phải giảm latency xuống một nửa, tôi tấn công decode bằng cách giảm số token output:**
yêu cầu trả lời ngắn trong system prompt và hạ `max_tokens` (200 → ~100). Đây là đòn bẩy trực
tiếp nhất vì latency ≈ prefill + N_out × TPOT. Các knob khác ít tác dụng hơn: thread count gần
như không ảnh hưởng (`make tune`: 1.00×), 2-bit không nhanh hơn 4-bit trên máy này, còn prefill
chỉ chiếm ~9%.

**Ghi chú về chất lượng:** model 0.8B trả lời có lỗi nội dung dù context đúng. Nó diễn giải
TTFT thành "Target Throughput at Full Load", và nói PagedAttention giải quyết fragmentation
"do lưu KV cache ở các page không liên tục", trong khi thực tế ngược lại: lưu liên tục và cấp
phát trước mới gây phân mảnh. Retrieval đúng nhưng generator yếu, nên trong hệ thống thật cần
model lớn hơn hoặc thêm bước kiểm tra câu trả lời.
