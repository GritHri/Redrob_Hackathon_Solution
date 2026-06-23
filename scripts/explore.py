#!/usr/bin/env python3
"""
Dataset exploration toolkit for candidates.jsonl.

Usage examples:
  python scripts/explore.py --stats
  python scripts/explore.py --id CAND_0073832
  python scripts/explore.py --title "ML Engineer" --n 5
  python scripts/explore.py --filter-test
  python scripts/explore.py --field profile.country
  python scripts/explore.py --field profile.current_title --top 30
  python scripts/explore.py --company Wipro --n 3
  python scripts/explore.py --search "semantic search" --n 5
  python scripts/explore.py --sample 3
  python scripts/explore.py --filter-trace CAND_0073832
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator

DATA_PATH = Path(__file__).parent.parent / "data" / "candidates.jsonl"
SRC_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))


def iter_candidates(path: Path = DATA_PATH) -> Iterator[dict]:
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def get_nested(record: dict, dotpath: str):
    parts = dotpath.split(".")
    val = record
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return None
    return val


def fmt_candidate(r: dict, verbose: bool = False) -> str:
    p = r.get("profile", {})
    sig = r.get("redrob_signals", {})
    lines = [
        f"  ID:       {r['candidate_id']}",
        f"  Title:    {p.get('current_title')}",
        f"  Company:  {p.get('current_company')}  ({p.get('current_company_size')})",
        f"  Location: {p.get('location')}, {p.get('country')}",
        f"  YoE:      {p.get('years_of_experience')}",
        f"  Open:     {sig.get('open_to_work_flag')}  "
        f"Relocate: {sig.get('willing_to_relocate')}  "
        f"Response: {sig.get('recruiter_response_rate')}",
    ]
    if verbose:
        skills = [f"{s['name']}({s.get('proficiency','?')},{s.get('duration_months',0)}mo)"
                  for s in r.get("skills", [])[:12]]
        lines.append(f"  Skills:   {', '.join(skills)}")
        for job in r.get("career_history", [])[:3]:
            desc = (job.get("description") or "")[:120].replace("\n", " ")
            lines.append(f"  Job:      {job.get('title')} @ {job.get('company')} | {desc}")
    return "\n".join(lines)


def cmd_stats(args):
    country_c = Counter()
    title_c = Counter()
    willing_c = Counter()
    total = 0
    for r in iter_candidates():
        p = r.get("profile", {})
        country_c[p.get("country", "__MISSING__")] += 1
        title_c[p.get("current_title", "__MISSING__")] += 1
        willing_c[str(r.get("redrob_signals", {}).get("willing_to_relocate", "__MISSING__"))] += 1
        total += 1

    print(f"Total candidates: {total:,}")
    print()
    print("Country distribution:")
    for k, v in sorted(country_c.items(), key=lambda x: -x[1]):
        print(f"  {v:>7,}  {k}")
    print()
    print("willing_to_relocate values:")
    for k, v in sorted(willing_c.items(), key=lambda x: -x[1]):
        print(f"  {v:>7,}  {k}")
    print()
    print(f"Top 50 current_title:")
    for k, v in title_c.most_common(50):
        print(f"  {v:>7,}  {k}")


def cmd_filter_test(args):
    from filter import (
        NOISE_TITLES, CONSULTING_FIRMS, AI_KEYWORDS,
        CV_SPEECH_ROBOTICS_KW, NLP_IR_KW, RESEARCH_INSTITUTION_KW, PRODUCTION_KW,
    )

    def _ai_signal(r):
        st = " ".join(s.get("name", "").lower() for s in (r.get("skills") or []))
        ct = " ".join((j.get("description", "") or "").lower() for j in (r.get("career_history") or []))
        return any(kw in st + " " + ct for kw in AI_KEYWORDS)

    f1 = f2 = f3 = f4 = f5 = f6 = kept = 0
    for r in iter_candidates():
        p = r.get("profile", {})
        sig = r.get("redrob_signals", {})

        # F1: noise title (unconditional)
        if p.get("current_title") in NOISE_TITLES:
            f1 += 1; continue

        # F2: pure consulting + no AI
        companies = {job.get("company", "") for job in (r.get("career_history") or [])}
        if not (companies - CONSULTING_FIRMS) and not _ai_signal(r):
            f2 += 1; continue

        # F3: location
        if p.get("country") != "India" and not sig.get("willing_to_relocate", False):
            f3 += 1; continue

        # F4: YoE bounds
        yoe = p.get("years_of_experience") or 0
        if yoe < 2 or yoe > 18:
            f4 += 1; continue

        # F5: CV/Speech/Robotics only, no NLP/IR
        st = " ".join(s.get("name", "").lower() for s in (r.get("skills") or []))
        ct = " ".join((j.get("description", "") or "").lower() for j in (r.get("career_history") or []))
        combined = st + " " + ct
        if (any(kw in combined for kw in CV_SPEECH_ROBOTICS_KW) and
                not any(kw in combined for kw in NLP_IR_KW)):
            f5 += 1; continue

        # F6: pure researcher, no production
        career = r.get("career_history") or []
        if career:
            cos = [job.get("company", "").lower() for job in career]
            if (all(any(kw in co for kw in RESEARCH_INSTITUTION_KW) for co in cos) and
                    not any(kw in ct for kw in PRODUCTION_KW)):
                f6 += 1; continue

        kept += 1

    total = f1 + f2 + f3 + f4 + f5 + f6 + kept
    print(f"Total: {total:,}")
    print(f"Filter 1 (noise title):         -{f1:,}")
    print(f"Filter 2 (pure consulting):     -{f2:,}")
    print(f"Filter 3 (location):            -{f3:,}")
    print(f"Filter 4 (YoE <2 or >18):       -{f4:,}")
    print(f"Filter 5 (CV/Speech/Robot only):-{f5:,}")
    print(f"Filter 6 (pure researcher):     -{f6:,}")
    print(f"Kept:                            {kept:,}")


def cmd_id(args):
    for r in iter_candidates():
        if r["candidate_id"] == args.id:
            print(fmt_candidate(r, verbose=True))
            print()
            print("  Full redrob_signals:")
            for k, v in (r.get("redrob_signals") or {}).items():
                print(f"    {k}: {v}")
            return
    print(f"Not found: {args.id}")


def cmd_title(args):
    count = 0
    for r in iter_candidates():
        if r.get("profile", {}).get("current_title") == args.title:
            print(fmt_candidate(r, verbose=args.verbose))
            print()
            count += 1
            if count >= args.n:
                break
    print(f"Shown {count} candidates with title={args.title!r}")


def cmd_field(args):
    counter = Counter()
    for r in iter_candidates():
        val = get_nested(r, args.field)
        if isinstance(val, list):
            for item in val:
                counter[str(item)] += 1
        else:
            counter[str(val)] += 1
    print(f"Unique values for '{args.field}': {len(counter)}")
    for k, v in counter.most_common(args.top):
        print(f"  {v:>7,}  {k}")


def cmd_company(args):
    count = 0
    for r in iter_candidates():
        companies = {job.get("company", "") for job in r.get("career_history", [])}
        if args.company in companies:
            print(fmt_candidate(r, verbose=args.verbose))
            print()
            count += 1
            if count >= args.n:
                break
    print(f"Shown {count} candidates with {args.company!r} in career history")


def cmd_search(args):
    query = args.search.lower()
    count = 0
    for r in iter_candidates():
        text = json.dumps(r).lower()
        if query in text:
            print(fmt_candidate(r, verbose=args.verbose))
            print()
            count += 1
            if count >= args.n:
                break
    print(f"Shown {count} candidates matching {args.search!r}")


def cmd_sample(args):
    import random
    reservoir = []
    for i, r in enumerate(iter_candidates()):
        if i < args.n:
            reservoir.append(r)
        else:
            j = random.randint(0, i)
            if j < args.n:
                reservoir[j] = r
    for r in reservoir:
        print(fmt_candidate(r, verbose=True))
        print()


def cmd_filter_trace(args):
    """Show exactly why a specific candidate is kept or dropped."""
    from filter import NOISE_TITLES, CONSULTING_FIRMS, AI_KEYWORDS

    for r in iter_candidates():
        if r["candidate_id"] != args.filter_trace:
            continue
        p = r.get("profile", {})
        sig = r.get("redrob_signals", {})

        print(f"Tracing: {r['candidate_id']}")
        print(fmt_candidate(r, verbose=True))
        print()

        title = p.get("current_title", "")
        if title in NOISE_TITLES:
            print(f"[DROPPED] Filter 1 — title {title!r} in NOISE_TITLES")
            return
        print(f"[PASS] Filter 1 — title {title!r} not in NOISE_TITLES")

        companies = {job.get("company", "") for job in (r.get("career_history") or [])}
        consulting = companies & CONSULTING_FIRMS
        non_consulting = companies - CONSULTING_FIRMS
        print(f"  Companies in career: {companies}")
        print(f"  Consulting: {consulting}  |  Non-consulting: {non_consulting}")
        if non_consulting:
            print("[PASS] Filter 2 — has non-consulting company")
        else:
            skills_text = " ".join(s.get("name", "").lower() for s in (r.get("skills") or []))
            career_text = " ".join(
                (j.get("description", "") or "").lower() for j in (r.get("career_history") or [])
            )
            combined = skills_text + " " + career_text
            matched_kw = [kw for kw in AI_KEYWORDS if kw in combined]
            if matched_kw:
                print(f"[PASS] Filter 2 — pure consulting but AI keywords found: {matched_kw}")
            else:
                print(f"[DROPPED] Filter 2 — pure consulting, no AI keywords matched")
                print(f"  Skills text: {skills_text[:200]}")
                return

        country = p.get("country", "")
        willing = sig.get("willing_to_relocate", False)
        if country == "India":
            print(f"[PASS] Filter 3 — country=India")
        elif willing:
            print(f"[PASS] Filter 3 — outside India ({country}) but willing_to_relocate=True")
        else:
            print(f"[DROPPED] Filter 3 — country={country!r}, willing_to_relocate={willing}")
            return

        print("[KEPT] All filters passed")
        return
    print(f"Not found: {args.filter_trace}")


def main():
    parser = argparse.ArgumentParser(description="Explore candidates.jsonl")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("stats", help="Dataset-wide statistics")

    p = sub.add_parser("filter-test", help="Dry-run all 3 hard filters, show drop counts")

    p = sub.add_parser("id", help="Show one candidate by ID")
    p.add_argument("id")

    p = sub.add_parser("title", help="Show candidates with given current_title")
    p.add_argument("title")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--verbose", "-v", action="store_true")

    p = sub.add_parser("field", help="Show value distribution for any dotpath field")
    p.add_argument("field", help="e.g. profile.country or profile.current_title")
    p.add_argument("--top", type=int, default=30)

    p = sub.add_parser("company", help="Show candidates who worked at given company")
    p.add_argument("company")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--verbose", "-v", action="store_true")

    p = sub.add_parser("search", help="Full-text search across entire record JSON")
    p.add_argument("search")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--verbose", "-v", action="store_true")

    p = sub.add_parser("sample", help="Show N random candidates")
    p.add_argument("--n", type=int, default=3)

    p = sub.add_parser("filter-trace", help="Trace why a candidate is kept/dropped by filters")
    p.add_argument("filter_trace", metavar="ID")

    args = parser.parse_args()

    dispatch = {
        "stats": cmd_stats,
        "filter-test": cmd_filter_test,
        "id": cmd_id,
        "title": cmd_title,
        "field": cmd_field,
        "company": cmd_company,
        "search": cmd_search,
        "sample": cmd_sample,
        "filter-trace": cmd_filter_trace,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
