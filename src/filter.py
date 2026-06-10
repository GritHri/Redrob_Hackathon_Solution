import pandas as pd
import json
import sys
from pathlib import Path

CONSULTING_FIRMS = {
    "Accenture", "Capgemini", "Cognizant",
    "HCL", "Infosys", "Mindtree",
    "Mphasis", "TCS", "Tech Mahindra", "Wipro",
}

AI_KEYWORDS = {
    "embedding", "vector", "retrieval", "ranking", "recommendation",
    "nlp", "llm", "machine learning", "deep learning", "faiss",
    "transformer", "fine-tun", "rag", "search", "pytorch", "tensorflow",
    "neural", "bert", "gpt",
}

NOISE_TITLES = {
    "Business Analyst",
    "HR Manager",
    "Mechanical Engineer",
    "Accountant",
    "Project Manager",
    "Customer Support",
    "Operations Manager",
    "Content Writer",
    "Sales Executive",
    "Civil Engineer",
    "Graphic Designer",
    "Marketing Manager",
}

def load_candidates(jsonl_path: str) -> pd.DataFrame:
    records = []
    with open(jsonl_path) as f:
        for line in f:
            records.append(json.loads(line))
    return pd.json_normalize(records)

def apply_title_filter(df: pd.DataFrame) -> pd.DataFrame:
    mask = ~df["profile.current_title"].isin(NOISE_TITLES)
    dropped = (~mask).sum()
    print(f"  title filter : -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)

def apply_consulting_filter(df: pd.DataFrame) -> pd.DataFrame:
    def is_pure_consulting_no_ai(row) -> bool:
        companies = {job.get("company", "") for job in (row.get("career_history") or [])}
        if companies - CONSULTING_FIRMS:
            return False  # has at least one non-consulting company → keep
        skills_text = " ".join(s.get("name", "").lower() for s in (row.get("skills") or []))
        career_text = " ".join(
            (job.get("description", "") or "").lower()
            for job in (row.get("career_history") or [])
        )
        combined = skills_text + " " + career_text
        return not any(kw in combined for kw in AI_KEYWORDS)

    mask = ~df.apply(is_pure_consulting_no_ai, axis=1)
    dropped = (~mask).sum()
    print(f"  consulting filter: -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)

def apply_location_filter(df: pd.DataFrame) -> pd.DataFrame:
    is_india = df["profile.country"] == "India"
    willing = df["redrob_signals.willing_to_relocate"].astype(bool)
    mask = is_india | willing
    dropped = (~mask).sum()
    print(f"  location filter: -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/candidates.jsonl"
    df = load_candidates(path)
    print(f"{len(df):,} loaded")
    df = apply_title_filter(df)
    df = apply_consulting_filter(df)
    df = apply_location_filter(df)
    print(f"\nfinal: {len(df):,} candidates")
    print(df["profile.current_title"].value_counts().head(10).to_string())
