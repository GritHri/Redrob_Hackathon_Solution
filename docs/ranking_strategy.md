# Candidate Ranking Strategy — Analysis & Filter Documentation

**Role:** Senior AI Engineer — Founding Team, Redrob AI  
**Scoring:** NDCG@10 (50%), NDCG@50 (30%), MAP (15%), P@10 (5%)  
**Implication:** Top 10 drive half the score. Top 50 drive 80%. Optimize for precision at top, recall through rank 50.

---

## 1. Core Thesis

The JD is NOT asking for "most AI keywords." It is asking for someone who has **shipped retrieval/ranking/recommendation systems to real users at product companies**.

> *"The right answer involves reasoning about the gap between what the JD says and what the JD means. A Tier 5 candidate may not use the words 'RAG' or 'Pinecone' in their profile, but if their career history shows they built a recommendation system at a product company, they're a fit."*  
> — JD, "Final note for hackathon participants"

> *"We'd rather see 10 great matches than 1000 maybes."*  
> — JD, "How to read between the lines"

---

## 2. Hard Filters (Eliminate Before Scoring)

These filters reduce the 100K pool to a tractable search space without risking loss of true positives.

---

### 2.1 Non-Technical Job Titles — REJECT ALL

**Filter:** Exclude candidates whose `current_title` is one of:
- Business Analyst, HR Manager, Mechanical Engineer, Accountant, Project Manager, Customer Support, Operations Manager, Content Writer, Sales Executive, Civil Engineer, Graphic Designer, Marketing Manager

**Count eliminated:** ~63,000 candidates

**Why:**  
The JD explicitly names this as a trap:

> *"A candidate who has all the AI keywords listed as skills but whose title is 'Marketing Manager' is not a fit, no matter how perfect their skill list looks."*  
> — JD, "Final note for hackathon participants"

No career description from a Civil Engineer will contain "shipped a ranking system." Skill fields on these profiles are noise — synthetic data places AI keywords on irrelevant profiles specifically to test whether the ranker ignores them. These are the honeypot-adjacent records.

**Risk of over-filtering:** Zero. No reasonable interpretation of "Senior AI Engineer" at a Series A product company maps to any of these titles.

---

### 2.2 Outside India, Not Willing to Relocate — REJECT

**Filter:** Exclude candidates where `country != "India"` AND `willing_to_relocate == False`

**Why:**

> *"Outside India: case-by-case, but we don't sponsor work visas."*  
> — JD, "On location, comp, and logistics"

A candidate based in Canada, UK, USA, etc. who is not willing to relocate cannot be hired. Even willing-to-relocate candidates outside India face visa sponsorship issues, so they should be ranked very low (not rejected outright — could be NRI returning — but not prioritized).

**Nuance:** `country == "India"` but non-Tier-1 city with `willing_to_relocate == False` — do NOT reject. Penalize slightly but keep (JD is flexible on exact location within India).

---

### 2.3 Honeypot Profiles — REJECT

**Filter:** Profiles with logically impossible data:
- `years_of_experience` at a single company > that company's plausible age (e.g., 8 yrs at a company founded 2020)
- A skill with `proficiency == "expert"` and `duration_months == 0`
- Multiple such contradictions in same profile

**Why:**

> *"~80 candidates have subtly impossible profiles (e.g., 8 yrs at a 3-year-old company; expert proficiency with 0 months duration). Ground truth forces these to relevance tier 0. Honeypot rate >10% in top 100 → Stage 3 disqualification."*  
> — CLAUDE.md, "Honeypots"

**Implementation note:** A well-built ranker avoids honeypots naturally through profile consistency checks. Do not hard-skip — score them, but consistency penalty should drop them out of top 100 automatically.

---

## 3. Primary Scoring Signals

These signals directly measure fit for the role. Stack-ranked by importance.

---

### 3.1 Career Descriptions — Highest Weight Signal

**What to look for:** Text in `career_history[*].description` containing evidence of:
- Built/shipped ranking, search, recommendation, retrieval systems
- Worked with: embedding models, vector indexes, hybrid retrieval, re-ranking
- Ran A/B tests on ranking quality, measured NDCG/MRR/MAP
- Evolved a system from BM25/rule-based to ML-based
- Deployed to real users at meaningful scale

**Why this is the top signal:**

> *"The right answer involves reasoning about the gap between what the JD says and what the JD means."*  
> — JD, "Final note for hackathon participants"

> *"Has shipped at least one end-to-end ranking, search, or recommendation system to real users at meaningful scale."*  
> — JD, "How to read between the lines"

The JD is explicit that keyword matching on the skills array is a trap. Career descriptions reveal what was actually built vs. what was self-reported. A "Recommendation Systems Engineer" at Swiggy whose description says "migrated our keyword-search product to embedding-based retrieval" is worth 10x a "ML Engineer" whose description says "assisted in data preprocessing."

**Negative signal in descriptions:** Phrases like:
- "self-learner level", "online courses", "played with the OpenAI API", "built a small RAG side project"
- "maintained pipelines", "assisted the data science team", "supported model deployment"

These indicate adjacency, not ownership.

---

### 3.2 Job Title — High Weight

**Tier 1 titles (strongest signal):**
- Recommendation Systems Engineer, Search Engineer, NLP Engineer, Applied ML Engineer
- AI Engineer, ML Engineer, Machine Learning Engineer, Senior ML Engineer
- Senior AI Engineer, Lead AI Engineer, Staff ML Engineer, Senior Applied Scientist

**Tier 2 titles (good signal):**
- Data Scientist (applied, not research), AI Specialist, AI Research Engineer
- Senior Data Scientist, Senior Software Engineer (ML)

**Tier 3 titles (partial signal — check career descriptions carefully):**
- Software Engineer, Backend Engineer, Senior Software Engineer
- Data Engineer, Analytics Engineer (if career descriptions show ML/search work)

**Why titles matter:**

> *"The 'ideal candidate' we're imagining is roughly: 6–8 years total experience, of which 4–5 are in applied ML/AI roles at product companies."*  
> — JD, "How to read between the lines"

Title signals the candidate's primary identity. A Recommendation Systems Engineer has self-identified their specialty. A Software Engineer may have done ML work but it is not their primary frame.

**Dataset reality check:** Only ~820 candidates hold ML/AI-specific titles in the 100K pool. That is already 8x the 100 slots needed. The entire top 100 can be filled from this pool if quality holds.

---

### 3.3 Skills Array — Medium Weight (with caveats)

**High-value skills (core must-haves per JD):**

| Skill category | Specific signals |
|---------------|-----------------|
| Embedding retrieval | Sentence Transformers, BGE, E5, OpenAI Embeddings, text-embedding-ada |
| Vector search | FAISS, Pinecone, Qdrant, Weaviate, Milvus, Chroma |
| Hybrid search | Elasticsearch, OpenSearch (with embedding context) |
| Ranking evaluation | NDCG, MRR, MAP, Information Retrieval, Learning to Rank |
| LLM systems | Hugging Face Transformers, LangChain (only if paired with pre-LLM experience) |
| Fine-tuning | LoRA, QLoRA, PEFT (nice-to-have per JD) |

**Why skills matter (with caveat):**

> *"Things you absolutely need: Production experience with embeddings-based retrieval systems... Production experience with vector databases or hybrid search infrastructure... Hands-on experience designing evaluation frameworks for ranking systems — NDCG, MRR, MAP."*  
> — JD, "The skills inventory"

**The caveat — keyword trap:**

> *"The 'right answer' to this JD is not 'find candidates whose skills section contains the most AI keywords.' That's a trap we've explicitly built into the dataset."*  
> — JD, "Final note for hackathon participants"

Skills should be **corroborated by career descriptions**. A skill with high `duration_months` and `endorsements` from a relevant prior role carries weight. The same skill self-listed with 0 endorsements and 1 month duration on a non-ML career profile is noise.

**Skill proficiency interpretation:**
- `expert` + long `duration_months` + high `endorsements` = strong signal
- `expert` + `duration_months == 0` = honeypot flag
- `beginner` + short duration = self-reported aspiration, not production experience

---

### 3.4 Years of Experience — Medium Weight

**Target range:** 5–9 years total, with 3–5 years specifically in applied ML/AI

**Scoring approach:**
- 5–9 yrs: full score
- 4 yrs or 10–11 yrs: mild penalty, other signals compensate
- < 4 yrs or > 12 yrs: significant penalty (not reject)

**Why flexible, not hard filter:**

> *"This is a range, not a requirement. Some people hit 'senior engineer' judgment at 4 years; some never hit it after 15. We've used 5–9 because it's roughly where people we've hired into this kind of role have landed, but we'll seriously consider candidates outside the band if other signals are strong."*  
> — JD, "What we mean by '5–9 years'"

**Hard disqualifiers on experience:**

> *"If you've spent your career in pure research environments (academic labs, research-only roles) without any production deployment — we will not move forward."*  
> — JD, "What we mean by '5–9 years'"

> *"If your 'AI experience' consists primarily of recent (under 12 months) projects using LangChain to call OpenAI — we will probably not move forward, unless you can demonstrate substantial pre-LLM-era ML production experience."*  
> — JD, "What we mean by '5–9 years'"

> *"If you are a senior engineer who hasn't written production code in the last 18 months because you've moved into 'architecture' or 'tech lead' roles — we will probably not move forward. This role writes code."*  
> — JD, "What we mean by '5–9 years'"

---

### 3.5 Company Type — High Weight

**Rank order:**
1. India product startups / scale-ups (Swiggy, Zomato, Razorpay, Meesho, PhonePe, Dunzo, etc.)
2. Global product companies (Uber, Google, Meta, Amazon — India offices)
3. Mid-size product companies (SaaS, fintech, e-commerce, marketplace)
4. Mixed: product company + consulting stints (prior product ML work is what counts)
5. Consulting firms with ML project work (HCL, Mindtree — newer consulting with product exposure)
6. Pure legacy consulting (TCS, Infosys, Wipro entire career)

**Why company type matters:**

> *"The 'ideal candidate' we're imagining is roughly: 6–8 years total experience, of which 4–5 are in applied ML/AI roles at **product companies** (not pure services)."*  
> — JD, "How to read between the lines"

> *"Things we explicitly do NOT want: People who have only worked at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc.) in their entire career."*  
> — JD, "Things we explicitly do NOT want"

**Nuance:** "Currently at one of these companies but have prior product-company experience, that's fine." — JD. Current employer = consulting giant is not disqualifying if prior career shows product ML work.

---

### 3.6 Location — Medium Weight

| Location | Score modifier |
|----------|---------------|
| Pune or Noida | +boost (preferred cities) |
| Hyderabad, Mumbai, Bangalore, Delhi NCR | Neutral (Tier-1 India, JD explicitly welcomes) |
| Other India city, `willing_to_relocate == True` | Mild penalty |
| Other India city, `willing_to_relocate == False` | Moderate penalty |
| Outside India, `willing_to_relocate == True` | Strong penalty (visa issue) |
| Outside India, `willing_to_relocate == False` | Reject or near-zero |

**Supporting quotes:**

> *"Location: Pune/Noida-preferred but flexible. Candidates in Hyderabad, Pune, Mumbai, Delhi NCR welcome to apply."*  
> — JD, "On location, comp, and logistics"

> *"Outside India: case-by-case, but we don't sponsor work visas."*  
> — JD, "On location, comp, and logistics"

> *"Open to relocation candidates from Tier-1 Indian cities."*  
> — JD, header

---

## 4. Behavioral Signals — Multiplier Layer

Apply AFTER computing skill/career score. Behavioral signals indicate whether a candidate is **actually hirable**, not just relevant.

> *"These behavioral signals are often more predictive of whether a candidate can actually be hired than their static profile. A perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% response rate is, for hiring purposes, not actually available."*  
> — redrob_signals_doc.docx

> *"Your ranking system should also weigh behavioral signals — a perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% recruiter response rate is, for hiring purposes, not actually available. Down-weight them appropriately."*  
> — JD, "Final note for hackathon participants"

**Reference date: 2026-06-10**

| Signal | Strong (+) | Neutral | Penalize (–) |
|--------|-----------|---------|-------------|
| `last_active_date` | ≥ 2026-03-10 (within 90d) | 2025-12-10 – 2026-03-10 | < 2025-12-10 (>6 months stale) |
| `recruiter_response_rate` | ≥ 0.6 | 0.3 – 0.6 | < 0.2 |
| `open_to_work_flag` | True | — | False (alone not reject) |
| `applications_submitted_30d` | ≥ 2 | 1 | 0 |
| `interview_completion_rate` | ≥ 0.7 | 0.5 – 0.7 | < 0.3 |
| `github_activity_score` | ≥ 30 | 1 – 30 | -1 (no GitHub = no bonus, not penalized) |
| `notice_period_days` | ≤ 30 | 31 – 60 | ≥ 90 |

**Implementation:** Compute a `behavioral_multiplier` in range [0.5, 1.2]. Multiply final skill score by it. Do not let behavioral signals override a strong skill match — they tune ranking among similarly-skilled candidates.

---

## 5. Soft Disqualifiers (Penalize, Don't Reject)

These patterns push candidates down the ranking but don't eliminate:

### 5.1 Title-Chaser Pattern
- Job history shows: 3+ companies in 4.5 years, each with a title upgrade
- Implies optimizing for promotions, not depth

> *"Title-chasers. If your career trajectory shows you optimizing for 'Senior' → 'Staff' → 'Principal' titles by switching companies every 1.5 years, we're not a fit."*  
> — JD, "Things we explicitly do NOT want"

### 5.2 Framework Enthusiast Pattern
- Skills are predominantly: LangChain, LlamaIndex, AutoGPT, LangGraph
- Career descriptions mention: "built demo", "used [framework] to call OpenAI API", "tutorial"
- No evidence of pre-LLM ML production systems

> *"Framework enthusiasts. If your GitHub is full of LangChain tutorials and your blog posts are 'How I used [hot framework] to build [demo]' — that's fine but it's not what we need."*  
> — JD, "Things we explicitly do NOT want"

### 5.3 CV/Speech/Robotics Specialist Without NLP/IR
- Skills dominated by: Image Classification, YOLO, OpenCV, TTS, Speech Recognition, Robotics
- No retrieval, ranking, or NLP signal in career

> *"People whose primary expertise is computer vision, speech, or robotics without significant NLP/IR exposure. We respect your work but you'd be re-learning fundamentals here."*  
> — JD, "Things we explicitly do NOT want"

### 5.4 Closed-Source Only Career
- Entire career at enterprises with no external validation: no GitHub, no papers, no open-source, no talks

> *"People whose work has been entirely on closed-source proprietary systems for 5+ years without external validation (papers, talks, open-source). We need to see how you think, not just trust that you can think."*  
> — JD, "Things we explicitly do NOT want"

---

## 6. Candidate Tiers

### Tier A — Top 10 (All criteria met)
- Title: ML/AI/Search/Recommendation/NLP Engineer variant
- Career at product companies, descriptions show shipped retrieval/ranking/search
- Core skills present with meaningful duration + endorsements
- India location (Tier-1 city or willing to relocate)
- Behavioral: recently active, high response rate, short notice

**Archetype:** Recommendation Systems Engineer, 6yr, Hyderabad, worked at Swiggy/Zomato/Uber, skills include FAISS (expert, 35mo), Pinecone (expert, 88mo), Information Retrieval (expert, 84mo), Sentence Transformers (expert, 69mo), open=True, response\_rate=0.91, last\_active within 30 days.

### Tier B — Ranks 11–50
- Strong on most Tier A criteria, one dimension weaker
- Examples: right skills + India non-tier-1 city but relocating; right skills + 10yr experience; product company ML with consulting stint mixed in; data scientist who built ranking (not "ML Engineer" title but actual work)

### Tier C — Ranks 51–100 (High-recall safety net)
- Adjacent technical roles with ML exposure: Data Engineers at product companies who touched embedding pipelines; Backend Engineers who built search APIs; strong NLP engineers with some production stints
- Strong skills but poor behavioral signals (inactive, low response rate)
- India location, right skills, but experience outside 4–12yr range

### Reject (Never rank)
- Non-tech titles (row 0–11 from title distribution table)
- Outside India, not willing to relocate
- Confirmed honeypot profiles

---

## 7. Search Space Reduction

| Category | Title examples | Pool size | Priority |
|----------|---------------|-----------|---------|
| ML/AI-specific | ML Engineer → Lead AI Engineer | ~820 | **Primary** |
| Data/Analytics adjacent | Data Scientist, Analytics Eng, Data Engineer, Backend Eng | ~3,600 | Secondary (ranks 51–100) |
| Generic tech | Software Engineer, Full Stack, Cloud, Java, DevOps, QA | ~23,000 | Tertiary (only if padding) |
| **Non-tech** | **Business Analyst → Marketing Manager** | **~63,000** | **Skip entirely** |

The ~820 ML/AI-titled candidates alone provide 8x the needed quota. The entire top-100 is likely sourced from the primary + secondary pools only.

---

## 8. Scoring Formula (Conceptual)

```
final_score = (
    career_description_score   * 0.35   # did they actually build retrieval/ranking?
  + title_tier_score           * 0.20   # ML-specific title vs generic
  + skills_relevance_score     * 0.20   # core skill presence + duration + endorsements
  + company_type_score         * 0.15   # product company vs consulting
  + location_score             * 0.10   # India tier-1, relocation
) * behavioral_multiplier               # range [0.5, 1.2]
  * consistency_score                   # honeypot penalty [0.0, 1.0]
```

**Note:** Behavioral multiplier is a modifier, not a primary signal. Skills determine relevance; behavior determines availability.
