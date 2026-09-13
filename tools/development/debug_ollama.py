import sys
sys.path.insert(0, '.')
import traceback
import json
import requests
from app.services.knowledge.knowledge_service import knowledge_service

res = knowledge_service.search('and pump. Cite the source document and page numbers for every major recommendation.', 2)
context = "\n\n".join(f"[{r['chunk_id']}] {r['text']}" for r in res)
prompt = (
    "Use only this local context. If insufficient, say so.\n"
    f"CONTEXT:\n{context}\n\nQUESTION: and pump. Cite the source document and page numbers for every major recommendation."
)
try:
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen3:8b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
        },
        timeout=120,
    )
    print("Status:", r.status_code)
    try:
        print("JSON:", r.json())
    except:
        print("Text:", r.text)
except Exception as e:
    traceback.print_exc()
