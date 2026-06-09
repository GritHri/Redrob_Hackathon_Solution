# Company Distribution in Career History (100,000 candidates)

Counts reflect appearances across all `career_history` entries, not unique candidates.

| # | Company | Appearances |
|---|---------|-------------|
| 0 | Infosys | 20,960 |
| 1 | Wipro | 20,904 |
| 2 | Initech | 20,844 |
| 3 | Pied Piper | 20,831 |
| 4 | Wayne Enterprises | 20,785 |
| 5 | Acme Corp | 20,768 |
| 6 | Stark Industries | 20,759 |
| 7 | Hooli | 20,757 |
| 8 | TCS | 20,741 |
| 9 | Globex Inc | 20,726 |
| 10 | Dunder Mifflin | 20,605 |
| 11 | Swiggy | 2,905 |
| 12 | Razorpay | 2,810 |
| 13 | CRED | 2,795 |
| 14 | Capgemini | 2,795 |
| 15 | Zomato | 2,788 |
| 16 | HCL | 2,783 |
| 17 | Flipkart | 2,782 |
| 18 | Mindtree | 2,776 |
| 19 | Cognizant | 2,756 |
| 20 | Accenture | 2,752 |
| 21 | Tech Mahindra | 2,726 |
| 22 | Mphasis | 2,717 |
| 23 | Meesho | 375 |
| 24 | InMobi | 371 |
| 25 | Nykaa | 367 |
| 26 | PolicyBazaar | 348 |
| 27 | Ola | 347 |
| 28 | BYJU'S | 346 |
| 29 | Zoho | 344 |
| 30 | Vedantu | 343 |
| 31 | Unacademy | 335 |
| 32 | Paytm | 335 |
| 33 | Freshworks | 331 |
| 34 | PharmEasy | 331 |
| 35 | PhonePe | 330 |
| 36 | upGrad | 328 |
| 37 | Dream11 | 322 |
| 38 | Genpact AI | 81 |
| 39 | Glance | 76 |
| 40 | Rephrase.ai | 70 |
| 41 | Aganitha | 69 |
| 42 | Niramai | 68 |
| 43 | Saarthi.ai | 65 |
| 44 | Sarvam AI | 65 |
| 45 | Krutrim | 64 |
| 46 | Mad Street Den | 63 |
| 47 | Observe.AI | 63 |
| 48 | Wysa | 62 |
| 49 | Verloop.io | 61 |
| 50 | Haptik | 61 |
| 51 | Yellow.ai | 59 |
| 52 | Locobuzz | 57 |
| 53 | Amazon | 13 |
| 54 | Google | 13 |
| 55 | Netflix | 13 |
| 56 | Salesforce | 12 |
| 57 | Uber | 11 |
| 58 | Meta | 11 |
| 59 | Microsoft | 10 |
| 60 | Adobe | 10 |
| 61 | Apple | 8 |
| 62 | LinkedIn | 7 |

## Company Tiers

| Tier | Companies | Scoring weight |
|------|-----------|----------------|
| Fictional (noise) | Initech, Pied Piper, Wayne Enterprises, Acme Corp, Stark Industries, Hooli, Globex Inc, Dunder Mifflin | Neutral — synthetic background data, ~20K appearances each |
| Consulting (hard filter if AI-signal-free) | Infosys, Wipro, TCS, Capgemini, HCL, Mindtree, Cognizant, Accenture, Tech Mahindra, Mphasis | Penalized in company_type score |
| India product scale-ups | Swiggy, Razorpay, CRED, Zomato, Flipkart, Meesho, PhonePe, Paytm, Ola, Nykaa, etc. | High weight |
| AI-native startups | Sarvam AI, Krutrim, Rephrase.ai, Observe.AI, Mad Street Den, Haptik, Yellow.ai, etc. | High weight |
| Global product | Amazon, Google, Netflix, Salesforce, Uber, Meta, Microsoft, Adobe, Apple, LinkedIn | High weight (rare in dataset) |
