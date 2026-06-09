# Hard Filters

Filters applied before scoring. Binary — candidates either pass or are dropped entirely.

| # | Filter | Rule | Dropped |
|---|--------|------|---------|
| 1 | Non-technical titles | `current_title` exactly matches 12 noise job families (HR Manager, Accountant, Civil Engineer, etc.) | ~68,821 |
| 2 | Pure consulting, no AI | All `career_history` companies are consulting firms (TCS/Infosys/Wipro/Accenture/Capgemini/Cognizant/HCL/Mindtree/Mphasis/Tech Mahindra) AND no AI/ML keywords in skills or career descriptions | ~2,025 |
| 3 | Outside India, not relocating | `country != "India"` AND `willing_to_relocate == False` — JD explicitly states no visa sponsorship | ~4,938 |

**After all 3 filters: ~24,216 remain from 100,000.**

## Not hard filters (score penalties instead)
- Non-Tier-1 India city + not willing to relocate → moderate score penalty
- Outside India + willing to relocate → strong score penalty (visa friction)
- Pure consulting career with AI exposure → kept, penalized in company_type score
- Behavioral signals (inactive, low response rate) → multiplier [0.5–1.2]
- Honeypot profiles → consistency penalty, not rejection
