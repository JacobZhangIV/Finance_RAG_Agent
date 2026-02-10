#!/usr/bin/env python3
"""
RAG 检索：对语料做 embedding，对问题做 embedding，检索 top-k 证据并输出供 LLM 使用。
需设置环境变量 OPENAI_API_KEY。
用法:
  python rag_retrieve.py build              # 从 data/corpus/*.jsonl 构建索引
  python rag_retrieve.py query "2025 营业额是多少" --top-k 5   # 检索并输出
"""
import json
import os
import sys
import glob

from config import BASE_DIR, CORPUS_DIR

# 索引文件放在语料目录
EMBEDDINGS_NPY = os.path.join(CORPUS_DIR, "embeddings.npy")
EMBEDDINGS_META_JSON = os.path.join(CORPUS_DIR, "embeddings_meta.json")
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
DEFAULT_TOP_K = 5


def _get_client():
    try:
        from openai import OpenAI
    except ImportError:
        print("请先安装: pip install openai")
        sys.exit(1)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("请设置环境变量 OPENAI_API_KEY")
        sys.exit(1)
    return OpenAI()


def embed_texts(client, texts):
    """调用 OpenAI 对一批文本做 embedding，返回 list of list (float)."""
    out = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        # 空串会导致 API 报错，用空格代替
        batch = [t if t.strip() else " " for t in batch]
        r = client.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        for e in r.data:
            out.append(e.embedding)
    return out


def load_corpus_jsonl():
    """加载 data/corpus 下所有 .jsonl，返回 list of dict (chunk)."""
    os.makedirs(CORPUS_DIR, exist_ok=True)
    pattern = os.path.join(CORPUS_DIR, "*.jsonl")
    files = glob.glob(pattern)
    chunks = []
    for path in sorted(files):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunks.append(json.loads(line))
    return chunks


def build_index():
    """从语料 JSONL 构建 embedding 索引并保存。"""
    import numpy as np

    chunks = load_corpus_jsonl()
    if not chunks:
        print("未找到语料，请先在 data/corpus/ 下生成 .jsonl（如运行 htm_to_corpus.py）")
        sys.exit(1)

    texts = [c["text"] for c in chunks]
    client = _get_client()
    print(f"正在对 {len(texts)} 条 chunk 做 embedding ...")
    embeddings = embed_texts(client, texts)
    arr = np.array(embeddings, dtype=np.float32)
    meta = [
        {
            "chunk_id": c.get("chunk_id", ""),
            "type": c.get("type", ""),
            "source": c.get("source", {}),
            "text": c["text"],
        }
        for c in chunks
    ]

    np.save(EMBEDDINGS_NPY, arr)
    with open(EMBEDDINGS_META_JSON, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"索引已保存: {EMBEDDINGS_NPY}, {EMBEDDINGS_META_JSON}")


def cosine_similarity(a, b):
    """a 与 b 为向量，返回标量相似度。"""
    import numpy as np
    a, b = np.asarray(a), np.asarray(b)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def query_index(question, top_k=DEFAULT_TOP_K):
    """
    对问题做 embedding，在索引中检索 top-k，返回供 LLM 使用的结构：
    { "question": "...", "evidence": [ { "chunk_id", "source", "text", "score" }, ... ] }
    """
    import numpy as np

    if not os.path.isfile(EMBEDDINGS_NPY) or not os.path.isfile(EMBEDDINGS_META_JSON):
        print("未找到索引，请先运行: python rag_retrieve.py build")
        sys.exit(1)

    arr = np.load(EMBEDDINGS_NPY)
    with open(EMBEDDINGS_META_JSON, "r", encoding="utf-8") as f:
        meta = json.load(f)

    client = _get_client()
    q_emb = embed_texts(client, [question])[0]
    scores = [cosine_similarity(q_emb, row) for row in arr]
    idx = np.argsort(scores)[::-1][:top_k]

    evidence = []
    for i in idx:
        m = meta[i]
        evidence.append({
            "chunk_id": m["chunk_id"],
            "source": m["source"],
            "text": m["text"],
            "score": round(scores[i], 4),
        })

    return {"question": question, "evidence": evidence}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "build":
        build_index()
        return

    if cmd == "query":
        # python rag_retrieve.py query "问题" [--top-k 5] [--format json|prompt]
        args = sys.argv[2:]
        q = None
        top_k = DEFAULT_TOP_K
        out_format = "json"
        i = 0
        while i < len(args):
            if args[i] == "--top-k" and i + 1 < len(args):
                top_k = int(args[i + 1])
                i += 2
                continue
            if args[i] == "--format" and i + 1 < len(args):
                out_format = args[i + 1].lower()
                i += 2
                continue
            q = args[i]
            i += 1
        if not q:
            print("用法: python rag_retrieve.py query \"你的问题\" [--top-k 5] [--format json|prompt]")
            sys.exit(1)
        result = query_index(q, top_k=top_k)
        if out_format == "prompt":
            lines = ["Question: " + result["question"], "", "Evidence (from filings):"]
            for j, e in enumerate(result["evidence"], 1):
                src = e.get("source", {})
                ref = f"{src.get('company', '')} | {src.get('form', '')} | {src.get('filing_date', '')}"
                lines.append(f"[{j}] ({ref})")
                lines.append(e["text"])
                lines.append("")
            print("\n".join(lines))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("子命令: build | query")
    sys.exit(1)


if __name__ == "__main__":
    main()
