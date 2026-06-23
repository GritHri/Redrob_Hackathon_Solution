"""
Candidate scorer — pure functions, no I/O.

Entry point:
    score(record, semantic) -> float

Full breakdown for debugging/reasoning:
    score_breakdown(record, semantic) -> dict

Scoring formula (weights are design choices, not from hackathon docs):
    base  = semantic*0.35 + title*0.20 + skills*0.20 + company*0.15 + location*0.10
    final = base * behavioral_multiplier * consistency_score
"""

from datetime import date, datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Title tiers
# Source: docs/analyzed_data/job_title_distribution.md
# Scores are design choices based on JD priority ordering.
# ---------------------------------------------------------------------------

_TITLE_SCORES: dict[str, float] = {
    # Tier 1 — specialist ML/AI titles
    "Recommendation Systems Engineer":      1.00,
    "Machine Learning Engineer":            1.00,
    "Search Engineer":                      1.00,
    "Applied ML Engineer":                  1.00,
    "AI Engineer":                          1.00,
    "NLP Engineer":                         1.00,
    "Senior NLP Engineer":                  1.00,
    "Senior Machine Learning Engineer":     1.00,
    "Staff Machine Learning Engineer":      1.00,
    "Senior AI Engineer":                   1.00,
    "Lead AI Engineer":                     1.00,
    "Senior Applied Scientist":             1.00,
    # Tier 2 — ML adjacent
    "ML Engineer":                          0.75,
    "AI Research Engineer":                 0.75,
    "Data Scientist":                       0.75,
    "Senior Data Scientist":                0.75,
    "Junior ML Engineer":                   0.65,
    "AI Specialist":                        0.70,
    "Senior Software Engineer (ML)":        0.70,
    "Senior Engineer":                      0.45,
    # Tier 3 — technical, not ML-primary
    "Computer Vision Engineer":             0.40,  # CV-only filtered by F5; if here, has NLP/IR
    "Analytics Engineer":                   0.35,
    "Data Engineer":                        0.35,
    "Senior Data Engineer":                 0.35,
    "Data Analyst":                         0.30,
    "Backend Engineer":                     0.25,
    # Tier 4 — generic tech
    "Software Engineer":                    0.20,
    "Senior Software Engineer":             0.20,
    "Full Stack Developer":                 0.15,
    "Cloud Engineer":                       0.15,
    "Java Developer":                       0.10,
    ".NET Developer":                       0.10,
    "DevOps Engineer":                      0.10,
    "Mobile Developer":                     0.10,
    "Frontend Engineer":                    0.10,
    "QA Engineer":                          0.10,
}

# ---------------------------------------------------------------------------
# JD core skills
# Source: docs/hackathon_context/job_description.docx — "Things you absolutely need"
#         + "Things we'd like you to have"
# Skill names lowercased to match against lowercased candidate skill names.
# Exact names confirmed against full dataset scan (see docs/analyzed_data/).
# ---------------------------------------------------------------------------

JD_CORE_SKILLS: frozenset[str] = frozenset({
    # Embedding retrieval (JD: "absolutely need")
    "sentence transformers",
    "embeddings",
    "hugging face transformers",
    # Vector databases (JD: "absolutely need")
    "faiss",
    "pinecone",
    "weaviate",
    "qdrant",
    "milvus",
    "pgvector",
    "elasticsearch",
    "opensearch",
    # Search/retrieval concepts
    "information retrieval",
    "semantic search",
    "vector search",
    "recommendation systems",
    "bm25",
    "haystack",
    # Evaluation (JD: "absolutely need")
    "learning to rank",
    # LLM / RAG systems
    "llms",
    "rag",
    "langchain",
    "llamaindex",
    "fine-tuning llms",
    "prompt engineering",
    # ML frameworks
    "pytorch",
    "tensorflow",
    "nlp",
    # Fine-tuning (JD: "nice to have")
    "lora",
    "qlora",
    "peft",
})

_PROFICIENCY_WEIGHT: dict[str, float] = {
    "expert":       1.00,
    "advanced":     0.80,
    "intermediate": 0.50,
    "beginner":     0.20,
}

# Soft-cap divisor for skills normalisation: 4 strong skills = max score
_SKILLS_CAP = 4.0

# ---------------------------------------------------------------------------
# Company tiers
# Source: docs/analyzed_data/company_distribution.md
# ---------------------------------------------------------------------------

INDIA_PRODUCT_COMPANIES: frozenset[str] = frozenset({
    "Swiggy", "Razorpay", "CRED", "Zomato", "Flipkart", "Meesho", "PhonePe",
    "Paytm", "Ola", "Nykaa", "PolicyBazaar", "BYJU'S", "Vedantu", "Unacademy",
    "Freshworks", "PharmEasy", "upGrad", "Dream11", "Zoho", "InMobi",
    "Rephrase.ai", "Aganitha", "Niramai", "Saarthi.ai", "Sarvam AI", "Krutrim",
    "Mad Street Den", "Observe.AI", "Wysa", "Verloop.io", "Haptik", "Yellow.ai",
    "Locobuzz", "Glance", "Genpact AI",
})

GLOBAL_PRODUCT_COMPANIES: frozenset[str] = frozenset({
    "Amazon", "Google", "Netflix", "Salesforce", "Uber", "Meta",
    "Microsoft", "Adobe", "Apple", "LinkedIn",
})

CONSULTING_COMPANIES: frozenset[str] = frozenset({
    "Infosys", "Wipro", "TCS", "Capgemini", "HCL", "Mindtree",
    "Cognizant", "Accenture", "Tech Mahindra", "Mphasis",
})

FICTIONAL_COMPANIES: frozenset[str] = frozenset({
    "Initech", "Pied Piper", "Wayne Enterprises", "Acme Corp",
    "Stark Industries", "Hooli", "Globex Inc", "Dunder Mifflin",
})

# ---------------------------------------------------------------------------
# Location
# Source: docs/hackathon_context/job_description.docx
# ---------------------------------------------------------------------------

_PREFERRED_CITIES = {"pune", "noida"}
_TIER1_INDIA_CITIES = {
    "hyderabad", "mumbai", "bangalore", "bengaluru",
    "delhi", "gurgaon", "gurugram", "chennai", "kolkata",
    "pune", "noida",
}

# Reference date for recency calculations
_REF_DATE = date(2026, 6, 13)


# ---------------------------------------------------------------------------
# Sub-score functions — all return [0.0, 1.0]
# ---------------------------------------------------------------------------

def title_score(record: dict) -> float:
    title = (record.get("profile") or {}).get("current_title", "")
    return _TITLE_SCORES.get(title, 0.10)


def skills_score(record: dict) -> float:
    """
    Explicit set membership against JD core skills.
    Weighted by proficiency × capped duration. Normalised to [0, 1].
    expert/advanced + duration_months=0 → skip (honeypot signal; consistency_score penalises).
    """
    total = 0.0
    for skill in (record.get("skills") or []):
        name = (skill.get("name") or "").lower().strip()
        if name not in JD_CORE_SKILLS:
            continue
        prof = (skill.get("proficiency") or "beginner").lower()
        dur = skill.get("duration_months") or 0
        # Honeypot signal: claimed expert with zero months — skip this skill
        if prof in ("expert", "advanced") and dur == 0:
            continue
        prof_w = _PROFICIENCY_WEIGHT.get(prof, 0.20)
        dur_w = min(dur, 120) / 120.0
        total += prof_w * dur_w

    return min(total / _SKILLS_CAP, 1.0)


def company_score(record: dict) -> float:
    """
    Looks at all companies in career_history, not just current.
    JD: 'currently at consulting but prior product = fine.'
    """
    companies = {
        job.get("company", "")
        for job in (record.get("career_history") or [])
    }
    companies.discard("")

    if companies & INDIA_PRODUCT_COMPANIES:
        return 1.00
    if companies & GLOBAL_PRODUCT_COMPANIES:
        return 0.90
    # Unknown companies (not consulting, not fictional) — likely startups not in our list
    unknown = companies - CONSULTING_COMPANIES - FICTIONAL_COMPANIES
    if unknown:
        return 0.60
    if companies & CONSULTING_COMPANIES:
        # Passed F2 only because has AI signal — keep but penalise
        return 0.35
    # Only fictional companies (synthetic noise background)
    return 0.45


def location_score(record: dict) -> float:
    """Source: JD docx — Pune/Noida preferred; Hyderabad/Mumbai/Delhi NCR welcome."""
    p = record.get("profile") or {}
    sig = record.get("redrob_signals") or {}
    loc = (p.get("location") or "").lower()
    country = (p.get("country") or "").lower()

    if country == "india":
        if any(city in loc for city in _PREFERRED_CITIES):
            return 1.00
        if any(city in loc for city in _TIER1_INDIA_CITIES):
            return 0.85
        return 0.70 if sig.get("willing_to_relocate") else 0.55

    # Outside India — passed F3 only because willing_to_relocate=True
    return 0.35


def behavioral_multiplier(record: dict) -> float:
    """
    Combines availability, quality proxies, and market demand into [0.5, 1.2].
    JD: 'down-weight candidates who haven't logged in for 6 months with 5% response rate.'
    Range [0.5, 1.2] is a design choice — no range specified in source docs.
    """
    sig = record.get("redrob_signals") or {}

    # --- Availability ---
    days = _days_inactive(sig.get("last_active_date"))
    recency = max(0.0, 1.0 - days / 180.0)

    response = float(sig.get("recruiter_response_rate") or 0.5)
    interview = float(sig.get("interview_completion_rate") or 0.5)

    availability = recency * 0.40 + response * 0.35 + interview * 0.25
    if sig.get("open_to_work_flag"):
        availability = min(1.0, availability * 1.15)

    # Notice period (JD: sub-30 great, 30+ bar gets higher)
    notice = int(sig.get("notice_period_days") or 60)
    if notice <= 30:
        notice_f = 1.00
    elif notice <= 60:
        notice_f = 0.88
    elif notice <= 90:
        notice_f = 0.75
    else:
        notice_f = 0.60

    # --- Quality proxies ---
    github = sig.get("github_activity_score")
    # -1 = no GitHub linked → neutral, not penalised (CLAUDE.md: -1 if no GitHub)
    github_s = 0.50 if (github is None or github == -1) else float(github) / 100.0

    assessments = sig.get("skill_assessment_scores") or {}
    assess_s = (
        sum(assessments.values()) / len(assessments) / 100.0
        if assessments else 0.50
    )

    completeness = float(sig.get("profile_completeness_score") or 50) / 100.0

    quality = github_s * 0.30 + assess_s * 0.40 + completeness * 0.30

    # --- Market demand ---
    views = float(sig.get("profile_views_received_30d") or 0)
    searches = float(sig.get("search_appearance_30d") or 0)
    saved = float(sig.get("saved_by_recruiters_30d") or 0)
    market = min(1.0, (views / 200.0 + searches / 500.0 + saved / 10.0) / 3.0)

    raw = (availability * 0.50 + quality * 0.30 + market * 0.20) * notice_f
    return round(max(0.5, min(1.2, 0.5 + raw * 0.7)), 4)


def consistency_score(record: dict) -> float:
    """
    Honeypot detection: expert/advanced proficiency + duration_months=0 → flag.
    Source: submission_spec.docx — 'expert proficiency in 10 skills with 0 years used.'
    Each flag reduces score by 0.25; minimum 0.0.
    """
    flags = sum(
        1
        for skill in (record.get("skills") or [])
        if (skill.get("proficiency") or "").lower() in ("expert", "advanced")
        and (skill.get("duration_months") or 0) == 0
    )
    return round(max(0.0, 1.0 - flags * 0.25), 4)


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------

def score(record: dict, semantic: float) -> float:
    """
    Final score for one candidate.

    Args:
        record:   full candidate dict (nested, not pd.json_normalize'd)
        semantic: cosine similarity of career embedding vs JD embedding [0, 1]

    Returns:
        float in [0, ~1.2]
    """
    sem = max(0.0, min(1.0, float(semantic)))
    base = (
        sem                        * 0.35
        + title_score(record)      * 0.20
        + skills_score(record)     * 0.20
        + company_score(record)    * 0.15
        + location_score(record)   * 0.10
    )
    return round(max(0.0, base * behavioral_multiplier(record) * consistency_score(record)), 6)


def score_breakdown(record: dict, semantic: float) -> dict:
    """Full component breakdown — used by ranker for reasoning generation and debugging."""
    sem = max(0.0, min(1.0, float(semantic)))
    ts = title_score(record)
    ss = skills_score(record)
    cs = company_score(record)
    ls = location_score(record)
    bm = behavioral_multiplier(record)
    cons = consistency_score(record)
    base = sem * 0.35 + ts * 0.20 + ss * 0.20 + cs * 0.15 + ls * 0.10
    return {
        "final":                round(max(0.0, base * bm * cons), 6),
        "base":                 round(base, 4),
        "semantic":             round(sem, 4),
        "title":                round(ts, 4),
        "skills":               round(ss, 4),
        "company":              round(cs, 4),
        "location":             round(ls, 4),
        "behavioral_multiplier": bm,
        "consistency":          cons,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_inactive(last_active_str: Optional[str]) -> int:
    if not last_active_str:
        return 9999
    try:
        d = datetime.strptime(str(last_active_str)[:10], "%Y-%m-%d").date()
        return max(0, (_REF_DATE - d).days)
    except (ValueError, TypeError):
        return 9999
