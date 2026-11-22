from typing import List, Dict, Any
from app.schemas import CompetitorItem, CompetitorAnalysis


class CompetitorService:
    """
    Handles competitor validation, structuring, and labeling of speculative insights.
    Enforces compliance with Section 1 and Section 9 instructions:
    - Minimum 3 competitors.
    - Speculative/AI-inferred findings must be explicitly labeled (is_speculative=True).
    - No fabricated rankings, search volumes, or unsupported metrics.
    """

    @staticmethod
    def sanitize_competitor_item(comp_dict: Dict[str, Any], extracted_text: str = "") -> CompetitorItem:
        """
        Ensure competitor fields conform to requirements and clearly mark speculative findings.
        """
        name = str(comp_dict.get("competitor_name", "Industry Competitor")).strip()
        main_service = str(comp_dict.get("main_service", "Similar Business Services")).strip()
        target_market = str(comp_dict.get("target_market", "Target Market Segment")).strip()
        key_strength = str(comp_dict.get("key_strength", "Market presence and recognized solutions")).strip()
        weakness_or_gap = str(comp_dict.get("weakness_or_gap", "Higher pricing or slower customization")).strip()
        
        # Check if the competitor name was actually mentioned in the submitted website content
        is_mentioned_in_content = bool(name and name.lower() in extracted_text.lower())
        # If not explicitly named on the site itself, it is an AI-inferred/speculative market competitor
        is_speculative = comp_dict.get("is_speculative", not is_mentioned_in_content)

        # Ensure speculative competitor strengths and weaknesses are clearly framed as hypothetical estimates
        if is_speculative:
            if not any(k in key_strength.lower() for k in ["estimated", "hypothesized", "observed", "speculative"]):
                key_strength = f"Estimated peer advantage: {key_strength}"
            if not any(k in weakness_or_gap.lower() for k in ["potential", "hypothesized", "trade-off", "possible", "estimated"]):
                weakness_or_gap = f"Potential operational trade-off: {weakness_or_gap}"

        notes = comp_dict.get("notes")
        if not notes or "speculative" not in notes.lower():
            notes = (
                "Speculative market peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
                if is_speculative
                else "Mentioned in site context."
            )

        return CompetitorItem(
            competitor_name=name,
            main_service=main_service,
            target_market=target_market,
            key_strength=key_strength,
            weakness_or_gap=weakness_or_gap,
            is_speculative=is_speculative,
            notes=notes,
        )

    @classmethod
    def process_competitor_data(
        cls,
        raw_competitor_data: Dict[str, Any],
        brand_name: str,
        business_category: str,
        extracted_text: str = ""
    ) -> CompetitorAnalysis:
        """
        Validate, normalize, and guarantee minimum 3 competitors in competitor analysis.
        """
        brand_overview = str(raw_competitor_data.get("brand_overview", f"{brand_name} operates in the {business_category} space.")).strip()
        
        main_prods = raw_competitor_data.get("main_products_and_services", [])
        if not isinstance(main_prods, list) or not main_prods:
            main_prods = [business_category]
        main_prods = [str(p).strip() for p in main_prods if str(p).strip()]

        raw_competitors = raw_competitor_data.get("competitors", [])
        if not isinstance(raw_competitors, list):
            raw_competitors = []

        processed_competitors: List[CompetitorItem] = []
        for c in raw_competitors:
            if isinstance(c, dict):
                processed_competitors.append(cls.sanitize_competitor_item(c, extracted_text))

        # Enforce minimum 3 competitors requirement using generic market peer categories
        peer_templates = [
            (
                f"Established Enterprise {business_category.split()[0]} Providers",
                f"Full-Suite {business_category}",
                "Enterprise Organizations",
                "Estimated peer advantage: broad market footprint and established brand recognition",
                "Potential operational trade-off: higher cost structure and less agile custom adaptation",
            ),
            (
                f"Specialized Boutique {business_category.split()[0]} Agencies",
                f"Targeted {business_category} Advisory",
                "Mid-Market & Specialized Clients",
                "Estimated peer advantage: specialized domain focus and personalized project attention",
                "Potential operational trade-off: limited team capacity for large-scale multi-region execution",
            ),
            (
                f"Self-Serve {business_category.split()[0]} Software Platforms",
                f"Automated {business_category} Tooling",
                "Startups & Developer Teams",
                "Estimated peer advantage: rapid self-serve onboarding and automated workflows",
                "Potential operational trade-off: absence of high-touch bespoke engineering and consultative support",
            ),
        ]

        idx = 0
        while len(processed_competitors) < 3:
            tmpl = peer_templates[idx % len(peer_templates)]
            processed_competitors.append(
                CompetitorItem(
                    competitor_name=tmpl[0],
                    main_service=tmpl[1],
                    target_market=tmpl[2],
                    key_strength=tmpl[3],
                    weakness_or_gap=tmpl[4],
                    is_speculative=True,
                    notes="Speculative market peer category for comparative positioning; strengths and weaknesses are hypothetical estimates, not verified facts."
                )
            )
            idx += 1

        strengths = raw_competitor_data.get("strengths", [])
        if not isinstance(strengths, list) or not strengths:
            strengths = [f"Specialized expertise in {business_category}", "Direct customer-focused solutions"]
        strengths = [str(s).strip() for s in strengths if str(s).strip()]

        opportunities = raw_competitor_data.get("opportunities", [])
        if not isinstance(opportunities, list) or not opportunities:
            opportunities = ["Expand digital marketing reach", "Enhance targeted content for specific customer personas"]
        opportunities = [str(o).strip() for o in opportunities if str(o).strip()]

        return CompetitorAnalysis(
            brand_overview=brand_overview,
            main_products_and_services=main_prods,
            competitors=processed_competitors,
            strengths=strengths,
            opportunities=opportunities,
        )
