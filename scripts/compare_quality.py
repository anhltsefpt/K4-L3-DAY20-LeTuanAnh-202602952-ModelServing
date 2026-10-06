"""Hỏi cùng câu hỏi cho 2 server (4-bit :8080, 2-bit :8090) và in câu trả lời cạnh nhau."""
import json
import time
import urllib.request

SERVERS = {"Q4_K_M (4-bit)": 8080, "UD-Q2_K_XL (2-bit)": 8090}
QUESTIONS = [
    "Thủ đô của Việt Nam là gì? Trả lời một câu.",
    "Một cửa hàng bán 3 quyển vở, mỗi quyển 12.000 đồng. Khách đưa 50.000 đồng. Tiền thối lại là bao nhiêu? Giải thích ngắn.",
    "Write a Python function that checks whether a number is prime.",
    "Explain in 2 sentences why LLM decoding is memory-bandwidth bound.",
]


def ask(port, q):
    body = json.dumps({
        "messages": [{"role": "user", "content": q}],
        "max_tokens": 200,
        "temperature": 0,  # temperature 0 để so sánh công bằng, không ngẫu nhiên
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"].strip(), time.time() - t0


for i, q in enumerate(QUESTIONS, 1):
    print("=" * 80)
    print(f"Câu {i}: {q}")
    for name, port in SERVERS.items():
        answer, secs = ask(port, q)
        print(f"\n--- {name}  ({secs:.2f}s)\n{answer}")
    print()
