"""Load and search the dense course index."""

import json
import os
import warnings


def load_index(index_dir):
    import numpy as np

    with open(os.path.join(index_dir, "config.json"), encoding="utf-8") as f:
        config = json.load(f)
    embeddings = np.load(os.path.join(index_dir, "embeddings.npy"))
    with open(os.path.join(index_dir, "chunks.jsonl"), encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]

    if embeddings.ndim != 2:
        raise ValueError("embeddings.npy must contain a two-dimensional array")
    if embeddings.shape[0] != len(chunks):
        raise ValueError("the embedding and chunk counts differ")
    if embeddings.shape[1] != config["dim"]:
        raise ValueError("the embedding dimension differs from config.json")

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return config, embeddings / norms, chunks


def create_query_encoder(model_name):
    os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
    from fastembed import TextEmbedding

    with warnings.catch_warnings():
        # The stored index uses the mean-pooled representation from version 0.8.
        warnings.filterwarnings(
            "ignore",
            message=r"The model .* now uses mean pooling instead of CLS embedding.*",
        )
        return TextEmbedding(model_name, providers=["CPUExecutionProvider"])


def search_index(embeddings, chunks, query_vector, k=5, topic=None, threshold=0.0):
    import numpy as np

    if k < 1:
        raise ValueError("k must be at least 1")

    query = np.asarray(query_vector, dtype=np.float32)
    if query.ndim != 1 or query.shape[0] != embeddings.shape[1]:
        raise ValueError("the query dimension differs from the index")
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0:
        raise ValueError("the query embedding is empty")

    similarities = embeddings @ (query / query_norm)
    results = []
    for index in np.argsort(-similarities, kind="stable"):
        chunk = chunks[index]
        if topic and chunk.get("topic") != topic:
            continue

        cosine = float(np.clip(similarities[index], -1.0, 1.0))
        score = (cosine + 1.0) / 2.0
        if score < threshold:
            continue

        angular_distance = float(np.sqrt(2.0 * (1.0 - cosine)))
        results.append(
            {
                "score": round(score, 4),
                "annoy_distance": round(angular_distance, 4),
                "file": chunk["file"],
                "topic": chunk.get("topic"),
                "chunk_id": chunk["chunk_id"],
                "snippet": chunk["text"][:300],
            }
        )
        if len(results) == k:
            break
    return results
