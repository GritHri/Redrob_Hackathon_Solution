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
    # core retrieval/ranking/search
    "embedding", "vector", "retrieval", "ranking", "recommendation",
    "search", "faiss", "bm25",
    # vector databases
    "pinecone", "weaviate", "qdrant", "milvus", "chroma", "pgvector",
    # LLM / NLP
    "nlp", "llm", "rag", "bert", "gpt", "transformer", "hugging",
    "langchain", "llamaindex", "semantic",
    # training / fine-tuning
    "machine learning", "deep learning", "neural",
    "fine-tun", "lora", "qlora", "peft",
    # frameworks
    "pytorch", "tensorflow",
    # generative AI
    "generative", "diffusion",
    # MLOps / serving
    "mlops", "kubeflow", "bentoml",
}

# Titles that signal wrong job family — but only drop if career also has no AI signal.
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

# CV / Speech / Robotics domain keywords (primary expertise signals)
CV_SPEECH_ROBOTICS_KW = {
    "computer vision", "opencv", "yolo", "object detection", "image classification",
    "image segmentation", "facial recognition", "face detection", "face recognition",
    "object tracking", "depth estimation", "stereo vision", "3d reconstruction",
    "pose estimation", "action recognition", "ocr", "optical character",
    "speech recognition", "text to speech", "tts", "asr", "voice recognition",
    "speaker recognition", "speech synthesis", "audio classification",
    "robotics", "ros", "autonomous vehicle", "self-driving", "lidar",
    "point cloud", "slam", "drone control", "robot arm",
}

# NLP / IR exposure signals — presence of ANY of these means not a pure CV/Speech/Robotics specialist
NLP_IR_KW = {
    "nlp", "natural language", "information retrieval", "text classification",
    "sentiment", "named entity", "question answering", "machine translation",
    "text summarization", "embedding", "vector search", "vector database",
    "retrieval", "ranking", "recommendation", "language model", "llm",
    "rag", "bert", "transformer", "gpt", "hugging", "search engine",
    "semantic search", "chatbot", "conversational", "dialogue",
    "langchain", "llamaindex", "word2vec", "glove",
    # vector databases and search engines — explicit IR tools
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "chroma", "pgvector",
    "elasticsearch", "opensearch", "bm25",
}

# Academic / research institution signals for pure-researcher filter
RESEARCH_INSTITUTION_KW = {
    "university", "institute", "iit ", "iisc", "iim ", "college",
    "research lab", "research institute", "laboratory", "academia",
    "national lab", "mit", "stanford", "cmu", "iiser",
}

# Production deployment evidence — presence means NOT a pure researcher
PRODUCTION_KW = {
    "production", "deployed", "shipped", "at scale", "real users",
    "live system", "serving", "latency", "throughput", "million users",
    "billion", "customers", "end-to-end", "pipeline", "api endpoint",
    "inference", "a/b test", "online experiment",
}


def _ai_signal(row) -> bool:
    """True if row has any AI signal in skills or career descriptions."""
    skills_text = " ".join(s.get("name", "").lower() for s in (row.get("skills") or []))
    career_text = " ".join(
        (job.get("description", "") or "").lower()
        for job in (row.get("career_history") or [])
    )
    combined = skills_text + " " + career_text
    return any(kw in combined for kw in AI_KEYWORDS)


def load_candidates(jsonl_path: str) -> pd.DataFrame:
    records = []
    with open(jsonl_path) as f:
        for line in f:
            records.append(json.loads(line))
    return pd.json_normalize(records)


def apply_title_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Unconditional drop for the 12 noise job families.
    JD explicitly states: 'Marketing Manager is not a fit, no matter how perfect
    their skill list looks.' Skills-array keyword stuffing is an explicit dataset trap.
    """
    mask = ~df["profile.current_title"].isin(NOISE_TITLES)
    dropped = (~mask).sum()
    print(f"  title filter:      -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)


def apply_consulting_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Drop if entire career is at consulting firms AND no AI keyword anywhere."""
    def is_pure_consulting_no_ai(row) -> bool:
        companies = {job.get("company", "") for job in (row.get("career_history") or [])}
        if companies - CONSULTING_FIRMS:
            return False
        return not _ai_signal(row)

    mask = ~df.apply(is_pure_consulting_no_ai, axis=1)
    dropped = (~mask).sum()
    print(f"  consulting filter: -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)


def apply_location_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Drop if outside India and not willing to relocate."""
    is_india = df["profile.country"] == "India"
    willing = df["redrob_signals.willing_to_relocate"].astype(bool)
    mask = is_india | willing
    dropped = (~mask).sum()
    print(f"  location filter:   -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)


def apply_yoe_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Drop if years_of_experience < 2 or > 18. JD: too junior or past reasonable scope."""
    yoe = df["profile.years_of_experience"].fillna(0)
    mask = (yoe >= 2) & (yoe <= 18)
    dropped = (~mask).sum()
    print(f"  yoe filter:        -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)


def apply_domain_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop if primary expertise is CV/Speech/Robotics with zero NLP/IR exposure.
    JD explicitly lists this as disqualifying: 'you'd be re-learning fundamentals here.'
    """
    def is_cv_speech_robotics_only(row) -> bool:
        skills_text = " ".join(s.get("name", "").lower() for s in (row.get("skills") or []))
        career_text = " ".join(
            (job.get("description", "") or "").lower()
            for job in (row.get("career_history") or [])
        )
        combined = skills_text + " " + career_text
        has_cv_sr = any(kw in combined for kw in CV_SPEECH_ROBOTICS_KW)
        has_nlp_ir = any(kw in combined for kw in NLP_IR_KW)
        return has_cv_sr and not has_nlp_ir

    mask = ~df.apply(is_cv_speech_robotics_only, axis=1)
    dropped = (~mask).sum()
    print(f"  domain filter:     -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)


def apply_researcher_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop if all career positions are at academic/research institutions AND
    no production deployment evidence. JD: tried pure researchers twice, didn't work.
    """
    def is_pure_researcher(row) -> bool:
        career = row.get("career_history") or []
        if not career:
            return False
        companies = [job.get("company", "").lower() for job in career]
        all_academic = all(
            any(kw in co for kw in RESEARCH_INSTITUTION_KW) for co in companies
        )
        if not all_academic:
            return False
        career_text = " ".join(
            (job.get("description", "") or "").lower() for job in career
        )
        return not any(kw in career_text for kw in PRODUCTION_KW)

    mask = ~df.apply(is_pure_researcher, axis=1)
    dropped = (~mask).sum()
    print(f"  researcher filter: -{dropped:,} → {mask.sum():,} remain")
    return df[mask].reset_index(drop=True)


def run_all_filters(df: pd.DataFrame) -> pd.DataFrame:
    df = apply_title_filter(df)
    df = apply_consulting_filter(df)
    df = apply_location_filter(df)
    df = apply_yoe_filter(df)
    df = apply_domain_filter(df)
    df = apply_researcher_filter(df)
    return df


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/candidates.jsonl"
    df = load_candidates(path)
    print(f"{len(df):,} loaded\n")
    df = run_all_filters(df)
    print(f"\nfinal: {len(df):,} candidates")
    print(df["profile.current_title"].value_counts().head(20).to_string())
