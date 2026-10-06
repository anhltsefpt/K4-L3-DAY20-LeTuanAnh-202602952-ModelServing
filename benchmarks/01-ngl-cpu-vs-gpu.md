# 01 - Extra: CPU-only (`ngl=0`) vs full Metal offload (`ngl=99`)

Model `Qwen3.5-0.8B-Q4_K_M.gguf` (497 MiB) · host `Darwin-arm64` (Apple M1 Pro, 16 GB) · llama.cpp `b10488`
Command:

```bash
runtime/b10488/llama-b10488/llama-bench -m models/Qwen3.5-0.8B-Q4_K_M.gguf \
  -ngl 0,99 -t 10 -p 512 -n 128 -r 3 -o md
```

| ngl | Phase | Test | tok/s |
|--:|:--|:--|--:|
| 0 (CPU only) | prefill | pp512 | 372.32 ± 60.13 |
| 0 (CPU only) | decode | tg128 | 65.11 ± 3.17 |
| 99 (Metal GPU) | prefill | pp512 | 2325.13 ± 10.63 |
| 99 (Metal GPU) | decode | tg128 | 129.65 ± 0.24 |

**Speedup ngl=0 → ngl=99:** prefill **6.25×** · decode **1.99×**

(llama-bench prints the rows in order ngl=0 then ngl=99; the backend column reads
`MTL,BLAS` for both because that is the build, not the per-run offload.)
