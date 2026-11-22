from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class LinkAnalysisRequest(BaseModel):
    url: str = Field(
        ...,
        description="The full HTTP or HTTPS URL of the website to analyze",
        examples=["https://example.com"]
    )


class BrandInfo(BaseModel):
    name: str = Field(..., description="Your brand or business name")
    category: str = Field(..., description="Main business category/industry")
    summary: str = Field(..., description="Business overview and summary")


# Section 1: Competitor vs Your Brand Details
class CompetitorItem(BaseModel):
    competitor_name: str = Field(..., description="Competitor brand name")
    main_service: str = Field(..., description="Primary service or product")
    target_market: str = Field(..., description="Target market or customer segment")
    key_strength: str = Field(..., description="Primary competitor strength")
    weakness_or_gap: str = Field(..., description="Competitor weakness or market gap")
    is_speculative: bool = Field(
        True,
        description="True if competitor finding is an AI-generated suggestion / speculative"
    )
    notes: Optional[str] = Field(None, description="Optional supporting notes or comparison details")


class CompetitorAnalysis(BaseModel):
    brand_overview: str = Field(..., description="Overview of the submitted brand")
    main_products_and_services: List[str] = Field(
        default_factory=list,
        description="Main products and services offered by the brand"
    )
    competitors: List[CompetitorItem] = Field(
        ...,
        min_length=3,
        description="Identified competitors (minimum 3 where reliable info is available)"
    )
    strengths: List[str] = Field(
        ...,
        description="Your brand's competitive advantages and key strengths"
    )
    opportunities: List[str] = Field(
        ...,
        description="Opportunities to improve market positioning"
    )


# Section 2: Top 5 Target Search Queries
class TargetSearchQuery(BaseModel):
    query: str = Field(..., description="Search query potential customers would use")
    platforms: List[str] = Field(
        ...,
        description="Supported platforms: Google Search, Facebook, Instagram, LinkedIn, and/or X"
    )
    intent: str = Field(
        ...,
        description="Search intent (e.g. Service Search, Business Discovery, Inspiration, B2B Search)"
    )
    business_relevance: str = Field(..., description="Why this query is relevant to the business")
    target_audience: str = Field(..., description="Target audience searching for this query")


# Section 3: SEO Improvement
class SEOImprovements(BaseModel):
    primary_keyword: str = Field(..., description="Recommended primary keyword")
    secondary_keywords: List[str] = Field(..., description="Secondary keyword recommendations")
    long_tail_keywords: List[str] = Field(
        default_factory=list,
        description="High-intent long-tail keywords"
    )
    relevant_business_keywords: List[str] = Field(
        default_factory=list,
        description="Relevant business category keywords"
    )
    recommended_title: str = Field(..., description="Recommended SEO page title")
    primary_keyword_focus: Optional[str] = Field(
        None,
        description="Primary keyword focused in the title"
    )
    title_structure_explanation: Optional[str] = Field(
        None,
        description="Explanation of why this title structure is effective"
    )
    meta_description: str = Field(..., description="Recommended human-friendly meta description")
    business_summary: Optional[str] = Field(
        None,
        description="Short human-friendly business summary included in meta"
    )
    supporting_content: List[str] = Field(
        ...,
        description="Suggested content additions (e.g. FAQs, landing pages, blog topics, case studies)"
    )


# Section 4: Top 5 Services
class ServiceItem(BaseModel):
    service_name: str = Field(..., description="Name of the service")
    description: str = Field(..., description="Short explanation of the service")
    target_industry: str = Field(..., description="Relevant business industry")
    target_customer: str = Field(..., description="Potential customer type")
    main_benefit: str = Field(..., description="Why customers need this service / key value")
    is_inferred: bool = Field(
        False,
        description="True if inferred rather than explicitly extracted from website content"
    )


# Section 5: Target Audience Identification
class TargetAudience(BaseModel):
    primary_audience: List[str] = Field(..., description="Primary target audience segments")
    secondary_audience: List[str] = Field(..., description="Secondary target audience segments")
    industries: List[str] = Field(..., description="Target industry segments")
    business_types: List[str] = Field(
        default_factory=list,
        description="Types of businesses served (e.g. Small Businesses, Startups, Enterprise)"
    )
    customer_profiles: List[str] = Field(
        default_factory=list,
        description="Customer persona characteristics and profiles"
    )
    geographic_focus: Optional[str] = Field(
        "Global / Not specified",
        description="Location or geographical focus, if detected on website"
    )
    customer_needs: List[str] = Field(..., description="Customer pain points, challenges, and requirements")
    customer_interests: List[str] = Field(
        default_factory=list,
        description="Potential customer interests"
    )
    recommended_marketing_segments: List[str] = Field(
        default_factory=list,
        description="Recommended audience segments for marketing campaigns"
    )
    is_inferred: bool = Field(
        True,
        description="True if target audience recommendations are AI-inferred rather than explicitly stated on the website"
    )
    audience_notes: Optional[str] = Field(
        None,
        description="Supporting notes clarifying direct detection vs inferred audience recommendations"
    )


class AnalysisData(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: List[TargetSearchQuery] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="Exactly five target search queries across supported platforms"
    )
    seo_improvements: SEOImprovements
    top_services: List[ServiceItem] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="Top five services offered by the business"
    )
    target_audience: TargetAudience


class LinkAnalysisResponse(BaseModel):
    success: bool = Field(True, description="Indicates if analysis completed successfully")
    website: str = Field(..., description="The analyzed website URL")
    brand: BrandInfo = Field(..., description="Brand name, category, and summary")
    analysis: AnalysisData = Field(..., description="Detailed 5-section link analysis")


class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Indicates failed request")
    error: str = Field(..., description="Short error message")
    detail: Optional[str] = Field(None, description="Detailed explanation of the failure")
