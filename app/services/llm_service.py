import json
import logging
import re
from typing import Dict, Any, Optional

from app.config import settings
from app.services.website_extractor import ExtractedWebsiteContent

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Raised when the LLM provider fails, times out, or returns an unprocessable response."""
    pass


ANALYSIS_SYSTEM_PROMPT = """You are an expert AI business, SEO, and competitive intelligence analyst.
Your task is to analyze the extracted content from a specific website and produce a factual, evidence-backed, structured business analysis in JSON format.

CRITICAL INSTRUCTIONS:
1. Base your analysis STRICTLY on evidence extracted from the provided website content.
2. Section 1 (Competitor Analysis): Identify at least 3 realistic competitors or market peer categories. If specific competitors are not mentioned on the site itself, identify plausible market peer categories based on the business domain, and set "is_speculative": true for each. Do not present guessed competitor strengths or weaknesses as verified facts; frame them explicitly as hypothetical peer estimates. In competitor "notes", state clearly that findings are speculative estimates rather than verified benchmarks. NEVER invent fictional brand names or fake corporate entities.
3. Section 2 (Target Search Queries): Provide EXACTLY 5 search queries suitable for potential customers finding this business across Google Search, Facebook, Instagram, LinkedIn, and/or X. NEVER invent search volume numbers, CPC, or ranking metrics. Do not repeat adjacent words within queries (e.g. avoid 'solutions solutions').
4. Section 3 (SEO Improvements): Recommend practical SEO keyword enhancements, a relevant SEO page title, an engaging meta description, and strategic supporting content assets. Never duplicate words within phrases (e.g. avoid 'technology & software solutions solutions'). Avoid listing the primary keyword again as a secondary keyword. Avoid unsupported claims such as 'maximum visibility and CTR', 'proven', or 'guaranteed' unless explicitly cited from website text.
5. Section 4 (Top 5 Services): Identify EXACTLY 5 top services or core offerings. Do not treat JSON-LD `knowsAbout` entries as explicit services. Mark a service explicit ('is_inferred': false) only when it appears as an actual offering, such as in `hasOfferCatalog` or the website's visible services list (e.g. under 'What We Do'). Only add inferred services if fewer than 5 are stated on the website, and label those clearly with 'is_inferred': true. Do not use unsupported claims like 'measurable business ROI' or unmeasured performance claims.
6. Section 5 (Target Audience): Identify primary and secondary target audience segments, industry verticals, customer profiles, geographic focus (if stated on site, else 'Global / Not specified'), and key customer pain points. Mark target audience recommendations as inferred ('is_inferred': true) unless the submitted website explicitly states them. Avoid unsupported ROI claims.
7. Return ONLY a single, valid JSON object matching the requested schema. Do not include markdown preamble or conversational text outside the JSON.
"""

JSON_STRUCTURE_GUIDE = """
Return a JSON object with this exact top-level schema:
{
  "brand": {
    "name": "Brand Name",
    "category": "Main Industry Category",
    "summary": "Concise 2-3 sentence business summary."
  },
  "competitor_analysis": {
    "brand_overview": "Comprehensive overview of the brand and positioning.",
    "main_products_and_services": ["Service A", "Service B"],
    "competitors": [
      {
        "competitor_name": "Competitor 1",
        "main_service": "Main Service",
        "target_market": "Target Market",
        "key_strength": "Estimated peer advantage: ...",
        "weakness_or_gap": "Potential operational trade-off: ...",
        "is_speculative": true,
        "notes": "Speculative market peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
      }
    ],
    "strengths": ["Strength 1", "Strength 2"],
    "opportunities": ["Opportunity 1", "Opportunity 2"]
  },
  "target_search_queries": [
    {
      "query": "search query string",
      "platforms": ["Google", "LinkedIn"],
      "intent": "Service Search / B2B Search / Discovery",
      "business_relevance": "Why this query matches the business",
      "target_audience": "Who searches for this"
    }
  ],
  "seo_improvements": {
    "primary_keyword": "Primary Keyword",
    "secondary_keywords": ["Keyword 1", "Keyword 2"],
    "long_tail_keywords": ["Long tail 1", "Long tail 2"],
    "relevant_business_keywords": ["Category keyword 1", "Category keyword 2"],
    "recommended_title": "Primary Keyword | Brand Name",
    "primary_keyword_focus": "Primary Keyword",
    "title_structure_explanation": "Front-loads brand and primary keyword to align with search intent and user discovery.",
    "meta_description": "Compelling meta description under 160 characters.",
    "business_summary": "Short search snippet summary.",
    "supporting_content": ["FAQ section on pricing", "Industry landing page for Healthcare"]
  },
  "top_services": [
    {
      "service_name": "Service 1",
      "description": "Clear service description",
      "target_industry": "Industry vertical",
      "target_customer": "Target persona",
      "main_benefit": "Core functional value delivered",
      "is_inferred": false
    }
  ],
  "target_audience": {
    "primary_audience": ["Primary Audience A"],
    "secondary_audience": ["Secondary Audience B"],
    "industries": ["Industry 1", "Industry 2"],
    "business_types": ["Small Businesses", "Startups", "Enterprise"],
    "customer_profiles": ["Decision Maker / Role Profile"],
    "geographic_focus": "Identified location or Global",
    "customer_needs": ["Key need or pain point 1", "Key need 2"],
    "customer_interests": ["Interest 1", "Interest 2"],
    "recommended_marketing_segments": ["Segment 1", "Segment 2"],
    "is_inferred": true,
    "audience_notes": "Inferred audience segments based on business domain analysis; not explicitly stated on the website."
  }
}
"""


class LLMService:
    def __init__(self, provider: Optional[str] = None):
        self._provider = provider

    @property
    def provider(self) -> str:
        return (self._provider or settings.LLM_PROVIDER).lower()

    async def generate_analysis(self, extracted: ExtractedWebsiteContent) -> Dict[str, Any]:
        """
        Generate structured analysis based on extracted website content.
        Routes to the configured LLM provider or mock engine.
        """
        prompt_content = extracted.to_llm_context()
        user_prompt = f"Analyze the following website content and generate the full 5-section analysis JSON:\n\n{prompt_content}\n\nSchema requirement:\n{JSON_STRUCTURE_GUIDE}"

        if self.provider == "groq":
            return await self._call_groq(user_prompt)
        elif self.provider == "gemini":
            return await self._call_gemini(user_prompt)
        elif self.provider == "openai":
            return await self._call_openai(user_prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(user_prompt)
        elif self.provider == "mock":
            return self._generate_mock_analysis(extracted)
        else:
            raise LLMProviderError(f"Unsupported LLM provider '{self.provider}'. Supported: groq, gemini, openai, anthropic, mock.")

    async def _call_groq(self, user_prompt: str) -> Dict[str, Any]:
        """Call Groq API using groq Python SDK with JSON mode and Pydantic validation."""
        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise LLMProviderError(
                "GROQ_API_KEY is not configured in the environment. Please add it to your .env file or set LLM_PROVIDER=mock for offline testing."
            )

        try:
            import groq
            client = groq.AsyncGroq(api_key=api_key)

            messages = [
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            try:
                completion = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=4096,
                    temperature=0.2,
                )
            except Exception as req_err:
                # If Groq's server-side JSON validator rejects due to reasoning traces (json_validate_failed),
                # retry with raw completion and parse using our robust JSON sanitizer
                err_str = str(req_err).lower()
                if "json_validate_failed" in err_str or "failed to validate json" in err_str:
                    logger.warning(f"Groq json_validate_failed encountered. Retrying without constrained response_format: {req_err}")
                    completion = await client.chat.completions.create(
                        model=settings.GROQ_MODEL,
                        messages=messages,
                        max_tokens=4096,
                        temperature=0.2,
                    )
                else:
                    raise

            raw_text = completion.choices[0].message.content
            if not raw_text:
                raise LLMProviderError("Groq API returned an empty response.")

            return self._parse_and_sanitize_json(raw_text)
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Groq API error: {str(e)}")

    async def _call_gemini(self, user_prompt: str) -> Dict[str, Any]:
        """Call Google Gemini API using google-genai SDK with JSON mode."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise LLMProviderError(
                "GEMINI_API_KEY is not configured in the environment. Please add it to your .env file or set LLM_PROVIDER=mock for offline testing."
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=ANALYSIS_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            if not response.text:
                raise LLMProviderError("Gemini API returned an empty response.")

            return self._parse_and_sanitize_json(response.text)
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Google Gemini API error: {str(e)}")

    async def _call_openai(self, user_prompt: str) -> Dict[str, Any]:
        """Call OpenAI API using openai SDK with JSON object mode."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise LLMProviderError(
                "OPENAI_API_KEY is not configured in the environment. Please add it to your .env file or set LLM_PROVIDER=mock for offline testing."
            )

        try:
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)

            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            raw_text = completion.choices[0].message.content
            if not raw_text:
                raise LLMProviderError("OpenAI API returned an empty response.")

            return self._parse_and_sanitize_json(raw_text)
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"OpenAI API error: {str(e)}")

    async def _call_anthropic(self, user_prompt: str) -> Dict[str, Any]:
        """Call Anthropic API using anthropic SDK."""
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise LLMProviderError(
                "ANTHROPIC_API_KEY is not configured in the environment. Please add it to your .env file or set LLM_PROVIDER=mock for offline testing."
            )

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)

            message = await client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=4000,
                system=ANALYSIS_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"{user_prompt}\nEnsure the response is strictly raw valid JSON."}
                ],
                temperature=0.2,
            )

            text_blocks = [b.text for b in message.content if getattr(b, "type", "") == "text"]
            raw_text = "".join(text_blocks)
            if not raw_text:
                raise LLMProviderError("Anthropic API returned an empty response.")

            return self._parse_and_sanitize_json(raw_text)
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Anthropic API error: {str(e)}")

    def _parse_and_sanitize_json(self, raw_text: str) -> Dict[str, Any]:
        """
        Robustly clean and parse JSON from model output, handling potential markdown code blocks.
        """
        cleaned = raw_text.strip()
        # Strip ```json ... ``` markdown if wrapped
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                raise LLMProviderError("LLM output is not a JSON object.")
            return data
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to decode LLM JSON: {exc}. Content: {raw_text[:300]}")
            raise LLMProviderError(f"Invalid JSON format returned by LLM provider: {str(exc)}")

    def _generate_mock_analysis(self, extracted: ExtractedWebsiteContent) -> Dict[str, Any]:
        """
        Deterministic, evidence-derived mock analysis generator for offline testing,
        CI/CD, and environments without an active paid API key.
        Extracts genuine brand, service, and topic signals from the submitted website.
        """
        brand_name = (
            extracted.og_site_name
            or (extracted.title.split("-")[0].split("|")[0].strip() if extracted.title else "")
            or "Submitted Brand"
        )
        if len(brand_name) > 40:
            brand_name = brand_name[:40].strip()

        # Deduce category from title and headings
        combined_text = f"{extracted.title} {extracted.meta_description} {' '.join(extracted.headings[:5])}"
        category = "Digital & Professional Services"
        if any(w in combined_text.lower() for w in ["tech", "software", "ai", "platform", "cloud"]):
            category = "Technology & Software Solutions"
        elif any(w in combined_text.lower() for w in ["health", "medical", "clinic"]):
            category = "Healthcare & Wellness"
        elif any(w in combined_text.lower() for w in ["shop", "store", "ecommerce", "retail"]):
            category = "E-Commerce & Retail"
        elif any(w in combined_text.lower() for w in ["finance", "invest", "banking", "capital"]):
            category = "Financial Services"

        summary = extracted.meta_description or (
            f"{brand_name} provides comprehensive {category.lower()} designed to serve modern client and enterprise requirements."
        )

        # Derive services: first prioritize extracted explicit services from JSON-LD / noscript / meta
        explicit_services = list(extracted.discovered_services)
        if not explicit_services:
            explicit_services = [
                h for h in extracted.headings
                if 5 < len(h) < 45 and not any(x in h.lower() for x in ["about", "contact", "home", "privacy", "terms", "what we do", "products"])
            ]
        if not explicit_services and extracted.nav_links:
            explicit_services = [n for n in extracted.nav_links if 3 < len(n) < 35]

        top_services = []
        inferred_functional_roles = [
            (
                f"{category.split('&')[0].strip()} Strategy & Architecture",
                f"Strategic advisory and solution planning in {category.lower()}.",
                "Aligns functional implementation with business objectives."
            ),
            (
                f"{category.split('&')[0].strip()} Integration & Deployment",
                f"System deployment and workflow integration for {category.lower()}.",
                "Ensures smooth operational rollout."
            ),
            (
                f"{category.split('&')[0].strip()} Ongoing Technical Support",
                f"Continuous technical maintenance and operational guidance for {category.lower()}.",
                "Maintains consistent service availability."
            ),
            (
                f"{category.split('&')[0].strip()} Process Optimization",
                f"Workflow assessment and operational optimization in {category.lower()}.",
                "Improves process efficiency across teams."
            ),
            (
                f"{category.split('&')[0].strip()} Quality Assurance & Advisory",
                f"Standards compliance and quality validation for {category.lower()}.",
                "Supports operational integrity and governance."
            ),
        ]

        for i in range(5):
            if i < len(explicit_services):
                name = explicit_services[i]
                is_inf = False
                desc = f"Specialized {name.lower()} offering based on verified site content."
                benefit = f"Provides specialized capabilities in {name.lower()}."
            else:
                tmpl_idx = (i - len(explicit_services)) % len(inferred_functional_roles)
                tmpl = inferred_functional_roles[tmpl_idx]
                name = tmpl[0]
                desc = tmpl[1]
                benefit = tmpl[2]
                is_inf = True

            top_services.append({
                "service_name": name,
                "description": desc,
                "target_industry": category,
                "target_customer": "Enterprise and Professional Teams" if i % 2 == 0 else "Growing Businesses and Startups",
                "main_benefit": benefit,
                "is_inferred": is_inf
            })

        # Competitors (minimum 3, marked speculative, using genuine market peer categories framed as hypothetical estimates)
        competitors = [
            {
                "competitor_name": f"Established Enterprise {category.split()[0]} Providers",
                "main_service": f"Full-Suite {category}",
                "target_market": "Large Enterprise Organizations",
                "key_strength": "Estimated peer advantage: broad enterprise footprint and recognized brand legacy",
                "weakness_or_gap": "Potential operational trade-off: higher cost structure and less agile customization",
                "is_speculative": True,
                "notes": "Speculative market peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
            },
            {
                "competitor_name": f"Specialized Boutique {category.split()[0]} Agencies",
                "main_service": f"Targeted {category} Advisory",
                "target_market": "Startups and Mid-Market",
                "key_strength": "Estimated peer advantage: specialized domain focus and personalized project attention",
                "weakness_or_gap": "Potential operational trade-off: limited team capacity for large-scale multi-region execution",
                "is_speculative": True,
                "notes": "Speculative boutique peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
            },
            {
                "competitor_name": f"Self-Serve {category.split()[0]} Software Platforms",
                "main_service": f"Automated {category} Tooling",
                "target_market": "B2B and Professional Teams",
                "key_strength": "Estimated peer advantage: rapid self-serve onboarding and automated workflows",
                "weakness_or_gap": "Potential operational trade-off: absence of bespoke software engineering and consultative customization",
                "is_speculative": True,
                "notes": "Speculative platform peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
            }
        ]

        # Target search queries (exactly 5 across required platforms)
        target_queries = [
            {
                "query": f"Best {category.lower()} for businesses",
                "platforms": ["Google"],
                "intent": "Service Search",
                "business_relevance": f"Direct commercial query for customers seeking {category.lower()}.",
                "target_audience": "Business Owners and Operations Leads"
            },
            {
                "query": f"{brand_name} {category.lower()} reviews",
                "platforms": ["Google", "X"],
                "intent": "Brand Evaluation & Discovery",
                "business_relevance": "Customers evaluating brand reputation and capabilities.",
                "target_audience": "Prospective Buyers and Market Evaluators"
            },
            {
                "query": f"Top enterprise {category.lower()} tools",
                "platforms": ["LinkedIn"],
                "intent": "B2B Search",
                "business_relevance": "B2B professionals looking for vetted corporate partnerships.",
                "target_audience": "Corporate Directors and Technology Leaders"
            },
            {
                "query": f"Innovative ideas for {category.lower()}",
                "platforms": ["Instagram", "Facebook"],
                "intent": "Inspiration & Discovery",
                "business_relevance": "Visual and engagement-focused interest query.",
                "target_audience": "Creative Professionals and Industry Enthusiasts"
            },
            {
                "query": f"Affordable {category.lower()} options for startups",
                "platforms": ["Google", "X"],
                "intent": "Service Search",
                "business_relevance": "Budget-conscious founders seeking immediate implementation.",
                "target_audience": "Startup Founders and Small Business Managers"
            }
        ]

        primary_kw = f"{brand_name} {category}" if len(f"{brand_name} {category}") < 40 else category

        # Avoid duplicated keyword phrases and avoid repeating the primary keyword in secondary keywords
        cat_lower = category.lower()
        sec_candidates = [
            f"{explicit_services[0]} services" if explicit_services else f"custom {cat_lower}",
            f"best {cat_lower}",
            f"{brand_name} services",
            f"enterprise {cat_lower}",
        ]
        sec_kws = []
        for sk in sec_candidates:
            if sk.lower() != primary_kw.lower() and sk.lower() not in [x.lower() for x in sec_kws]:
                sec_kws.append(sk)

        if "solutions" in cat_lower:
            rec_title = f"{brand_name} | {category}"
        else:
            rec_title = f"{brand_name} | {category} & Solutions"

        return {
            "brand": {
                "name": brand_name,
                "category": category,
                "summary": summary
            },
            "competitor_analysis": {
                "brand_overview": f"{brand_name} is active in {category}, delivering customer-centric solutions.",
                "main_products_and_services": [s["service_name"] for s in top_services[:3]],
                "competitors": competitors,
                "strengths": [
                    f"Focused dedication to {category}",
                    "Transparent service architecture and clear customer value",
                    "Agile delivery tailored to client requirements"
                ],
                "opportunities": [
                    "Increase organic search presence for high-intent queries",
                    "Develop specialized vertical landing pages and customer case studies",
                    "Expand multi-channel engagement on LinkedIn and Google"
                ]
            },
            "target_search_queries": target_queries,
            "seo_improvements": {
                "primary_keyword": primary_kw,
                "secondary_keywords": sec_kws,
                "long_tail_keywords": [
                    f"how to choose the right {category.lower()} partner",
                    f"enterprise {category.lower()} implementation guide"
                ],
                "relevant_business_keywords": [
                    category,
                    "Client Success",
                    "Digital Transformation"
                ],
                "recommended_title": rec_title,
                "primary_keyword_focus": primary_kw,
                "title_structure_explanation": "Front-loads the brand and primary category keyword to align with search intent and user discovery.",
                "meta_description": f"Explore {brand_name}'s {category.lower()} offerings and engineering capabilities tailored to enterprise requirements.",
                "business_summary": f"{brand_name} provides {category.lower()} tailored for client projects.",
                "supporting_content": [
                    "Frequently Asked Questions (FAQ) addressing pricing, timelines, and technical integration",
                    f"Industry Spotlight: {category} for Growth Stage Companies",
                    "Customer Case Studies illustrating project architecture and delivery milestones",
                    "Educational blog series comparing in-house vs outsourced solutions"
                ]
            },
            "top_services": top_services,
            "target_audience": {
                "primary_audience": ["Business Owners", "Operations Managers", "Corporate Decision Makers"],
                "secondary_audience": ["Technical Leads", "Startup Founders", "Procurement Specialists"],
                "industries": [category, "Technology", "Professional Services"],
                "business_types": ["Small to Midsize Businesses (SMBs)", "Early-Stage Startups", "Mid-Market Enterprises"],
                "customer_profiles": ["Growth-focused leaders looking for reliable domain execution"],
                "geographic_focus": "Global / Not specified",
                "customer_needs": [
                    f"Access to dependable and cost-effective {category.lower()}",
                    "Streamlined delivery without unnecessary operational overhead",
                    "Dependable technical execution and responsive ongoing support"
                ],
                "customer_interests": ["Business efficiency", "Digital innovation", "Scalable infrastructure"],
                "recommended_marketing_segments": [
                    "High-growth tech startups seeking fast deployment",
                    "Established regional businesses modernizing legacy workflows"
                ],
                "is_inferred": True,
                "audience_notes": "Inferred audience segments based on business category and service offerings; not explicitly enumerated on the website."
            }
        }
