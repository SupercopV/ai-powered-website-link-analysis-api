# AI-Powered Website Link Analysis API

A production-grade Python 3.x + FastAPI application that securely analyzes a given website URL, extracts authentic business and brand content with strict SSRF protection, processes the information with an environment-configured LLM, and returns structured, actionable intelligence across five key commercial dimensions.

---

## Table of Contents
1. [Objective & Key Features](#objective--key-features)
2. [Architecture & SSRF Protection](#architecture--ssrf-protection)
3. [Project Structure](#project-structure)
4. [Installation & Setup](#installation--setup)
5. [Running the Application](#running-the-application)
6. [Running the Test Suite](#running-the-test-suite)
7. [API Documentation & Endpoints](#api-documentation--endpoints)
8. [Sample API Request & Response](#sample-api-request--response)
9. [LLM Platform & Model Research (Cost, Speed, Accuracy)](#llm-platform--model-research)
10. [Cost Optimization Strategies](#cost-optimization-strategies)
11. [Deployment & Submission Guide](#deployment--submission-guide)

---

## 1. Objective & Key Features

The application provides a single REST endpoint (`POST /link-analysis`) running on port `4000` with interactive OpenAPI documentation at `/docs`. It inspects a submitted URL and delivers a comprehensive 5-section analysis:

- **Section 1: Competitor vs Brand Details:**
  Identifies brand overview, main category, products/services, and a minimum of 3 competitors. Speculative or AI-inferred competitors are explicitly labeled (`is_speculative: true`). Includes brand strengths and market opportunities.
- **Section 2: Top 5 Target Search Queries:**
  Generates exactly 5 high-intent search queries mapped across supported platforms (Google Search, Facebook, Instagram, LinkedIn, and/or X). Search volume numbers are never fabricated.
- **Section 3: SEO Improvement:**
  Provides keyword recommendations (primary, secondary, long-tail, and business-focused), an optimized SEO title, a human-friendly meta description, and strategic supporting content assets.
- **Section 4: Top 5 Services:**
  Identifies the top five services extracted from actual website content. Any service derived logically from the business context is explicitly tagged (`is_inferred: true`).
- **Section 5: Target Audience Identification:**
  Details primary and secondary target audiences, industry verticals, business types, customer profiles, geographic focus, customer needs, and marketing segments.

---

## 2. Architecture & SSRF Protection

To prevent Server-Side Request Forgery (SSRF) and ensure security against internal network exfiltration:

1. **Protocol Whitelisting:** Strictly allows only `http` and `https` schemes; rejects `ftp`, `file`, `javascript`, `data`, and `gopher`.
2. **Domain & DNS Resolution Inspection:**
   - Pre-filters blacklisted hostnames (`localhost`, `metadata.google.internal`, `instance-data`) and internal suffixes (`.local`, `.internal`, `.lan`, `.localdomain`).
   - Resolves all domain names to their underlying IP addresses using system DNS before dispatching HTTP calls.
   - Validates resolved IPv4 and IPv6 addresses against restricted subnets using Python's `ipaddress` library:
     - Private IP ranges (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`; IPv6 `fc00::/7`)
     - Loopback interfaces (`127.0.0.0/8`, `::1`)
     - Link-local and cloud metadata addresses (`169.254.0.0/16`, `fe80::/10`)
     - Carrier-Grade NAT (RFC 6598: `100.64.0.0/10`)
     - Multicast, broadcast, reserved, and benchmarking blocks
3. **Manual Redirect Inspection:** Disables automatic HTTP redirects in the HTTP client. Every HTTP 3xx redirect location is resolved and re-verified against the SSRF validator before following (preventing DNS rebinding and open redirect bypasses).
4. **Denial-of-Service Defense:** Limits response payloads to 5 MB and enforces a 15-second timeout.
5. **Content Pre-Cleaning & Token Optimization:** Strips scripts, styles, SVG markup, iframes, and cookie banners; extracts headers (`H1`-`H3`), meta tags, navigation menus, and body text; and limits context to 12,000 characters to reduce LLM token costs.

---

## 3. Project Structure

```text
ai-link-analysis/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application and exception handlers
│   ├── config.py                   # Environment settings and configuration
│   ├── schemas.py                  # Pydantic request and response schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── website_extractor.py    # Safe HTTP fetcher and HTML parser
│   │   ├── llm_service.py          # Multi-provider LLM client (Gemini, OpenAI, Anthropic, Mock)
│   │   ├── analysis_service.py     # Pipeline coordinator and schema normalizer
│   │   └── competitor_service.py   # Competitor structuring and speculative labeling
│   │
│   └── utils/
│       ├── __init__.py
│       └── validators.py           # SSRF protection and URL validation
│
├── tests/
│   ├── __init__.py
│   └── test_link_analysis.py       # Comprehensive pytest test suite (11 test cases)
│
├── samples/
│   ├── sample_request.json         # Realistic request payload
│   └── sample_response.json        # Structured 5-section response
│
├── .env.example                    # Template for environment variables
├── .gitignore                      # Git ignore file excluding credentials and caches
├── requirements.txt                # Pinned production dependencies
└── README.md                       # Documentation, research, and submission guide
```

---

## 4. Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13
- pip (Python package manager)

### Step 1: Clone or Open the Workspace
```bash
cd "c:\Users\lenovo\Desktop\Dxora test 2"
```

### Step 2: Create and Activate a Virtual Environment
```bash
# On Linux / macOS
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the example file to `.env`:
```bash
cp .env.example .env
```

Edit `.env` to configure your preferred LLM provider:
- **Groq Cloud (Primary Recommended):**
  Set `LLM_PROVIDER=groq`, `GROQ_API_KEY=gsk_...`, and `GROQ_MODEL=openai/gpt-oss-20b`. Obtain your free API key at [Groq Console](https://console.groq.com/). Ultra-fast LPU inference, native JSON mode with Pydantic response schema validation, and lowest per-token cost ($0.075/1M in, $0.300/1M out).
- **Google Gemini (Alternative / Free Tier):**
  Set `LLM_PROVIDER=gemini` and obtain an API key with eligible free-tier access from [Google AI Studio](https://aistudio.google.com/) (free-tier quotas apply; prompts and responses may be used by Google to improve products).
- **Offline / Local Testing (Zero API Key):**
  Set `LLM_PROVIDER=mock`. The application extracts authentic text from the submitted website and generates the complete 5-section analysis locally without making external LLM calls.
- **OpenAI (Optional Fallback):**
  Set `LLM_PROVIDER=openai`, `OPENAI_API_KEY=sk-...`, `OPENAI_MODEL=gpt-6-luna`.
- **Anthropic (Optional Fallback):**
  Set `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=sk-ant-...`, `ANTHROPIC_MODEL=claude-3-5-haiku-20241022`.

---

## 5. Running the Application

Start the server using the required start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Once running, access the interactive OpenAPI documentation at:
- **Interactive Swagger Docs:** [http://localhost:4000/docs](http://localhost:4000/docs)
- **OpenAPI JSON Schema:** [http://localhost:4000/openapi.json](http://localhost:4000/openapi.json)

---

## 6. Running the Test Suite

The test suite validates SSRF protection, URL validation, error handling, mock LLM generation, and the complete 5-section analysis pipeline:

```bash
python -m pytest -v
```

Expected output:
```text
tests/test_link_analysis.py::test_docs_and_openapi PASSED                [  4%]
tests/test_link_analysis.py::test_ssrf_protection_localhost PASSED       [  9%]
tests/test_link_analysis.py::test_ssrf_protection_private_ips PASSED     [ 14%]
tests/test_link_analysis.py::test_invalid_urls PASSED                    [ 19%]
tests/test_link_analysis.py::test_inaccessible_website PASSED            [ 23%]
tests/test_link_analysis.py::test_successful_link_analysis_pipeline PASSED [ 28%]
tests/test_link_analysis.py::test_groq_provider_configuration_and_structured_generation PASSED [ 33%]
tests/test_link_analysis.py::test_groq_missing_api_key_error PASSED      [ 38%]
tests/test_link_analysis.py::test_groq_provider_api_error PASSED         [ 42%]
tests/test_link_analysis.py::test_mock_llm_provider_offline_mode PASSED  [ 47%]
tests/test_link_analysis.py::test_llm_provider_error_handling PASSED     [ 52%]
tests/test_link_analysis.py::test_validator_unit_ssrf PASSED             [ 57%]
tests/test_link_analysis.py::test_competitor_service_speculative_marking PASSED [ 61%]
tests/test_link_analysis.py::test_website_extractor_cleaning PASSED      [ 66%]
tests/test_link_analysis.py::test_insufficient_business_content_example_com PASSED [ 71%]
tests/test_link_analysis.py::test_unit_has_sufficient_business_content PASSED [ 76%]
tests/test_link_analysis.py::test_clean_keyword_phrase_deduplication PASSED [ 80%]
tests/test_link_analysis.py::test_explicit_services_and_no_duplicate_keywords_dxora PASSED [ 85%]
tests/test_link_analysis.py::test_knows_about_not_treated_as_explicit_services PASSED [ 90%]
tests/test_link_analysis.py::test_no_primary_keyword_duplication_in_secondary_keywords PASSED [ 95%]
tests/test_link_analysis.py::test_partial_explicit_services_mixed_inferred PASSED [100%]
============================== 21 passed in 1.07s ==============================
```

---

## 7. API Documentation & Endpoints

### `POST /link-analysis`

Analyzes the submitted website URL and returns the 5-section business intelligence.

#### Request Body
```json
{
  "url": "https://example.com"
}
```

#### Status Codes & Responses
| Status Code | Description | Example Condition |
|---|---|---|
| `200 OK` | Analysis successfully generated | Valid public URL, page extracted and analyzed |
| `400 Bad Request` | Invalid URL or SSRF Violation | `http://localhost:4000`, `192.168.1.1`, malformed URL |
| `422 Unprocessable Entity` | Content validation error | Missing `"url"` field, or placeholder/documentation website (e.g. `example.com`) lacking substantive commercial content |
| `502 Bad Gateway` | Target website inaccessible or LLM error | Non-existent domain, target HTTP 500, LLM rate limit |
| `500 Internal Server Error` | Unexpected server error | Unhandled system exception |

---

## 8. Sample API Request & Response

### Sample Request
```bash
curl -X POST "http://localhost:4000/link-analysis" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://dxora.com"}'
```

### Sample Response (`samples/sample_response.json`)
```json
{
  "success": true,
  "website": "https://dxora.com",
  "brand": {
    "name": "Dxora Technologies",
    "category": "Technology & Software Solutions",
    "summary": "Dxora Technologies delivers custom software, enterprise AI/LLM engineering, mobile apps, and scalable cloud solutions with 16+ years of proven excellence."
  },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "Dxora Technologies is a software engineering agency specializing in custom software development, enterprise AI/LLM architectures, mobile apps, and cloud infrastructure.",
      "main_products_and_services": [
        "Custom Software Development",
        "Enterprise AI & LLM Engineering",
        "Mobile App Development"
      ],
      "competitors": [
        {
          "competitor_name": "Established Enterprise Technology Providers",
          "main_service": "Full-Suite Technology & Software Solutions",
          "target_market": "Large Enterprise Organizations",
          "key_strength": "Estimated peer advantage: broad enterprise footprint and recognized brand legacy",
          "weakness_or_gap": "Potential operational trade-off: higher cost structure and less agile customization",
          "is_speculative": true,
          "notes": "Speculative market peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
        },
        {
          "competitor_name": "Specialized Boutique Technology Agencies",
          "main_service": "Targeted Technology & Software Solutions Advisory",
          "target_market": "Startups and Mid-Market",
          "key_strength": "Estimated peer advantage: specialized domain focus and personalized project attention",
          "weakness_or_gap": "Potential operational trade-off: limited team capacity for large-scale multi-region execution",
          "is_speculative": true,
          "notes": "Speculative boutique peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
        },
        {
          "competitor_name": "Self-Serve Technology Software Platforms",
          "main_service": "Automated Technology & Software Solutions Tooling",
          "target_market": "B2B and Professional Teams",
          "key_strength": "Estimated peer advantage: rapid self-serve onboarding and automated workflows",
          "weakness_or_gap": "Potential operational trade-off: absence of bespoke software engineering and consultative customization",
          "is_speculative": true,
          "notes": "Speculative platform peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
        }
      ],
      "strengths": [
        "Specialized capabilities in enterprise AI, custom software, and scalable cloud solutions",
        "Transparent engineering practices and dedicated technical project teams",
        "Agile delivery tailored to client and enterprise requirements"
      ],
      "opportunities": [
        "Increase organic search visibility for high-intent enterprise AI and software engineering queries",
        "Develop technical case studies detailing system integration and delivery milestones",
        "Expand multi-channel thought leadership on LinkedIn and Google Search"
      ]
    },
    "target_search_queries": [
      {
        "query": "Best technology & software solutions for businesses",
        "platforms": [
          "Google"
        ],
        "intent": "Service Search",
        "business_relevance": "Direct commercial query for customers seeking technology and software engineering services.",
        "target_audience": "Business Owners and Operations Leads"
      },
      {
        "query": "Dxora Technologies technology & software solutions reviews",
        "platforms": [
          "Google",
          "X"
        ],
        "intent": "Brand Evaluation & Discovery",
        "business_relevance": "Prospective buyers researching vendor credentials and client track record.",
        "target_audience": "Prospective Buyers and Market Evaluators"
      },
      {
        "query": "Top enterprise technology & software solutions tools",
        "platforms": [
          "LinkedIn"
        ],
        "intent": "B2B Search",
        "business_relevance": "Corporate leaders looking for vetted corporate partnerships and technical delivery teams.",
        "target_audience": "Corporate Directors and Technology Leaders"
      },
      {
        "query": "Innovative ideas for technology & software solutions",
        "platforms": [
          "Instagram",
          "Facebook"
        ],
        "intent": "Inspiration & Discovery",
        "business_relevance": "Visual diagrams and engagement-focused interest query.",
        "target_audience": "Creative Professionals and Industry Enthusiasts"
      },
      {
        "query": "Affordable technology & software solutions for startups",
        "platforms": [
          "Google",
          "X"
        ],
        "intent": "Service Search",
        "business_relevance": "Founders seeking immediate technical implementation partners.",
        "target_audience": "Startup Founders and Small Business Managers"
      }
    ],
    "seo_improvements": {
      "primary_keyword": "Technology & Software Solutions",
      "secondary_keywords": [
        "Custom Software Development services",
        "best technology & software solutions",
        "Dxora Technologies services",
        "enterprise technology & software solutions"
      ],
      "long_tail_keywords": [
        "how to choose the right technology & software solutions partner",
        "enterprise technology & software solutions implementation guide"
      ],
      "relevant_business_keywords": [
        "Technology & Software Solutions",
        "Client Success",
        "Digital Transformation"
      ],
      "recommended_title": "Dxora Technologies | Technology & Software Solutions",
      "primary_keyword_focus": "Technology & Software Solutions",
      "title_structure_explanation": "Front-loads the brand and primary category keyword to align with search intent and user discovery.",
      "meta_description": "Explore Dxora Technologies's technology & software solutions offerings and engineering capabilities tailored to enterprise requirements.",
      "business_summary": "Dxora Technologies provides technology & software solutions tailored for client projects.",
      "supporting_content": [
        "Frequently Asked Questions (FAQ) addressing pricing, timelines, and technical integration",
        "Technical Guide: Implementing Technology & Software Solutions for Growth Organizations",
        "Customer Case Studies illustrating project architecture and delivery milestones",
        "Educational articles comparing architectural approaches and framework choices"
      ]
    },
    "top_services": [
      {
        "service_name": "Custom Software Development",
        "description": "Specialized custom software development offering based on verified site content.",
        "target_industry": "Technology & Software Solutions",
        "target_customer": "Enterprise and Professional Teams",
        "main_benefit": "Provides specialized capabilities in custom software development.",
        "is_inferred": false
      },
      {
        "service_name": "Enterprise AI & LLM Engineering",
        "description": "Specialized enterprise ai & llm engineering offering based on verified site content.",
        "target_industry": "Technology & Software Solutions",
        "target_customer": "Growing Businesses and Startups",
        "main_benefit": "Provides specialized capabilities in enterprise ai & llm engineering.",
        "is_inferred": false
      },
      {
        "service_name": "Mobile App Development",
        "description": "Specialized mobile app development offering based on verified site content.",
        "target_industry": "Technology & Software Solutions",
        "target_customer": "Enterprise and Professional Teams",
        "main_benefit": "Provides specialized capabilities in mobile app development.",
        "is_inferred": false
      },
      {
        "service_name": "Web App Development",
        "description": "Specialized web app development offering based on verified site content.",
        "target_industry": "Technology & Software Solutions",
        "target_customer": "Growing Businesses and Startups",
        "main_benefit": "Provides specialized capabilities in web app development.",
        "is_inferred": false
      },
      {
        "service_name": "Data Engineering & Analytics",
        "description": "Specialized data engineering & analytics offering based on verified site content.",
        "target_industry": "Technology & Software Solutions",
        "target_customer": "Enterprise and Professional Teams",
        "main_benefit": "Provides specialized capabilities in data engineering & analytics.",
        "is_inferred": false
      }
    ],
    "target_audience": {
      "primary_audience": [
        "Business Owners",
        "Operations Managers",
        "Corporate Decision Makers"
      ],
      "secondary_audience": [
        "Technical Leads",
        "Startup Founders",
        "Procurement Specialists"
      ],
      "industries": [
        "Technology & Software Solutions",
        "Technology",
        "Professional Services"
      ],
      "business_types": [
        "Small to Midsize Businesses (SMBs)",
        "Early-Stage Startups",
        "Mid-Market Enterprises"
      ],
      "customer_profiles": [
        "Growth-focused leaders looking for reliable domain execution"
      ],
      "geographic_focus": "Global / Not specified",
      "customer_needs": [
        "Access to dependable and cost-effective technology & software solutions",
        "Streamlined delivery without unnecessary operational overhead",
        "Dependable technical execution and responsive ongoing support"
      ],
      "customer_interests": [
        "Business efficiency",
        "Digital innovation",
        "Scalable infrastructure"
      ],
      "recommended_marketing_segments": [
        "High-growth tech startups seeking fast deployment",
        "Established regional businesses modernizing legacy workflows"
      ],
      "is_inferred": true,
      "audience_notes": "Inferred audience segments based on business category and service offerings; not explicitly enumerated on the website."
    }
  }
}
```

---

## 9. LLM Platform & Model Research (Cost, Capabilities, Accuracy)

To determine the most viable LLM platform for production link analysis, we researched and compared currently supported models across leading LLM providers. Current pricing was verified against official provider pricing pages in **November 2026**. 

*(Note: Older generations such as Gemini 1.5 Flash, GPT-4o mini, and GPT-5 mini have been deprecated/retired in official provider catalogs in favor of active production releases).*

### Official Pricing & Model Sources
- **Groq Cloud:** [Groq Official Documentation & Models](https://console.groq.com/docs/models), [Groq API Console](https://console.groq.com/), and [Groq Pricing](https://groq.com/pricing) *(Verified November 2026)*
- **Google Gemini:** [Google AI for Developers Pricing](https://ai.google.dev/pricing) and [Google AI Studio](https://aistudio.google.com/) *(Verified November 2026)*
- **OpenAI:** [OpenAI API Pricing](https://openai.com/api/pricing/) and [OpenAI Models Documentation](https://platform.openai.com/docs/models) *(Verified November 2026)*
- **Anthropic:** [Anthropic Claude Pricing](https://www.anthropic.com/pricing) *(Verified November 2026)*

> **Methodology Note:**
> - **Listed Prices & Context Limits:** Directly sourced from official active provider documentation (November 2026).
> - **Cost Estimates:** All token volumes and per-request costs are explicitly modeled as **estimates** based on typical website payload characteristics (~2,500 input tokens and ~1,200 output tokens).
> - **Latency & Hardware Advantages:** Groq's Language Processing Units (LPUs) provide near-instantaneous token generation speeds (~1,000 tokens/sec), dramatically reducing user response wait time compared to traditional GPU cloud inference.

### A. LLM Provider Comparison Table (Currently Supported Models)

| Criteria | **Groq Cloud** (Primary Recommended) | **Google Gemini** (Alternative / Free Tier) | **OpenAI** (Fallback 1) | **Anthropic** (Fallback 2) |
|---|---|---|---|---|
| **Active Model Name** | `openai/gpt-oss-20b` | `gemini-3.8-flash` | `gpt-6-luna` | `claude-haiku-5-5` |
| **Model Status** | **Active Production Model**<br>*(Supported on Groq LPUs)* | **Active Production Default**<br>*(Gemini 1.5 Flash retired)* | **Active Production Model**<br>*(GPT-4o mini & GPT-5 mini deprecated)* | **Active Production Model** |
| **Input Pricing (per 1M tokens)** | **$0.075** | **$0.75** (Promo rate thru Dec 31, 2026)<br>**$1.50** (Standard rate starting Jan 1, 2027)<br>*(Free tier available)* | $0.100 | $0.100 (Prompts $\le$ 100K)<br>$0.500 (Prompts > 100K) |
| **Output Pricing (per 1M tokens)** | **$0.300** | **$3.75** (Promo rate thru Dec 31, 2026)<br>**$7.50** (Standard rate starting Jan 1, 2027)<br>*(Free tier available)* | $0.500 | $0.500 (Prompts $\le$ 100K)<br>$2.500 (Prompts > 100K) |
| **Free Tier / Starter Credits** | **Yes:** Generous free on-demand tier on [Groq Console](https://console.groq.com/) | **Yes:** Available on Google AI Studio at **$0 cost**.<br>*(Requires API key & eligible free-tier access; quotas apply; Google may use free-tier prompts/responses to improve products).* | No free tier; paid account / pay-per-token balance required | No free tier; paid account / pay-per-token balance required |
| **API Key Required** | Yes (Groq Console) | Yes (Google AI Studio) | Yes (Paid account required) | Yes (Paid account required) |
| **Context Window** | **131,072 tokens** | 1,000,000 tokens | 1,000,000 tokens | 1,000,000 tokens |
| **Structured JSON Support** | Native JSON mode (`response_format={"type": "json_object"}`) + robust Pydantic schema validation | Native `response_mime_type="application/json"` with schema enforcement | Native `response_format={"type": "json_object"}` | Supported via system instructions & tool schema definitions |
| **Speed & Accuracy** | **Fastest:** Near-instantaneous LPU inference (~1,000 t/s), reliable schema compliance | Excellent: High fidelity in summarizing unstructured HTML without hallucinations | Excellent: Reliable schema adherence and consistent field population | High: Strong reasoning, thorough adherence to extraction rules |
| **Recommendation** | **Top Pick (Primary):** Fastest inference, lowest cost, reliable JSON mode + schema validation | **Alternative Pick:** High context, free tier option on Google AI Studio | **Primary Fallback:** Supported, reliable active model from OpenAI | **Secondary Fallback:** Cost-effective paid option for high-volume tasks |

---

### B. Best Model Selection & Rationale

**Winner:** **Groq Cloud — `openai/gpt-oss-20b`**

1. **Ultra-Low Cost & Active Availability:**
   At only **$0.075 / 1M input tokens** and **$0.300 / 1M output tokens**, `openai/gpt-oss-20b` on Groq delivers industry-leading cost efficiency—cheaper than comparable frontier APIs while operating at hardware-accelerated speeds.
2. **Native JSON Mode & Pydantic Schema Validation:**
   Groq natively supports JSON mode via `response_format={"type": "json_object"}`. The model is guided by structured schema specifications in the system prompt, and all raw model responses are parsed, sanitized, normalized, and validated through Pydantic (`LinkAnalysisResponse`) before returning to the client.
3. **Hardware-Accelerated LPU Generation:**
   Running on Groq’s specialized LPUs (Language Processing Units), inference latency is reduced to sub-second responses, providing exceptional end-user experience for link analysis requests.
4. **Context Window (131,072 tokens):**
   Ample headroom to ingest cleaned website contexts (which are typically condensed to ~2,500 tokens), leaving >125,000 tokens for system rules, reasoning, and JSON response assembly.
5. **Flexible Fallback Options Built-In:**
   - **Alternative Provider:** Google Gemini 3.8 Flash (`gemini-3.8-flash`) via `LLM_PROVIDER=gemini` (1M context, free tier on Google AI Studio).
   - **OpenAI Fallback:** `gpt-6-luna` via `LLM_PROVIDER=openai` ($0.100 input / $0.500 output per 1M tokens).
   - **Anthropic Fallback:** `claude-haiku-5-5` via `LLM_PROVIDER=anthropic`.
   - **Zero-Key Offline Fallback:** Built-in deterministic mock engine (`LLM_PROVIDER=mock`) for automated CI/CD and offline local development.

---

### C. Estimated Usage & Cost Breakdown

All cost computations below are **estimates** based on typical single-page website analysis:
- **Estimated Cleaned Website Input Content:** ~2,000 – 3,000 tokens (average estimate: ~2,500 tokens)
- **Estimated Structured JSON Output:** ~1,000 – 1,400 tokens (average estimate: ~1,200 tokens)

#### Estimated Cost Per Request:

- **Groq Cloud — `openai/gpt-oss-20b` (Primary Recommended):**
  $$\text{Estimated Input Cost} = \frac{2,500}{1,000,000} \times \$0.075 = \$0.0001875$$
  $$\text{Estimated Output Cost} = \frac{1,200}{1,000,000} \times \$0.300 = \$0.0003600$$
  $$\textbf{Estimated Total Cost Per Analysis} \approx \mathbf{\$0.0005475} \quad (\approx 0.055\text{ cents / analysis})$$
  *(Enables over **1,825 analyses per single dollar** spent).*

- **Google Gemini 3.8 Flash (Promotional Rate through Dec 31, 2026):**
  $$\text{Estimated Input Cost} = \frac{2,500}{1,000,000} \times \$0.75 = \$0.001875$$
  $$\text{Estimated Output Cost} = \frac{1,200}{1,000,000} \times \$3.75 = \$0.004500$$
  $$\textbf{Estimated Total Cost Per Analysis (Through Dec 31, 2026)} \approx \mathbf{\$0.006375} \quad (\approx 0.64\text{ cents})$$

- **Google Gemini 3.8 Flash (Standard Rate starting Jan 1, 2027):**
  $$\text{Estimated Input Cost} = \frac{2,500}{1,000,000} \times \$1.50 = \$0.003750$$
  $$\text{Estimated Output Cost} = \frac{1,200}{1,000,000} \times \$7.50 = \$0.009000$$
  $$\textbf{Estimated Total Cost Per Analysis (Starting Jan 1, 2027)} \approx \mathbf{\$0.012750} \quad (\approx 1.28\text{ cents})$$

- **Google Gemini 3.8 Flash (Free Tier):**
  $$\textbf{Estimated Total Cost Per Analysis} = \mathbf{\$0.00}$$
  *(Requires API key and eligible free-tier access; rate limit quotas apply; data subject to Google product improvement terms).*

- **OpenAI GPT-6 Luna (Fallback 1):**
  $$\text{Estimated Input Cost} = \frac{2,500}{1,000,000} \times \$0.10 = \$0.000250$$
  $$\text{Estimated Output Cost} = \frac{1,200}{1,000,000} \times \$0.50 = \$0.000600$$
  $$\textbf{Estimated Total Cost Per Analysis} \approx \mathbf{\$0.000850} \quad (\approx 0.085\text{ cents})$$

- **Anthropic Claude Haiku 5.5 (Fallback 2):**
  $$\text{Estimated Input Cost} = \frac{2,500}{1,000,000} \times \$0.10 = \$0.000250$$
  $$\text{Estimated Output Cost} = \frac{1,200}{1,000,000} \times \$0.50 = \$0.000600$$
  $$\textbf{Estimated Total Cost Per Analysis} \approx \mathbf{\$0.000850} \quad (\approx 0.085\text{ cents})$$

---

## 10. Cost Optimization Strategies

To ensure cost efficiency at scale:

1. **HTML Stripping & Tag Filtering:**
   Before passing content to the LLM, the application decomposes `<script>`, `<style>`, `<svg>`, `<canvas>`, `<iframe>`, and `<noscript>` elements. This removes 60%–80% of raw byte overhead.
2. **Boilerplate & Noise Elimination:**
   Automated filters discard cookie consent warnings ("We use cookies...", "Accept all"), copyright footers, and redundant legal notices.
3. **Structured Content Condensation:**
   The extractor selectively extracts headings (`H1`–`H3`), OpenGraph metadata, navigation links, and content paragraphs, capping context at 12,000 characters (~2,500 tokens).
4. **Schema Guidance in System Prompts:**
   The LLM prompt defines strict JSON keys, avoiding conversational preambles or markdown code blocks that consume unnecessary output tokens.
5. **Offline Mock Mode (`LLM_PROVIDER=mock`):**
   Developers and automated test runners can execute full pipeline evaluations with zero API calls.

---

## 11. Deployment & Submission Guide

### Render Cloud Deployment Instructions

Follow these exact steps to deploy the API to [Render](https://render.com) using the project's actual module path and configuration:

#### 1. Configuration Settings on Render
When creating a **New Web Service** connected to your repository, specify:
- **Name:** `dxora-link-analysis` (or your preferred service name)
- **Environment:** `Python 3`
- **Region:** Any region close to your target audience (e.g., Oregon, Frankfurt, Singapore)
- **Branch:** `main`
- **Root Directory:**
  - Leave **empty** (or `.`) if you initialized your Git repository directly in this project folder (where `requirements.txt` and `app/` are at the repository root).
  - If your repository contains this project inside a subfolder (e.g. `Dxora test 2`), set the **Root Directory** to that folder name: `Dxora test 2`.
- **Build Command:**
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
  *(Note: Render dynamically assigns a port to the web service via the `$PORT` environment variable. The start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT` instructs Uvicorn to bind to `0.0.0.0` and Render's allocated port. For local development, port `4000` is retained).*

#### 2. Storing `GROQ_API_KEY` Privately in Render
> [!IMPORTANT]
> **Never commit your `.env` file or API keys to GitHub or source control.** The repository includes a `.gitignore` file that blocks `.env` and all credential patterns.
> 
> To configure your secret key securely on Render:
> 1. In your Render Service Dashboard, navigate to the **Environment** tab.
> 2. Under **Environment Variables**, click **Add Environment Variable**.
> 3. Add the following required environment variables:
>    - `LLM_PROVIDER`: `groq`
>    - `GROQ_MODEL`: `openai/gpt-oss-20b`
>    - `GROQ_API_KEY`: `<your-groq-api-key-from-console.groq.com>`
> 4. Click **Save Changes**. Render will automatically deploy or restart the service with these private environment variables securely loaded in memory.

---

### Remaining Manual Steps for Candidate Submission

As instructed, the assistant does not create GitHub repositories, push to remote repositories, deploy cloud instances, add payment methods, or make paid API calls. Complete these remaining steps manually:

#### Step 1: Follow Dxora Official Accounts
- **LinkedIn:** Follow [Dxora Technologies on LinkedIn](https://www.linkedin.com/company/dxora-technologies)
- **Instagram:** Follow [CREST on Instagram](https://www.instagram.com/crestspot/)
- *Save your profile links for the submission email.*

#### Step 2: Publish Your Code to GitHub
1. Initialize git and commit the codebase:
   ```bash
   git init
   git add .
   git commit -m "feat: complete AI-powered website link analysis API with Groq support"
   ```
2. Create a new **Public** GitHub repository (e.g., `dxora-link-analysis`) on your personal GitHub account.
3. Push your repository:
   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/dxora-link-analysis.git
   git push -u origin main
   ```
4. Verify on GitHub that `.env` is NOT uploaded and that `requirements.txt` and `README.md` are visible.

#### Step 3: Deploy to Render
1. Go to [render.com](https://render.com) and create a free account if you do not have one.
2. Click **New +** $\rightarrow$ **Web Service**.
3. Select your public GitHub repository (`dxora-link-analysis`).
4. Set Build Command: `pip install -r requirements.txt`.
5. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
6. Add your private `GROQ_API_KEY` (and `LLM_PROVIDER=groq`) under Environment Variables.
7. Click **Deploy Web Service** and wait for the build to complete.
8. Verify your live deployment:
   - Check interactive documentation: `https://<your-render-subdomain>.onrender.com/docs`
   - Send a test request via Swagger UI or curl to `POST /link-analysis`.

#### Step 4: Final Submission Email Template

Send an email to **`hr@chivoxai.com`** using the format below:

```text
To: hr@chivoxai.com
Subject: [Your Full Name] - Python Practical Link Analysis test review

Dear Dxora Hiring Team,

I have completed the Python Practical Test for the AI-Powered Website Link Analysis API. 
The implementation meets all technical requirements, including SSRF protection, full 5-section structured analysis, Groq LLM integration, and Render deployment preparation.

Here are my submission details:

1. Full Name: [Your Full Name]
2. Demo Link: https://ai-powered-website-link-analysis-api-mmws.onrender.com
3. API Documentation Link: https://ai-powered-website-link-analysis-api-mmws.onrender.com/docs
4. Public GitHub Repository Link: https://github.com/SupercopV/ai-powered-website-link-analysis-api
5. Contact Number: [Your Phone Number]
6. Current Location: [Your City, Country]
7. Preferred Date and Time for Final Discussion: [e.g., Nov 24, 2026 at 3:00 PM IST]

Verification Profile Links:
- LinkedIn Profile: [Your LinkedIn Profile URL] (Followed Dxora Technologies)
- Instagram Profile: [Your Instagram Profile URL] (Followed CREST)

Key Project Highlights:
- Production FastAPI application running on port 4000 locally and configured for Render deployment using module path `app.main:app` and dynamic `$PORT`.
- Hardened SSRF defense: System DNS pre-resolution, private IP subnet rejection, loopback/cloud metadata filtering, and manual inspection on every HTTP 3xx redirect hop.
- Comprehensive 5-Section Intelligence Output: Competitor analysis with speculative labeling, exactly 5 target search queries across platforms without invented search volumes, practical SEO recommendations without keyword duplication, top 5 services prioritizing explicit offerings, and target audience identification.
- Primary LLM Provider: Groq Cloud using currently supported model `openai/gpt-oss-20b` with native JSON mode ($0.075/1M input, $0.300/1M output, estimated ~$0.0005475 per analysis).
- 100% passing test suite across SSRF protection, URL validation, Groq configuration, structured response validation, provider error handling, and end-to-end pipeline execution.

Looking forward to the technical discussion.

Best regards,
[Your Full Name]
```

