# Hackathon Decoded — Redrob Intelligent Candidate Ranking Challenge
## Rules, Traps, and Inferred Strategy from All Docs

---

## 1. What You're Building

Rank the top 100 best-fit candidates from 100,000 profiles for one specific job:
**Senior AI Engineer, founding team, Pune/Noida India (hybrid).**

Output: one CSV — `candidate_id, rank, score, reasoning` — 100 rows, best fit first.

---

## 2. Scoring Formula (and What It Means Strategically)

```
Final = 0.50 × NDCG@10  +  0.30 × NDCG@50  +  0.15 × MAP  +  0.05 × P@10
```

- **Top 10 = 50% of your entire score.** Getting ranks 1-10 right matters more than ranks 11-100 combined.
- A system that nails ranks 1-10 but randomizes 11-100 still scores ~55%.
- Optimize for top 10 precision specifically, not average ranking quality.
- Tiebreak order: P@5 → P@10 → earlier submission timestamp.

---

## 3. The Dataset Reality

- 100,000 candidate profiles, but ~98,000 are instant noise (accountants, civil engineers, HR managers, graphic designers).
- In a 50-candidate sample: only 1 had an AI/ML title (Recommendation Systems Engineer at Swiggy).
- ~72% of candidates are India-based; rest scattered globally.
- Hard filter with pure rules kills 98K before any ML runs — saves all compute budget.

---

## 4. Hard Constraints (Non-Negotiable)

| Constraint | Limit | Applies to |
|-----------|-------|-----------|
| Runtime | ≤ 5 min wall-clock | **Ranking step only** |
| RAM | ≤ 16 GB | Ranking step only |
| Compute | CPU only, no GPU | Ranking step only |
| Network | Off — no API calls | Ranking step only |
| Disk | ≤ 5 GB intermediate state | Ranking step only |
| Submissions | 3 max, last valid counts | Entire competition |

**Key distinction:** Pre-compute (embeddings, indexes) has NO time limit. Only the step that produces the CSV is constrained. Document pre-compute separately in README.

---

## 5. JD Criteria — Hard Disqualifiers

Instant rank-bottom, no scoring needed:

```
1. current company is consulting (TCS/Infosys/Wipro/Accenture/Cognizant/Capgemini)
   AND career_history has no product company at all → DISQUALIFY

2. Title is wrong job family entirely (Accountant, Civil Engineer, HR Manager,
   Graphic Designer, Content Writer, Marketing Manager, etc.)
   AND career has no AI adjacency → DISQUALIFY

3. years_of_experience < 2 or > 18 → DISQUALIFY

4. Country != India AND willing_to_relocate == False
   AND preferred_work_mode == remote → DISQUALIFY (hybrid India role)

5. Primary expertise is Computer Vision / Speech / Robotics only,
   with no NLP/IR exposure → DISQUALIFY (JD explicitly lists this)

6. Pure researcher — academic labs, research-only roles,
   no production deployment evidence → DISQUALIFY (JD says tried twice, didn't work)
```

---

## 6. JD Criteria — Positive Flags

### Must-have signals (high weight)
- Production systems: career description contains `[deployed, shipped, production, real users, at scale, search, retrieval, ranking, recommendation]`
- Right tech: `[embeddings, vector, FAISS, Pinecone, Weaviate, Qdrant, sentence-transformers, BM25, Elasticsearch, hybrid search, FAISS, Milvus]`
- Evaluation mindset: `[NDCG, MRR, MAP, A/B test, offline eval, learning-to-rank, LambdaMART]`
- Product company background: Swiggy, Zomato, Flipkart, Razorpay, CRED, Meesho — or any Series A-D startup

### Nice-to-have (lower weight)
- LLM fine-tuning (LoRA, QLoRA, PEFT)
- Learning-to-rank models (XGBoost-based or neural)
- HR-tech, recruiting-tech, marketplace product background
- Open-source contributions in AI/ML space

### Experience sweet spot
- 5-9 years is the stated range, but JD says it's not a hard cutoff
- Disqualifying signals: 4+ years in "architecture/tech lead" without recent coding; LangChain tutorials with no pre-LLM ML experience

---

## 7. The Four Traps (Built Into Dataset)

### Trap 1: Keyword Stuffers
Skills section says `["RAG", "Pinecone", "LLMs"]` but title is Marketing Manager.
Naive skill-list embedding will love these. Career history must be checked, not just skills.

### Trap 2: Plain-Language Tier 1s
No AI keywords anywhere. Career says: *"built recommendation engine for 10M users at Flipkart"*.
Zero keyword match but clearly a fit. Career description embedding catches these — explicit keyword matching misses them entirely.

### Trap 3: Ghost Candidates
Perfect profile. `last_active_date` = 7 months ago. `recruiter_response_rate` = 0.05.
`open_to_work_flag = True` does NOT mean available — CAND_0000002 was OTW but inactive 208 days.
Behavioral multiplier must demote these.

### Trap 4: Honeypots (~80 candidates)
Subtle impossibilities baked into the profile:
- "8 years experience" at a company founded 3 years ago
- "Expert" proficiency in 10 skills with 0 months usage on each
- Honeypot rate > 10% in top 100 = **auto-disqualified** (Stage 3 filter)
- Detection: timeline arithmetic + skill duration cross-checks (no ML needed)

**The sample submission they included is an intentional anti-pattern** — HR Managers and Content Writers at rank 1-2 because they have 9 AI keywords in skills. Shows you exactly what failure looks like.

---

## 8. Pipeline Architecture

```
100K candidates
      │
      ▼
[Stage 1: Hard Filter]      ← PURE RULES. Binary. ~milliseconds.
  ~98K removed               Title / company / yoe / domain checks
      │
      ~2K remain
      ▼
[Stage 2: Semantic Score]   ← EMBEDDINGS live here (pre-computed offline)
  Career history text         Catch plain-language Tier 1s
  + explicit skill match      Rule-based for known tech stack
      │
      ▼
[Stage 3: Signal Scoring]   ← PURE ARITHMETIC
  Behavioral multiplier       availability × quality × market_demand
      │
      ▼
[Stage 4: Reasoning Gen]    ← STRUCTURED FACT EXTRACTION (see Section 10)
  Top 100 output CSV
```

---

## 9. Where to Use What Tech

| Task | Tool | Why |
|------|------|-----|
| Hard filter (title/company/yoe) | Pure rules | Binary decisions, no semantics needed |
| Skills matching (FAISS, Pinecone, etc.) | Explicit list membership check | You know exactly what skills you want; embedding "FAISS" as text can match wrong things |
| Career history fit | Sentence embeddings (all-MiniLM-L6-v2) | Catches plain-language Tier 1s that share no vocabulary with JD |
| Semantic JD match | Embeddings + cosine similarity | Same as above |
| ANN search across full 100K | FAISS — only if skipping hard filter | If hard filter cuts to ~2K, numpy cosine sim is milliseconds; FAISS unnecessary |
| Behavioral signals | Pure arithmetic/feature weights | Numerical data, no semantics |
| Honeypot detection | Timeline arithmetic | Cross-check company tenure vs company age |
| Reasoning text | Structured fact extraction | See Section 10 — no LLM needed or wanted |

**Recommended embedding model:** `sentence-transformers/all-MiniLM-L6-v2`
- 384 dimensions, ~80MB, fast on CPU
- Pre-compute all 100K embeddings offline (~20-40 min), save as `.npy`
- Ranking step just loads file + does cosine similarity (~10ms on filtered 2K candidates)

---

## 10. Behavioral Signals — 3 Functional Groups

### Group A: Availability (is this person reachable?)
| Signal | Good threshold | Red flag |
|--------|---------------|---------|
| `last_active_date` | < 30 days ago | > 90 days = ghost |
| `open_to_work_flag` | True = positive | True + inactive 6mo = still a ghost |
| `recruiter_response_rate` | > 0.5 = decent | < 0.2 = ghost |
| `avg_response_time_hours` | < 48h = engaged | > 168h (1 week) = passive |
| `notice_period_days` | ≤ 30 = great; 30-60 = ok | > 90 = friction |
| `interview_completion_rate` | > 0.6 = reliable | < 0.4 = red flag |
| `offer_acceptance_rate` | -1 = no history (neutral) | < 0.3 = flaky |
| `willing_to_relocate` | True if not already India | — |

**Availability composite:**
```python
recency = max(0, 1 - days_inactive / 180)   # decays to 0 at 6 months
raw = recency * 0.4 + response_rate * 0.35 + interview_completion * 0.25
availability = raw * (1.3 if open_to_work else 1.0) * notice_factor
```

### Group B: Quality Proxies (how good are they really?)
| Signal | Notes |
|--------|-------|
| `github_activity_score` | -1 = no GitHub linked (NEUTRAL, not zero) — don't penalize |
| `skill_assessment_scores` | Platform-verified test scores — gold signal when present |
| `profile_completeness_score` | Low = not serious |
| `endorsements_received` | Weak alone; combine with skill-level endorsements |
| `verified_email` / `verified_phone` | Both false = suspicious |

### Group C: Market Demand (what does the market think?)
| Signal | Insight |
|--------|---------|
| `profile_views_received_30d` | Recruiters already finding them (median: 46, good: 150+) |
| `search_appearance_30d` | Platform ranking in recruiter searches (median: 108, good: 500+) |
| `saved_by_recruiters_30d` | Bookmarked by recruiters (median: 5, good: 10+) |

Market demand signals are one of the cleanest quality proxies: a genuine AI candidate naturally appears in many AI-role recruiter searches. Independent validation.

---

## 11. Reasoning Column — What They Actually Want

### What's penalized (from spec)
- Empty reasoning
- All-identical reasoning strings
- Templated reasoning that just inserts the candidate's name
- Reasoning that mentions skills NOT in the candidate's profile (hallucination)
- Reasoning that contradicts the rank (glowing rank-95 reasoning = red flag)

### What they reward (from spec's Stage 4 checklist)
- Specific facts from the profile (yoe, title, named skills with durations, signal values)
- JD connection (maps to specific JD requirements, not generic praise)
- Honest concerns (acknowledge notice period, inactivity, gaps)
- No hallucination (every claim verifiable in the profile JSON)
- Variation (10 sampled rows must be substantively different)
- Rank consistency (tone must match rank)

### DO NOT use a local LLM for reasoning
CPU-only local LLM (Llama 3.2 1B Q4) = ~5-8 tokens/sec.
100 candidates × 50 tokens = 5,000 tokens = 600-1,000 seconds.
That's over budget even if pre-computed. More importantly: hallucination risk is real and is explicitly penalized.

### Use structured fact extraction instead

The spec's own example reasonings are fact extractions, not LLM output:
```
"Senior AI Engineer with 7 years building RAG systems at product companies;
 strong recent engagement and Bangalore-based."
→ {title} + {yoe} + {career_domain} + {company_type} + {behavioral} + {location}

"some concern on notice period (120 days) but otherwise strong fit."
→ HONEST_CONCERN: notice_period_days=120
```

Rich fact extraction = naturally different per candidate (different facts) + no hallucination risk + zero compute cost.

**What the spec penalizes:** `"John is a strong candidate for this role."` — same structure, swap name, zero info.

**What you're building:** `"6 yrs at Swiggy+Zomato shipping recommendation/ranking systems; FAISS expert (88mo), Pinecone expert; Hyderabad-based, willing to relocate; active 15d ago, 0.91 recruiter response rate, 60d notice."` — every token comes from a profile field.

---

## 12. Submission Format Rules (from Validator)

```csv
candidate_id,rank,score,reasoning
CAND_0042871,1,0.987,"1-2 sentence reasoning here"
```

- Exactly 100 data rows (not 99, not 101)
- Ranks 1-100 each appear exactly once
- Each `candidate_id` appears exactly once
- All candidate_ids must exist in `candidates.jsonl`
- `score` is non-increasing with rank (rank 1 ≥ rank 2 ≥ ... ≥ rank 100)
- Tie scores: break by `candidate_id` ascending
- File must be UTF-8, `.csv` extension, filename = your team participant ID

Run before every upload: `python validate_submission.py your_team_id.csv`

---

## 13. The 5-Stage Elimination Pipeline

| Stage | What Happens | What Gets You Eliminated |
|-------|-------------|--------------------------|
| 1. Format | Auto-validator runs | Any spec violation (wrong row count, bad IDs, non-monotonic scores) |
| 2. Scoring | NDCG computed on hidden ground truth | Score below cutoff for Stage 3 advancement |
| 3. Code Reproduction + Honeypot | Ranking step reproduced in Docker (5min, 16GB, CPU, no network). Honeypot rate computed. | Can't reproduce; honeypot rate > 10% in top 100; missing/fake code repo |
| 4. Manual Review | Reasoning quality. Methodology coherence. **Git history authenticity.** Code quality. | Failed reasoning checks; codebase is just LLM API calls; **flat git history with no iteration** |
| 5. Interview | 30-min video call defending architecture | Can't explain choices; contradicts submitted code; clearly didn't build it |

### Critical: Git History Authenticity (Stage 4)
They explicitly check: **"real iteration vs single dump."**
- Commit as you go during development
- Each commit should represent a real development step
- Do NOT build everything locally then dump it in one commit before deadline
- A flat history (1-3 commits for the whole project) is a Stage 4 red flag

---

## 14. Submission Checklist

Before submitting:
- [ ] `validate_submission.py` passes with no errors
- [ ] Top 10 have no obvious wrong-domain candidates (no accountants, HR managers)
- [ ] Top 10 have no candidates inactive > 90 days
- [ ] No honeypots in top 100 (check timeline: tenure months vs company founding date)
- [ ] Reasoning is specific per candidate, not generic, not templated name-swaps
- [ ] Reasoning tone matches rank (rank 5 = strong, rank 95 = hedged)
- [ ] Reasoning contains no skills/employers not in the actual profile
- [ ] Code repo has real iterative git history
- [ ] Single command to reproduce CSV is documented in README
- [ ] `submission_metadata_template.yaml` filled out
- [ ] Sandbox/demo link working (HuggingFace Spaces / Streamlit / Colab / Replit)

---

## 15. Score Maximization Strategy

1. **Top 10 is everything.** 50% of score lives in ranks 1-10. Every wrong pick at rank 1-10 hurts more than 5 wrong picks at ranks 50-60. Manually audit top 10 before submitting.

2. **Career history text > skill list.** Embed career descriptions, not skills. Keyword-heavy skill lists are how stuffers game the system. The JD itself says: a candidate without "RAG" or "Pinecone" in their skills but with "built recommendation engine for 10M users" in career history is a better pick.

3. **Availability multiplier is a significant differentiator.** Among candidates who are genuine skill fits, behavioral signals separate hireable from unhireable. A ghost with perfect skills ranks below an 80%-fit candidate who is active and responsive.

4. **Honeypot avoidance is pass/fail.** >10% honeypots in top 100 = disqualified. Cross-check career timelines. Expert at a skill with 0 months usage = red flag.

5. **Honest reasoning wins Stage 4.** Concern: 90-day notice is better than ignoring it. They explicitly reward reasoning that acknowledges gaps.

6. **3 submissions max — no feedback between submissions.** Validate heavily locally before each upload. Don't waste submissions on format fixes.
