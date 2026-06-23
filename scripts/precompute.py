#!/usr/bin/env python3
"""
Offline pre-computation: encode career descriptions for all filtered candidates.

Run once before ranking. No time limit applies here.

Outputs:
    artifacts/career_embeddings.npy  — (N, 384) float32, L2-normalised
    artifacts/candidate_ids.json     — ordered candidate_ids (index → id)
    artifacts/jd_embedding.npy       — (384,) JD embedding, L2-normalised

Usage:
    python scripts/precompute.py
    python scripts/precompute.py --candidates data/candidates.jsonl --out-dir artifacts
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

DATA_PATH = ROOT / "data" / "candidates.jsonl"
ARTIFACTS_DIR = ROOT / "artifacts"

# JD text to embed: technical/experience sections only.
# Excluded: location, salary, notice period, culture.
# Source: docs/hackathon_context/job_description.docx
JD_TEXT = """
Senior AI Engineer. Own the ranking, retrieval, and matching systems.
Ship ranking system using embeddings, hybrid retrieval, LLM-based re-ranking.
Set up evaluation infrastructure: offline benchmarks, online A/B testing, recruiter-feedback loops.
Candidate-JD matching at scale.

Required: production experience with embeddings-based retrieval systems — sentence-transformers,
BGE, E5 deployed to real users. Handled embedding drift, index refresh, retrieval-quality regression.
Production experience with vector databases or hybrid search — Pinecone, Weaviate, Qdrant, Milvus,
OpenSearch, Elasticsearch, FAISS. Hands-on experience designing evaluation frameworks for ranking:
NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation.

Nice to have: LLM fine-tuning LoRA QLoRA PEFT. Learning-to-rank models. HR-tech marketplace products.

Ideal: 6-8 years experience, 4-5 in applied ML/AI at product companies not pure services.
Shipped end-to-end ranking search recommendation system to real users at meaningful scale.
Built recommendation engine, search ranking, retrieval pipeline, vector search, embedding-based ranking,
information retrieval, hybrid search, semantic search, re-ranking, candidate matching.
Understands retrieval quality regression, A/B testing ranking systems, NDCG MRR MAP evaluation.
"""


def build_career_text(record: dict) -> str:
    """Concatenate all career_history descriptions. Title+company context included."""
    parts = []
    for job in (record.get("career_history") or []):
        title = (job.get("title") or "").strip()
        company = (job.get("company") or "").strip()
        desc = (job.get("description") or "").strip()
        if desc:
            parts.append(f"{title} at {company}: {desc}")
        elif title:
            parts.append(f"{title} at {company}")
    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default=str(DATA_PATH))
    parser.add_argument("--out-dir", default=str(ARTIFACTS_DIR))
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading model: {args.model}")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(args.model)

    # Load all records into memory, then filter via filter.py.
    # Supports both JSONL (candidates.jsonl) and JSON array (sample_candidates.json).
    print(f"Loading candidates from {args.candidates} ...")
    with open(args.candidates) as f:
        raw = f.read(1)
        f.seek(0)
        if raw == "[":
            records = json.load(f)
        else:
            records = [json.loads(line) for line in f if line.strip()]
    print(f"  Loaded: {len(records):,}")

    import pandas as pd
    from filter import run_all_filters

    df = pd.json_normalize(records)
    df = run_all_filters(df)
    print(f"  After filters: {len(df):,}")

    # Recover nested structure for career text extraction
    id_set = set(df["candidate_id"].tolist())
    record_by_id = {r["candidate_id"]: r for r in records if r["candidate_id"] in id_set}
    ordered_ids = df["candidate_id"].tolist()

    # Build one text string per candidate
    print("Building career texts...")
    texts = []
    empty = 0
    for cid in ordered_ids:
        text = build_career_text(record_by_id[cid])
        if not text.strip():
            text = "no career description"
            empty += 1
        texts.append(text)
    print(f"  Built {len(texts):,} texts  (empty descriptions: {empty})")

    # Encode
    print(f"Encoding {len(texts):,} career texts  batch={args.batch_size} ...")
    t0 = time.time()
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,  # L2-normalise: rank-time dot product == cosine similarity
        convert_to_numpy=True,
    )
    elapsed = time.time() - t0
    print(f"  Encoded in {elapsed:.1f}s  shape={embeddings.shape}  dtype={embeddings.dtype}")

    # Encode JD
    print("Encoding JD ...")
    jd_vec = model.encode(JD_TEXT, normalize_embeddings=True, convert_to_numpy=True)
    print(f"  JD embedding: {jd_vec.shape}")

    # Save
    emb_path = out_dir / "career_embeddings.npy"
    ids_path = out_dir / "candidate_ids.json"
    jd_path = out_dir / "jd_embedding.npy"

    np.save(emb_path, embeddings)
    ids_path.write_text(json.dumps(ordered_ids))
    np.save(jd_path, jd_vec)

    size_mb = embeddings.nbytes / 1024 / 1024
    print(f"\nArtifacts saved to {out_dir}/")
    print(f"  career_embeddings.npy  {size_mb:.1f} MB")
    print(f"  candidate_ids.json     {len(ordered_ids):,} ids")
    print(f"  jd_embedding.npy       {jd_vec.shape}")

    # Sanity: top 10 semantic matches
    print("\nTop 10 semantic matches (sanity check):")
    scores = embeddings @ jd_vec
    top_idx = scores.argsort()[::-1][:10]
    for rank, idx in enumerate(top_idx, 1):
        cid = ordered_ids[idx]
        r = record_by_id[cid]
        title = r.get("profile", {}).get("current_title", "?")
        loc = r.get("profile", {}).get("location", "?")
        print(f"  {rank:2d}. {cid}  score={scores[idx]:.4f}  {title}  [{loc}]")


if __name__ == "__main__":
    main()
