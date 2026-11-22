import logging
import re
from typing import Dict, Any, List

from app.schemas import (
    LinkAnalysisResponse,
    BrandInfo,
    AnalysisData,
    TargetSearchQuery,
    SEOImprovements,
    ServiceItem,
    TargetAudience,
)
from app.services.website_extractor import WebsiteExtractor, ExtractedWebsiteContent
from app.services.llm_service import LLMService, LLMProviderError
from app.services.competitor_service import CompetitorService
from app.utils.validators import (
    validate_and_sanitize_url,
    InvalidURLError,
    SSRFProtectionError,
    WebsiteInaccessibleError,
    InsufficientBusinessContentError,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, extractor: WebsiteExtractor = None, llm_service: LLMService = None):
        self.extractor = extractor or WebsiteExtractor()
        self.llm_service = llm_service or LLMService()

    @staticmethod
    def _clean_keyword_phrase(text: str) -> str:
        """
        Remove duplicate consecutive words (e.g. 'solutions solutions')
        and clean up whitespace and redundant connectors.
        """
        if not text:
            return ""
        s = str(text).strip()
        # Remove adjacent duplicated words (e.g. 'solutions solutions' -> 'solutions')
        s = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", s, flags=re.IGNORECASE)
        # Remove duplicated connector pairs (e.g. '& Solutions & Solutions' -> '& Solutions')
        s = re.sub(r"\b(\w+)(?:\s*&\s*\1\b)+", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    async def run_analysis(self, raw_url: str) -> LinkAnalysisResponse:
        """
        Execute full link analysis pipeline:
        1. SSRF and URL validation.
        2. Web content extraction and cleaning.
        3. LLM analysis generation.
        4. Competitor intelligence normalization (min 3, speculative marking).
        5. Exact 5 search queries & 5 top services enforcement.
        6. Pydantic validation and response assembly.
        """
        # Step 1: Validate URL & check SSRF
        sanitized_url = validate_and_sanitize_url(raw_url)

        # Step 2: Fetch and extract HTML content
        extracted = await self.extractor.fetch_and_extract(sanitized_url)

        # Step 2b: Validate that website has substantive business/commercial content
        is_substantive, reason = extracted.has_sufficient_business_content()
        if not is_substantive:
            raise InsufficientBusinessContentError(
                f"The submitted website ('{sanitized_url}') lacks substantive commercial or business content ({reason}). "
                "Please provide a URL to an active business or brand website."
            )

        # Step 3: Call LLM with cleaned context
        try:
            raw_analysis = await self.llm_service.generate_analysis(extracted)
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"LLM analysis execution failed: {str(e)}")

        # Step 4: Extract and sanitize Brand Info
        raw_brand = raw_analysis.get("brand", {})
        brand_name = str(raw_brand.get("name") or extracted.og_site_name or extracted.title.split("-")[0].strip() or "Brand").strip()
        category = str(raw_brand.get("category") or "Professional Services").strip()
        summary = str(raw_brand.get("summary") or extracted.meta_description or f"{brand_name} delivers services in {category}.").strip()

        brand = BrandInfo(
            name=brand_name,
            category=category,
            summary=summary,
        )

        # Step 5: Competitor Analysis via CompetitorService
        raw_comp_data = raw_analysis.get("competitor_analysis", {})
        competitor_analysis = CompetitorService.process_competitor_data(
            raw_competitor_data=raw_comp_data,
            brand_name=brand_name,
            business_category=category,
            extracted_text=extracted.cleaned_text,
        )

        # Step 6: Target Search Queries (Exactly 5)
        raw_queries = raw_analysis.get("target_search_queries", [])
        search_queries = self._normalize_search_queries(raw_queries, brand_name, category)

        # Step 7: SEO Improvements
        raw_seo = raw_analysis.get("seo_improvements", {})
        seo_improvements = self._normalize_seo_improvements(raw_seo, brand_name, category)

        # Step 8: Top 5 Services (Exactly 5, with is_inferred flags)
        raw_services = raw_analysis.get("top_services", [])
        top_services = self._normalize_top_services(raw_services, category, extracted)

        # Step 9: Target Audience
        raw_audience = raw_analysis.get("target_audience", {})
        target_audience = self._normalize_target_audience(raw_audience, category, extracted)

        analysis_data = AnalysisData(
            competitor_analysis=competitor_analysis,
            target_search_queries=search_queries,
            seo_improvements=seo_improvements,
            top_services=top_services,
            target_audience=target_audience,
        )

        return LinkAnalysisResponse(
            success=True,
            website=extracted.final_url,
            brand=brand,
            analysis=analysis_data,
        )

    def _normalize_search_queries(
        self, raw_queries: List[Dict[str, Any]], brand_name: str, category: str
    ) -> List[TargetSearchQuery]:
        """Ensure exactly five target search queries across supported platforms."""
        queries: List[TargetSearchQuery] = []
        supported_platforms = ["Google", "Facebook", "Instagram", "LinkedIn", "X"]

        if isinstance(raw_queries, list):
            for q in raw_queries:
                if isinstance(q, dict) and "query" in q:
                    clean_q = self._clean_keyword_phrase(str(q.get("query", "")))
                    if not clean_q:
                        continue
                    plats = q.get("platforms", ["Google"])
                    if not isinstance(plats, list) or not plats:
                        plats = ["Google"]
                    # Filter or map platform names
                    plats = [p for p in plats if any(sp.lower() in p.lower() for sp in supported_platforms)]
                    if not plats:
                        plats = ["Google"]

                    queries.append(
                        TargetSearchQuery(
                            query=clean_q,
                            platforms=plats,
                            intent=str(q.get("intent", "Service Search")).strip(),
                            business_relevance=str(q.get("business_relevance", f"Relevant to {category}")).strip(),
                            target_audience=str(q.get("target_audience", "Target Customers")).strip(),
                        )
                    )

        # Fallback templates if model returned fewer than 5
        fallback_templates = [
            ("Top {category} services for business", ["Google"], "Service Search", "Direct service evaluation", "Business Owners"),
            ("{brand} reviews and solutions", ["Google", "X"], "Brand Discovery", "Reputation check", "Potential Clients"),
            ("Best {category} solutions for companies", ["LinkedIn"], "B2B Search", "B2B vendor discovery", "Procurement & Executives"),
            ("Modern {category} trends and inspiration", ["Instagram", "Facebook"], "Inspiration", "Visual brand engagement", "Industry Creatives"),
            ("Affordable {category} options for startups", ["Google", "X"], "Service Search", "Startup vendor search", "Startup Founders"),
        ]

        idx = 0
        while len(queries) < 5:
            tmpl = fallback_templates[idx % len(fallback_templates)]
            raw_rendered = tmpl[0].format(category=category, brand=brand_name)
            queries.append(
                TargetSearchQuery(
                    query=self._clean_keyword_phrase(raw_rendered),
                    platforms=tmpl[1],
                    intent=tmpl[2],
                    business_relevance=tmpl[3],
                    target_audience=tmpl[4],
                )
            )
            idx += 1

        # Enforce exactly 5
        return queries[:5]

    def _normalize_seo_improvements(
        self, raw_seo: Dict[str, Any], brand_name: str, category: str
    ) -> SEOImprovements:
        """
        Format and validate SEO improvements section, preventing duplicated keyword phrases
        and eliminating unsupported claims.
        """
        primary_kw = self._clean_keyword_phrase(str(raw_seo.get("primary_keyword") or f"{brand_name} {category}"))

        # Secondary keywords - ensure the primary keyword is never repeated in secondary keywords
        raw_sec = raw_seo.get("secondary_keywords") or []
        cat_lower = category.lower()
        if not raw_sec:
            raw_sec = [f"best {cat_lower}", f"{brand_name} services", f"custom {cat_lower}"]

        sec_kws: List[str] = []
        for k in raw_sec:
            cleaned_k = self._clean_keyword_phrase(str(k))
            # Strictly avoid listing primary keyword again as a secondary keyword
            if cleaned_k and cleaned_k.lower() != primary_kw.lower() and cleaned_k.lower() not in [x.lower() for x in sec_kws]:
                sec_kws.append(cleaned_k)

        # Fallback if filtered list has fewer than 3 secondary keywords
        fallback_candidates = [
            f"best {cat_lower}",
            f"{brand_name} services",
            f"enterprise {cat_lower}",
            f"custom {cat_lower}",
        ]
        for fb in fallback_candidates:
            if len(sec_kws) >= 3:
                break
            cleaned_fb = self._clean_keyword_phrase(fb)
            if cleaned_fb and cleaned_fb.lower() != primary_kw.lower() and cleaned_fb.lower() not in [x.lower() for x in sec_kws]:
                sec_kws.append(cleaned_fb)

        raw_long = raw_seo.get("long_tail_keywords") or [
            f"how to implement {category.lower()} for business",
            f"enterprise {category.lower()} implementation guide"
        ]
        long_tail: List[str] = []
        for k in raw_long:
            cleaned_k = self._clean_keyword_phrase(str(k))
            if cleaned_k and cleaned_k.lower() not in [x.lower() for x in long_tail]:
                long_tail.append(cleaned_k)

        raw_rel = raw_seo.get("relevant_business_keywords") or [category, "Digital Transformation", "Enterprise Architecture"]
        rel_kws: List[str] = []
        for k in raw_rel:
            cleaned_k = self._clean_keyword_phrase(str(k))
            if cleaned_k and cleaned_k.lower() not in [x.lower() for x in rel_kws]:
                rel_kws.append(cleaned_k)

        rec_title = self._clean_keyword_phrase(str(raw_seo.get("recommended_title") or f"{brand_name} | Top {category}"))

        # Ensure title structure explanation does not claim unmeasured 'maximum visibility and CTR'
        title_expl = str(raw_seo.get("title_structure_explanation") or "Front-loads the brand and primary category keyword to align with search intent and user discovery.").strip()
        title_expl = re.sub(r"for maximum (?:search )?visibility and CTR\.?", "to align with search intent and user discovery.", title_expl, flags=re.I)

        # Meta description - remove unsupported claims like 'proven'
        meta_desc = str(raw_seo.get("meta_description") or f"Explore {brand_name}'s {category.lower()} offerings and engineering capabilities designed for modern business operations.").strip()
        meta_desc = re.sub(r"\bproven\s+", "", meta_desc, flags=re.I)

        # Business summary
        biz_summary = str(raw_seo.get("business_summary") or f"{brand_name} delivers {category.lower()}.").strip()
        biz_summary = re.sub(r"\bproven\s+", "", biz_summary, flags=re.I)
        biz_summary = re.sub(r"\s*delivering measurable (?:business )?ROI\.?", ".", biz_summary, flags=re.I)

        # Supporting content
        raw_sup = raw_seo.get("supporting_content") or [
            "Dedicated Service Detail Pages",
            "Frequently Asked Questions (FAQ) Section",
            "Industry Case Studies",
        ]
        supporting = []
        for s in raw_sup:
            s_clean = re.sub(r"\bdemonstrating ROI\b", "demonstrating delivery milestones", str(s), flags=re.I)
            if s_clean.strip():
                supporting.append(s_clean.strip())

        return SEOImprovements(
            primary_keyword=primary_kw,
            secondary_keywords=sec_kws,
            long_tail_keywords=long_tail,
            relevant_business_keywords=rel_kws,
            recommended_title=rec_title,
            primary_keyword_focus=self._clean_keyword_phrase(str(raw_seo.get("primary_keyword_focus") or primary_kw)),
            title_structure_explanation=title_expl,
            meta_description=meta_desc,
            business_summary=biz_summary,
            supporting_content=supporting,
        )

    def _normalize_top_services(
        self, raw_services: List[Dict[str, Any]], category: str, extracted: ExtractedWebsiteContent
    ) -> List[ServiceItem]:
        """Ensure exactly 5 top services, prioritizing explicit website services and clearly labeling inferred ones."""
        services: List[ServiceItem] = []

        extracted_text_lower = f"{extracted.cleaned_text} {extracted.meta_description}".lower()
        discovered_lower = [s.lower() for s in extracted.discovered_services]

        if isinstance(raw_services, list):
            for s in raw_services:
                if isinstance(s, dict) and "service_name" in s:
                    s_name = str(s.get("service_name", "")).strip()
                    if not s_name:
                        continue

                    s_lower = s_name.lower()
                    # Check if service is explicitly mentioned in site content or discovered services
                    is_explicit = (
                        any(s_lower in disc or disc in s_lower for disc in discovered_lower)
                        or s_lower in extracted_text_lower
                        or any(h.lower() == s_lower for h in extracted.headings + extracted.nav_links)
                    )

                    is_inferred = bool(s.get("is_inferred", not is_explicit))

                    # Clean main benefit of unsupported hype
                    benefit = str(s.get("main_benefit", f"Supports customer business requirements in {s_name.lower()}.")).strip()
                    benefit = re.sub(r"\bdelivers measurable (?:business )?ROI\.?", "supports operational execution and workflow efficiency.", benefit, flags=re.I)

                    services.append(
                        ServiceItem(
                            service_name=s_name,
                            description=str(s.get("description", f"Specialized {s_name} offering.")).strip(),
                            target_industry=str(s.get("target_industry", category)).strip(),
                            target_customer=str(s.get("target_customer", "Target Clients")).strip(),
                            main_benefit=benefit,
                            is_inferred=is_inferred,
                        )
                    )

        # If fewer than 5 services, first see if there are remaining discovered explicit services from the site!
        for disc in extracted.discovered_services:
            if len(services) >= 5:
                break
            if not any(disc.lower() == existing.service_name.lower() for existing in services):
                services.append(
                    ServiceItem(
                        service_name=disc,
                        description=f"Specialized {disc.lower()} tailored to enterprise requirements.",
                        target_industry=category,
                        target_customer="Enterprise and Growth Teams",
                        main_benefit=f"Provides dedicated capabilities in {disc.lower()}.",
                        is_inferred=False,  # Explicitly discovered from site!
                    )
                )

        # If STILL fewer than 5, pad with logical inferred services
        inferred_service_templates = [
            (
                f"{category.split('&')[0].strip()} Strategy & Architecture",
                f"Strategic advisory and solution planning in {category.lower()}.",
                "Aligns functional implementation with business objectives.",
            ),
            (
                f"{category.split('&')[0].strip()} Workflow Integration",
                f"System deployment and workflow integration for {category.lower()}.",
                "Ensures smooth operational rollout.",
            ),
            (
                f"{category.split('&')[0].strip()} Technical Advisory & Support",
                f"Continuous technical maintenance and operational guidance for {category.lower()}.",
                "Maintains consistent service availability.",
            ),
            (
                f"{category.split('&')[0].strip()} Process Optimization",
                f"Workflow assessment and operational optimization in {category.lower()}.",
                "Improves process efficiency across teams.",
            ),
            (
                f"{category.split('&')[0].strip()} Quality Assurance & Compliance",
                f"Standards compliance and quality validation for {category.lower()}.",
                "Supports operational integrity and governance.",
            ),
        ]

        idx = 0
        while len(services) < 5:
            tmpl = inferred_service_templates[idx % len(inferred_service_templates)]
            services.append(
                ServiceItem(
                    service_name=self._clean_keyword_phrase(tmpl[0]),
                    description=tmpl[1],
                    target_industry=category,
                    target_customer="Enterprise and Growth Teams",
                    main_benefit=tmpl[2],
                    is_inferred=True,  # Clearly labeled as inferred
                )
            )
            idx += 1

        return services[:5]

    def _normalize_target_audience(
        self, raw_audience: Dict[str, Any], category: str, extracted: ExtractedWebsiteContent
    ) -> TargetAudience:
        """Format and validate Target Audience section, marking recommendations as inferred unless explicitly stated on site."""
        prim = raw_audience.get("primary_audience") or ["Business Executives", "Operations Leaders"]
        prim = [str(x).strip() for x in prim if str(x).strip()]

        sec = raw_audience.get("secondary_audience") or ["Technical Teams", "Startup Founders"]
        sec = [str(x).strip() for x in sec if str(x).strip()]

        ind = raw_audience.get("industries") or [category, "Technology"]
        ind = [str(x).strip() for x in ind if str(x).strip()]

        btypes = raw_audience.get("business_types") or ["SMBs", "Startups", "Enterprise Companies"]
        btypes = [str(x).strip() for x in btypes if str(x).strip()]

        raw_needs = raw_audience.get("customer_needs") or ["Operational Efficiency", "Dependable Technical Architecture", "Domain Expertise"]
        needs = []
        for n in raw_needs:
            # Filter out unsupported claims like "Measurable business ROI"
            n_clean = re.sub(r"Measurable business ROI and\s*", "", str(n).strip(), flags=re.IGNORECASE)
            if n_clean.strip():
                needs.append(n_clean.strip())

        raw_interests = raw_audience.get("customer_interests") or ["Technical Innovation", "Scalability"]
        interests = [str(i).strip() for i in raw_interests if str(i).strip() and str(i).strip().lower() != "roi"]

        # Check if site explicitly states target audience
        explicit_markers = ["target audience", "our clients are", "who we serve", "built for", "designed for"]
        is_explicitly_stated = any(m in extracted.cleaned_text.lower() for m in explicit_markers)

        # Check raw flag or infer
        raw_is_inferred = raw_audience.get("is_inferred")
        if raw_is_inferred is not None:
            is_inferred = bool(raw_is_inferred)
        else:
            is_inferred = not is_explicitly_stated

        audience_notes = raw_audience.get("audience_notes")
        if not audience_notes:
            audience_notes = (
                "Inferred audience segments based on business category and service offerings; not explicitly enumerated on the website."
                if is_inferred
                else "Identified from explicit audience descriptions on the website."
            )

        return TargetAudience(
            primary_audience=prim,
            secondary_audience=sec,
            industries=ind,
            business_types=btypes,
            customer_profiles=[str(p).strip() for p in raw_audience.get("customer_profiles", ["Decision Makers"]) if str(p).strip()],
            geographic_focus=str(raw_audience.get("geographic_focus") or "Global / Not specified").strip(),
            customer_needs=needs,
            customer_interests=interests,
            recommended_marketing_segments=[str(m).strip() for m in raw_audience.get("recommended_marketing_segments", ["B2B Decision Makers"]) if str(m).strip()],
            is_inferred=is_inferred,
            audience_notes=audience_notes,
        )
