# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Challenge Overview

**Redrob Hackathon — Intelligent Candidate Discovery & Ranking**

Task: rank the top 100 candidates from `candidates.jsonl` (100,000 records) for the released job description. Output a CSV. Scored against hidden ground truth using NDCG@10 (50%), NDCG@50 (30%), MAP (15%), P@10 (5%).

**Job description summary:** Senior AI Engineer, 5–9 years, Redrob AI (Series A), Pune/Noida hybrid. Needs: embeddings, retrieval, ranking, LLMs, fine-tuning. Strong preference for "shipper" over "researcher" archetype. Current stack is BM25 + rule-based. Target skills: Python, ML systems, vector search, RAG, evaluation infra.

## Repository Structure

```
data/                          # All dataset files
  candidates.jsonl             # Full dataset — 100,000 candidate records (one JSON per line)
  sample_candidates.json       # 50 candidates — use for dev/testing
  candidate_schema.json        # Full schema of all candidate fields

docs/                          # Challenge documentation (read-only reference)
  job_description.docx         # The target JD
  redrob_signals_doc.docx      # Documentation for redrob_signals fields
  submission_spec.docx         # Submission rules, scoring, stages
  README.docx                  # Challenge overview

scripts/                       # Tooling
  validate_submission.py       # Validates output CSV format

submission/                    # Submission artifacts
  sample_submission.csv        # Format reference only — not a quality baseline
  submission_metadata_template.yaml  # Copy to submission_metadata.yaml and fill in
```

## Validation

```bash
python scripts/validate_submission.py <team_id>.csv
```

Catches: wrong row count, duplicate IDs/ranks, non-monotone scores, bad ID format, wrong tie-break order.

## Output Format

File: `<team_id>.csv`, UTF-8, exactly 100 data rows + header.

```
candidate_id,rank,score,reasoning
CAND_0042871,1,0.987,"Senior AI Engineer with 7 yrs; strong RAG + retrieval skills; Bangalore-based."
```

Rules:
- `rank` is int 1–100, each used exactly once
- `score` is float, non-increasing as rank increases
- Ties: break by `candidate_id` ascending
- `reasoning`: 1–2 sentences, fact-specific (references actual profile data), connects to JD. Blank reasoning is penalized at Stage 4 manual review.

## Candidate Data Fields

**profile**: `years_of_experience`, `current_title`, `headline`, `summary`, `location`, `country`, `current_company_size`, `current_industry`

**skills**: array of `{name, proficiency (beginner/intermediate/advanced/expert), endorsements, duration_months}`

**career_history**: array of `{company, title, start_date, end_date, duration_months, is_current, industry, company_size, description}`

**education**: `{institution, degree, field_of_study, start_year, end_year, grade, tier (tier_1–tier_4/unknown)}`

**redrob_signals** (key ones):
- `open_to_work_flag` — boolean
- `recruiter_response_rate` — 0.0–1.0
- `interview_completion_rate` — 0.0–1.0
- `github_activity_score` — 0–100, or -1 if no GitHub
- `profile_completeness_score` — 0–100
- `notice_period_days` — 0–180
- `expected_salary_range_inr_lpa` — `{min, max}`
- `preferred_work_mode` — remote/hybrid/onsite/flexible
- `willing_to_relocate` — boolean
- `skill_assessment_scores` — dict of skill→score (0–100)

## Compute Constraints (Hard)

Ranking step must satisfy all of these (enforced in Docker at Stage 3):

| Constraint | Limit |
|-----------|-------|
| Runtime | ≤ 5 minutes wall-clock |
| RAM | ≤ 16 GB |
| Compute | CPU only — no GPU |
| Network | Off — no API calls (no OpenAI, Anthropic, etc.) |
| Disk | ≤ 5 GB intermediate state |

Pre-computation (embeddings, indexes, model weights) can exceed 5 min — only the final ranking step must fit. Document this clearly in README.

## Honeypots

~80 candidates have subtly impossible profiles (e.g., 8 yrs at a 3-year-old company; expert proficiency with 0 months duration). Ground truth forces these to relevance tier 0. Honeypot rate >10% in top 100 → Stage 3 disqualification. A well-built ranker avoids them naturally through profile consistency checks.

## Submission Stages

1. **Format validation** — auto-run on upload
2. **Scoring** — once, after close, hidden leaderboard
3. **Code reproduction** — top-N: full repo + Docker sandbox, must reproduce within compute limits
4. **Manual review** — reasoning quality, git history authenticity, code quality
5. **Defend-your-work interview** — top finalists only

**3 submission cap total.** No live leaderboard or per-submission feedback.

## What to Submit

1. `<team_id>.csv` — the ranking
2. `submission_metadata.yaml` — filled from template
3. GitHub repo with: source code, `requirements.txt`, `submission_metadata.yaml`, reproduce command in README, pre-computed artifacts or script to generate them
4. Sandbox link (HuggingFace Spaces, Streamlit Cloud, Colab, etc.) — must rank ≤100 candidates end-to-end on CPU

## Source of Truth Hierarchy

**When any conflict exists between docs, use this order:**

1. `docs/hackathon_context/` — **authoritative**. These are the actual hackathon-issued files (JD, submission spec, signals doc, README). Rules, constraints, and JD criteria come only from here.
2. `docs/analyzed_data/` — **authoritative for dataset facts**. Title distribution, company distribution, and counts come from actual scans of `candidates.jsonl`.
3. `docs/HACKATHON_DECODED.md`, `docs/ranking_strategy.md`, `docs/hard_filters.md` — **interpretation and design docs, not source of truth**. These are working analysis documents — open to revision. Do not treat claims in these files as settled facts. Verify any claim against source 1 or 2 before acting on it.

Scoring weights, behavioral multiplier ranges, and model choices in the interpretation docs are **design decisions**, not sourced from hackathon rules.

## Architecture Guidance

Given the 5-min CPU constraint on 100K candidates:

- **Don't**: call any LLM API per candidate during ranking (impossible within budget)
- **Do**: precompute embeddings/features offline, then run a fast scoring function at rank time
- Effective approach: rule-based scoring with explicit feature weights (skills match, experience, title alignment, location, engagement signals) runs in seconds
- Hybrid: precomputed TF-IDF or sentence-transformer embeddings + fast dot-product ranking + redrob_signals multiplier
- The JD emphasizes: ML/AI skills (embeddings, retrieval, LLMs, RAG, fine-tuning), 5–9 yrs, India location (Pune/Noida preferred but open to Tier-1 relocation), product engineering mindset
