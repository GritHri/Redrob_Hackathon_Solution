#!/usr/bin/env python3
"""
Rank top 100 candidates for the Senior AI Engineer JD.

Usage:
    python scripts/rank.py
    python scripts/rank.py --out submission/HriGrit.csv
    python scripts/rank.py --candidates data/candidates.jsonl --artifacts artifacts/

Must complete in < 5 min wall-clock on CPU (precompute is a separate step).
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scorer import (
    score_breakdown,
    JD_CORE_SKILLS,
    INDIA_PRODUCT_COMPANIES,
    GLOBAL_PRODUCT_COMPANIES,
)

ARTIFACTS_DIR = ROOT / "artifacts"
DATA_PATH = ROOT / "data" / "candidates.jsonl"
DEFAULT_OUT = ROOT / "submission" / "HriGrit.csv"


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------

def load_artifacts(artifacts_dir: Path):
    embeddings = np.load(artifacts_dir / "career_embeddings.npy")  # (N, 384) float32
    candidate_ids: list[str] = json.loads(
        (artifacts_dir / "candidate_ids.json").read_text()
    )
    jd_vec = np.load(artifacts_dir / "jd_embedding.npy")  # (384,) float32
    id_to_idx = {cid: i for i, cid in enumerate(candidate_ids)}
    return embeddings, id_to_idx, jd_vec


# ---------------------------------------------------------------------------
# Record loading — single JSONL pass, only fetch IDs we need
# ---------------------------------------------------------------------------

def load_records(jsonl_path: Path, id_set: set[str]) -> dict[str, dict]:
    records: dict[str, dict] = {}
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            cid = r.get("candidate_id")
            if cid in id_set:
                records[cid] = r
                if len(records) == len(id_set):
                    break  # found all we need
    return records


# ---------------------------------------------------------------------------
# Reasoning generation
# ---------------------------------------------------------------------------

_PROF_RANK = {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}


def make_reasoning(record: dict, bd: dict) -> str:
    """
    1–2 fact-specific sentences referencing actual candidate data, tied to JD.

    Sentence 1: <Title> (<N>yr); <top matching skills>; [ex-<product co>;] <city>.
    Sentence 2: <behavioral highlights>; <semantic score note if notable>.
    """
    p = record.get("profile") or {}
    sig = record.get("redrob_signals") or {}

    title = (p.get("current_title") or "Engineer").strip()
    yoe = int(p.get("years_of_experience") or 0)
    loc = (p.get("location") or p.get("country") or "India").strip()

    # Top JD-matching skills — exclude honeypot entries (expert/advanced + 0 months)
    matched: list[tuple[str, str, int]] = []
    for sk in record.get("skills") or []:
        name = (sk.get("name") or "").strip()
        if not name or name.lower() not in JD_CORE_SKILLS:
            continue
        prof = (sk.get("proficiency") or "beginner").lower()
        dur = int(sk.get("duration_months") or 0)
        if prof in ("expert", "advanced") and dur == 0:
            continue  # honeypot flag — skip
        matched.append((name, prof, dur))

    matched.sort(key=lambda x: (_PROF_RANK.get(x[1], 0), x[2]), reverse=True)
    skill_str = ", ".join(
        f"{name} ({prof})" for name, prof, _ in matched[:3]
    )

    # Best product company across entire career history
    all_product = INDIA_PRODUCT_COMPANIES | GLOBAL_PRODUCT_COMPANIES
    product_co: str | None = next(
        (
            job.get("company")
            for job in (record.get("career_history") or [])
            if job.get("company") in all_product
        ),
        None,
    )

    # Sentence 1
    parts = [f"{title} ({yoe}yr)"]
    if skill_str:
        parts.append(skill_str)
    if product_co:
        parts.append(f"ex-{product_co}")
    sentence1 = "; ".join(parts) + f"; {loc}."

    # Sentence 2 — behavioral + quality signals
    s2: list[str] = []
    if sig.get("open_to_work_flag"):
        s2.append("open to work")
    notice = sig.get("notice_period_days")
    if notice is not None and int(notice) <= 30:
        s2.append(f"{int(notice)}d notice")
    github = sig.get("github_activity_score")
    if github is not None and github != -1 and int(github) >= 40:
        s2.append(f"GitHub score {int(github)}")
    sem = bd.get("semantic", 0.0)
    if sem >= 0.30:
        s2.append(f"strong semantic match ({sem:.2f})")
    elif sem >= 0.20:
        s2.append(f"semantic match ({sem:.2f})")

    sentence2 = "; ".join(s2).capitalize() + "." if s2 else ""
    return (sentence1 + (" " + sentence2 if sentence2 else "")).strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    t0 = time.time()

    parser = argparse.ArgumentParser(description="Rank top-100 candidates")
    parser.add_argument("--candidates", default=str(DATA_PATH))
    parser.add_argument("--artifacts", default=str(ARTIFACTS_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--top", type=int, default=100)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load artifacts
    print("Loading artifacts...")
    embeddings, id_to_idx, jd_vec = load_artifacts(Path(args.artifacts))
    artifact_ids: list[str] = list(id_to_idx.keys())
    print(f"  {embeddings.shape[0]:,} candidates  {embeddings.shape[1]}-dim embeddings")

    # 2. Semantic scores — dot product == cosine (both L2-normalised)
    print("Computing semantic scores...")
    sem_scores: np.ndarray = embeddings @ jd_vec  # shape (N,)

    # 3. Load raw records for artifact candidates (single JSONL pass)
    print("Loading candidate records...")
    records = load_records(Path(args.candidates), set(artifact_ids))
    print(f"  Loaded {len(records):,} records")

    missing = len(artifact_ids) - len(records)
    if missing:
        print(f"  WARNING: {missing} artifact IDs not found in JSONL — skipped")

    # 4. Score every candidate
    print("Scoring...")
    results: list[tuple[str, float, dict, dict]] = []
    for cid in artifact_ids:
        rec = records.get(cid)
        if rec is None:
            continue
        sem = float(sem_scores[id_to_idx[cid]])
        bd = score_breakdown(rec, sem)
        results.append((cid, bd["final"], bd, rec))

    # 5. Sort: score desc, candidate_id asc for tie-breaking (per submission spec)
    results.sort(key=lambda x: (-x[1], x[0]))

    top = results[: args.top]
    if len(top) < args.top:
        print(f"  WARNING: only {len(top)} candidates available — fewer than {args.top}")

    elapsed_score = time.time() - t0
    print(f"  Scored {len(results):,} in {elapsed_score:.1f}s")
    print(f"  Score range: {top[0][1]:.4f} (rank 1) → {top[-1][1]:.4f} (rank {len(top)})")

    # 6. Write CSV
    print(f"\nWriting {out_path} ...")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, (cid, final_score, bd, rec) in enumerate(top, 1):
            reasoning = make_reasoning(rec, bd)
            writer.writerow([cid, rank, f"{final_score:.6f}", reasoning])

    elapsed_total = time.time() - t0
    print(f"Done in {elapsed_total:.1f}s total.\n")

    # 7. Top-10 preview
    print("Top 10:")
    for rank, (cid, s, bd, rec) in enumerate(top[:10], 1):
        p = rec.get("profile") or {}
        print(
            f"  {rank:2d}. {cid}  {s:.4f}"
            f"  sem={bd['semantic']:.2f}"
            f"  title={bd['title']:.2f}"
            f"  skills={bd['skills']:.2f}"
            f"  co={bd['company']:.2f}"
            f"  bm={bd['behavioral_multiplier']:.2f}"
            f"  cons={bd['consistency']:.2f}"
            f"  | {p.get('current_title')}  [{p.get('location')}]"
        )


if __name__ == "__main__":
    main()
