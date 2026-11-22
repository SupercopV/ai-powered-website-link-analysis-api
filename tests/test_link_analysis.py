import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.website_extractor import ExtractedWebsiteContent
from app.utils.validators import SSRFProtectionError, WebsiteInaccessibleError


@pytest.fixture
def mock_extracted_content():
    return ExtractedWebsiteContent(
        url="https://example.com",
        final_url="https://example.com",
        title="Example Brand - Enterprise Cloud Solutions",
        meta_description="Example Brand provides cutting-edge cloud infrastructure and managed services.",
        meta_keywords="cloud, enterprise, devops, security",
        og_site_name="Example Brand",
        headings=["Cloud Migration Services", "DevOps Automation", "24/7 Managed Infrastructure"],
        nav_links=["Home", "Services", "Cloud Migration", "DevOps", "Managed IT", "Contact"],
        body_paragraphs=[
            "Example Brand helps mid-market and enterprise organizations modernize their IT architectures.",
            "Our certified engineers specialize in AWS, Azure, and Google Cloud implementations.",
            "Accelerate your digital transformation while reducing infrastructure run rates by 30%."
        ],
        cleaned_text="Example Brand provides cloud migration, DevOps, and managed cloud infrastructure."
    )


@pytest.fixture
def mock_llm_payload():
    return {
        "brand": {
            "name": "Example Brand",
            "category": "Cloud Infrastructure & DevOps",
            "summary": "Example Brand provides enterprise cloud modernization and managed services."
        },
        "competitor_analysis": {
            "brand_overview": "Example Brand delivers enterprise cloud and DevOps engineering.",
            "main_products_and_services": ["Cloud Migration", "DevOps Automation", "Managed Cloud"],
            "competitors": [
                {
                    "competitor_name": "CloudScale Global",
                    "main_service": "Enterprise Cloud Architecture",
                    "target_market": "Fortune 500 Enterprises",
                    "key_strength": "Global footprint and vast partner network",
                    "weakness_or_gap": "High billing rates and slow project kickoff",
                    "is_speculative": True,
                    "notes": "Speculative competitor identified via business category analysis."
                },
                {
                    "competitor_name": "DevOpsWorks Inc",
                    "main_service": "CI/CD Pipeline Automation",
                    "target_market": "High-growth tech startups",
                    "key_strength": "Specialized developer tooling focus",
                    "weakness_or_gap": "Lacks comprehensive 24/7 managed operations",
                    "is_speculative": True,
                    "notes": "Speculative competitor in automation niche."
                },
                {
                    "competitor_name": "InfraCore Systems",
                    "main_service": "Managed IT Infrastructure",
                    "target_market": "Mid-market corporations",
                    "key_strength": "Longstanding legacy infrastructure experience",
                    "weakness_or_gap": "Slower adoption of modern cloud-native standards",
                    "is_speculative": True,
                    "notes": "Speculative competitor offering legacy-to-cloud transition."
                }
            ],
            "strengths": [
                "Agile deployment methodology with certified cloud architects",
                "Proven 30% infrastructure cost reduction framework",
                "Dedicated customer success and proactive 24/7 monitoring"
            ],
            "opportunities": [
                "Develop targeted self-serve assessment tools for CTOs",
                "Publish in-depth case studies for financial and healthcare compliance migrations",
                "Expand B2B thought leadership on LinkedIn"
            ]
        },
        "target_search_queries": [
            {
                "query": "Enterprise cloud migration consulting",
                "platforms": ["Google"],
                "intent": "Service Search",
                "business_relevance": "High-intent transactional search for core cloud offering",
                "target_audience": "CTOs and IT Directors"
            },
            {
                "query": "Example Brand cloud infrastructure reviews",
                "platforms": ["Google", "X"],
                "intent": "Brand Discovery",
                "business_relevance": "Prospects verifying reputation and delivery quality",
                "target_audience": "Procurement Managers and VP of Engineering"
            },
            {
                "query": "Best devops automation companies for midmarket",
                "platforms": ["LinkedIn"],
                "intent": "B2B Search",
                "business_relevance": "B2B decision-maker exploring automation partners",
                "target_audience": "DevOps Leaders and Engineering Managers"
            },
            {
                "query": "Cloud architecture modernization best practices",
                "platforms": ["LinkedIn", "X"],
                "intent": "Inspiration & Research",
                "business_relevance": "Establishes technical thought leadership",
                "target_audience": "System Architects and Lead Developers"
            },
            {
                "query": "Affordable 24/7 managed cloud support",
                "platforms": ["Google", "Facebook"],
                "intent": "Service Search",
                "business_relevance": "Immediate solution search for operations support",
                "target_audience": "Startup Founders and IT Operations Leads"
            }
        ],
        "seo_improvements": {
            "primary_keyword": "Enterprise Cloud Migration",
            "secondary_keywords": ["DevOps Automation Services", "Managed Cloud Infrastructure", "Cloud Cost Optimization"],
            "long_tail_keywords": ["how to migrate enterprise workloads to AWS", "managed devops consulting for midmarket"],
            "relevant_business_keywords": ["Cloud Infrastructure", "Kubernetes", "DevSecOps", "Cloud Modernization"],
            "recommended_title": "Enterprise Cloud Migration & DevOps Services | Example Brand",
            "primary_keyword_focus": "Enterprise Cloud Migration",
            "title_structure_explanation": "Combines core primary keyword with secondary offering and recognizable brand name.",
            "meta_description": "Modernize your IT infrastructure with Example Brand. Expert cloud migration and DevOps automation designed to cut costs and accelerate delivery.",
            "business_summary": "Expert cloud migration and DevOps automation for mid-market and enterprise.",
            "supporting_content": [
                "AWS vs Azure vs GCP Migration Comparison Guide",
                "Cloud Security and Compliance FAQ",
                "Case Study: Reducing AWS Run Rate by 32% for Fintech SaaS",
                "Interactive Cloud Readiness Calculator"
            ]
        },
        "top_services": [
            {
                "service_name": "Cloud Migration Services",
                "description": "Seamless workload migration to AWS, Azure, and Google Cloud with zero downtime.",
                "target_industry": "Cloud Infrastructure",
                "target_customer": "Enterprise CTOs and Infrastructure Directors",
                "main_benefit": "Accelerates cloud transition while minimizing business interruption.",
                "is_inferred": False
            },
            {
                "service_name": "DevOps Automation",
                "description": "End-to-end CI/CD pipeline design, Infrastructure-as-Code, and containerization.",
                "target_industry": "Software & SaaS",
                "target_customer": "Engineering Leads and VP of Technology",
                "main_benefit": "Shortens deployment release cycles from weeks to minutes.",
                "is_inferred": False
            },
            {
                "service_name": "24/7 Managed Infrastructure",
                "description": "Continuous monitoring, incident response, and performance tuning.",
                "target_industry": "All Digital Businesses",
                "target_customer": "Operations Teams",
                "main_benefit": "Guarantees 99.99% uptime and proactive threat mitigation.",
                "is_inferred": False
            },
            {
                "service_name": "Cloud Cost Optimization & FinOps",
                "description": "Comprehensive resource audit and right-sizing to eliminate cloud waste.",
                "target_industry": "Growth Tech & Enterprises",
                "target_customer": "Chief Financial Officers and IT Directors",
                "main_benefit": "Drives immediate 20-40% savings on cloud monthly spend.",
                "is_inferred": True
            },
            {
                "service_name": "Cloud Security & Compliance Auditing",
                "description": "SOC2, ISO27001, and HIPAA architecture hardening and posture management.",
                "target_industry": "FinTech and HealthTech",
                "target_customer": "Compliance Officers and CISOs",
                "main_benefit": "Ensures complete regulatory compliance without slowing innovation.",
                "is_inferred": True
            }
        ],
        "target_audience": {
            "primary_audience": ["Chief Technology Officers (CTOs)", "VPs of Engineering", "IT Directors"],
            "secondary_audience": ["DevOps Engineers", "Cloud Architects", "Startup Founders"],
            "industries": ["Enterprise SaaS", "Financial Technology", "E-Commerce", "Healthcare IT"],
            "business_types": ["Mid-Market Companies ($10M-$100M ARR)", "Scale-ups", "Enterprises"],
            "customer_profiles": ["Technical leaders managing legacy infrastructure looking to modernize"],
            "geographic_focus": "Global / Not specified",
            "customer_needs": [
                "Eliminate infrastructure downtime during migrations",
                "Automate repetitive deployment workflows",
                "Control escalating AWS and Azure cloud bills"
            ],
            "customer_interests": ["Cloud-native architecture", "Kubernetes", "FinOps", "Developer velocity"],
            "recommended_marketing_segments": [
                "Growth-stage Series B+ SaaS companies needing robust CI/CD pipelines",
                "Traditional retail and financial firms migrating from on-premise data centers"
            ]
        }
    }


@pytest.mark.asyncio
async def test_docs_and_openapi():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Swagger docs endpoint
        res = await client.get("/docs")
        assert res.status_code == 200

        # OpenAPI schema endpoint
        res = await client.get("/openapi.json")
        assert res.status_code == 200
        data = res.json()
        assert "/link-analysis" in data["paths"]
        assert "post" in data["paths"]["/link-analysis"]


@pytest.mark.asyncio
async def test_ssrf_protection_localhost():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Loopback URL
        res = await client.post("/link-analysis", json={"url": "http://localhost:4000"})
        assert res.status_code == 400
        body = res.json()
        assert body["success"] is False
        assert "SSRF" in body["error"] or "blocked" in body["detail"].lower()

        # 127.0.0.1
        res = await client.post("/link-analysis", json={"url": "http://127.0.0.1:8080/admin"})
        assert res.status_code == 400
        body = res.json()
        assert body["success"] is False
        assert "SSRF" in body["error"] or "blocked" in body["detail"].lower()


@pytest.mark.asyncio
async def test_ssrf_protection_private_ips():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for private_url in [
            "http://10.0.0.1",
            "http://192.168.1.1",
            "http://172.16.0.5",
            "http://169.254.169.254/latest/meta-data/",
        ]:
            res = await client.post("/link-analysis", json={"url": private_url})
            assert res.status_code == 400
            body = res.json()
            assert body["success"] is False
            assert "SSRF" in body["error"]


@pytest.mark.asyncio
async def test_invalid_urls():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-http/https schemes
        res = await client.post("/link-analysis", json={"url": "ftp://example.com/file"})
        assert res.status_code == 400
        assert res.json()["success"] is False

        res = await client.post("/link-analysis", json={"url": "file:///etc/passwd"})
        assert res.status_code == 400
        assert res.json()["success"] is False

        # Malformed URL
        res = await client.post("/link-analysis", json={"url": "not-a-valid-url"})
        assert res.status_code == 400
        assert res.json()["success"] is False


@pytest.mark.asyncio
async def test_inaccessible_website():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Domain that fails DNS resolution
        res = await client.post("/link-analysis", json={"url": "https://this-domain-does-not-exist-123456789.org"})
        assert res.status_code == 502
        body = res.json()
        assert body["success"] is False
        assert "inaccessible" in body["error"].lower() or "dns" in body["detail"].lower()


@pytest.mark.asyncio
async def test_successful_link_analysis_pipeline(mock_extracted_content, mock_llm_payload):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://example.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.llm_service.LLMService.generate_analysis", new_callable=AsyncMock) as mock_llm:
            
            mock_fetch.return_value = mock_extracted_content
            mock_llm.return_value = mock_llm_payload

            response = await client.post("/link-analysis", json={"url": "https://example.com"})

            assert response.status_code == 200
            data = response.json()

            # Top-level structure verification
            assert data["success"] is True
            assert data["website"] == "https://example.com"
            assert data["brand"]["name"] == "Example Brand"
            assert data["brand"]["category"] == "Cloud Infrastructure & DevOps"
            assert len(data["brand"]["summary"]) > 10

            analysis = data["analysis"]

            # Section 1: Competitor Analysis
            comp = analysis["competitor_analysis"]
            assert len(comp["competitors"]) >= 3
            assert all("competitor_name" in c for c in comp["competitors"])
            assert all("is_speculative" in c for c in comp["competitors"])
            assert len(comp["strengths"]) >= 1
            assert len(comp["opportunities"]) >= 1

            # Section 2: Exactly 5 Target Search Queries
            queries = analysis["target_search_queries"]
            assert len(queries) == 5
            for q in queries:
                assert "query" in q
                assert "platforms" in q and len(q["platforms"]) >= 1
                assert "intent" in q
                assert "business_relevance" in q
                assert "target_audience" in q

            # Section 3: SEO Improvements
            seo = analysis["seo_improvements"]
            assert seo["primary_keyword"] == "Enterprise Cloud Migration"
            assert len(seo["secondary_keywords"]) >= 1
            assert len(seo["recommended_title"]) > 5
            assert len(seo["meta_description"]) > 10
            assert len(seo["supporting_content"]) >= 1

            # Section 4: Exactly 5 Top Services
            services = analysis["top_services"]
            assert len(services) == 5
            for s in services:
                assert "service_name" in s
                assert "description" in s
                assert "target_industry" in s
                assert "target_customer" in s
                assert "main_benefit" in s
                assert "is_inferred" in s
            # Verify explicit vs inferred distinction
            inferred_count = sum(1 for s in services if s["is_inferred"])
            assert inferred_count > 0

            # Section 5: Target Audience
            audience = analysis["target_audience"]
            assert len(audience["primary_audience"]) >= 1
            assert len(audience["secondary_audience"]) >= 1
            assert len(audience["industries"]) >= 1
            assert len(audience["customer_needs"]) >= 1


@pytest.mark.asyncio
async def test_groq_provider_configuration_and_structured_generation(mock_extracted_content, mock_llm_payload):
    """
    Verify Groq provider configuration, strict JSON mode invocation,
    and structured response validation against the Pydantic schema.
    """
    import json
    from unittest.mock import MagicMock
    from app.services.llm_service import LLMService

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Mock groq chat completion response
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_llm_payload)
        mock_completion.choices = [mock_choice]

        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://example.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.config.settings.LLM_PROVIDER", "groq"), \
             patch("app.config.settings.GROQ_API_KEY", "gsk_test_api_key_valid"), \
             patch("app.config.settings.GROQ_MODEL", "openai/gpt-oss-20b"), \
             patch("groq.AsyncGroq", return_value=mock_async_client):

            mock_fetch.return_value = mock_extracted_content

            response = await client.post("/link-analysis", json={"url": "https://example.com"})
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["brand"]["name"] == "Example Brand"
            assert len(data["analysis"]["target_search_queries"]) == 5
            assert len(data["analysis"]["top_services"]) == 5
            assert len(data["analysis"]["competitor_analysis"]["competitors"]) >= 3

            # Verify groq client was called with correct parameters
            call_kwargs = mock_async_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["model"] == "openai/gpt-oss-20b"
            assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_groq_missing_api_key_error(mock_extracted_content):
    """Verify clean 502 error when GROQ_API_KEY is missing while LLM_PROVIDER=groq."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://example.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.config.settings.LLM_PROVIDER", "groq"), \
             patch("app.config.settings.GROQ_API_KEY", ""):

            mock_fetch.return_value = mock_extracted_content

            response = await client.post("/link-analysis", json={"url": "https://example.com"})
            assert response.status_code == 502
            body = response.json()
            assert body["success"] is False
            assert body["error"] == "LLM Provider Error"
            assert "GROQ_API_KEY is not configured" in body["detail"]


@pytest.mark.asyncio
async def test_groq_provider_api_error(mock_extracted_content):
    """Verify clean 502 Bad Gateway response when Groq API fails or raises an error."""
    mock_async_client = AsyncMock()
    mock_async_client.chat.completions.create = AsyncMock(side_effect=Exception("Groq Rate Limit Exceeded: 429"))

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://example.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.config.settings.LLM_PROVIDER", "groq"), \
             patch("app.config.settings.GROQ_API_KEY", "gsk_test_api_key_valid"), \
             patch("groq.AsyncGroq", return_value=mock_async_client):

            mock_fetch.return_value = mock_extracted_content

            response = await client.post("/link-analysis", json={"url": "https://example.com"})
            assert response.status_code == 502
            body = response.json()
            assert body["success"] is False
            assert body["error"] == "LLM Provider Error"
            assert "Groq API error" in body["detail"]


@pytest.mark.asyncio
async def test_mock_llm_provider_offline_mode(mock_extracted_content):
    """Verify that with LLM_PROVIDER=mock, realistic analysis is produced without API keys."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://example.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.config.settings.LLM_PROVIDER", "mock"):
            
            mock_fetch.return_value = mock_extracted_content

            response = await client.post("/link-analysis", json={"url": "https://example.com"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["analysis"]["target_search_queries"]) == 5
            assert len(data["analysis"]["top_services"]) == 5
            assert len(data["analysis"]["competitor_analysis"]["competitors"]) >= 3


@pytest.mark.asyncio
async def test_llm_provider_error_handling(mock_extracted_content):
    """Verify clean 502 Bad Gateway response when the LLM provider fails."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://example.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.llm_service.LLMService.generate_analysis", side_effect=Exception("API Quota Exceeded")):
            
            mock_fetch.return_value = mock_extracted_content

            response = await client.post("/link-analysis", json={"url": "https://example.com"})
            assert response.status_code == 500 or response.status_code == 502
            body = response.json()
            assert body["success"] is False


def test_validator_unit_ssrf():
    from app.utils.validators import validate_and_sanitize_url, SSRFProtectionError, InvalidURLError

    # IPv6 loopback
    with pytest.raises(SSRFProtectionError):
        validate_and_sanitize_url("http://[::1]/secret")

    # Carrier-grade NAT (100.64.0.0/10)
    with pytest.raises(SSRFProtectionError):
        validate_and_sanitize_url("http://100.64.0.1")

    # Internal domains
    with pytest.raises(SSRFProtectionError):
        validate_and_sanitize_url("http://internal-service.local")

    with pytest.raises(SSRFProtectionError):
        validate_and_sanitize_url("http://backend.internal")

    # Unsupported protocols
    with pytest.raises(InvalidURLError):
        validate_and_sanitize_url("gopher://127.0.0.1:70")

    with pytest.raises(InvalidURLError):
        validate_and_sanitize_url("")


def test_competitor_service_speculative_marking():
    from app.services.competitor_service import CompetitorService

    raw_data = {
        "brand_overview": "Tech firm overview",
        "main_products_and_services": ["AI Platform"],
        "competitors": [
            {
                "competitor_name": "RivalCorp",
                "main_service": "Cloud AI",
                "target_market": "Enterprises",
                "key_strength": "Scale",
                "weakness_or_gap": "Expensive",
            }
        ],
        "strengths": ["Agility"],
        "opportunities": ["Growth"]
    }

    # "RivalCorp" is not mentioned in website text -> must be marked speculative
    res = CompetitorService.process_competitor_data(
        raw_competitor_data=raw_data,
        brand_name="MyTech",
        business_category="AI Software",
        extracted_text="We are MyTech. We do not mention anyone else."
    )

    # Must pad to at least 3 competitors
    assert len(res.competitors) >= 3
    # Check speculative flag
    assert res.competitors[0].is_speculative is True
    assert res.competitors[1].is_speculative is True
    assert res.competitors[2].is_speculative is True


def test_website_extractor_cleaning():
    from app.services.website_extractor import WebsiteExtractor

    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OmniCloud - Secure Enterprise Cloud</title>
        <meta name="description" content="Next generation enterprise cloud infrastructure.">
        <meta name="keywords" content="cloud, kubernetes, security">
        <meta property="og:site_name" content="OmniCloud">
        <script>console.log("malicious or tracker script");</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <nav>
            <a href="/migration">Cloud Migration</a>
            <a href="/security">Cloud Security</a>
        </nav>
        <h1>Cloud Modernization for Enterprise</h1>
        <h2>DevOps Infrastructure</h2>
        <p>OmniCloud helps enterprise teams automate their multi-cloud deployments safely and efficiently.</p>
        <p>We use cookies to enhance your experience. Accept all cookies.</p>
    </body>
    </html>
    """

    extractor = WebsiteExtractor()
    extracted = extractor.extract_content(sample_html, original_url="https://omnicloud.io", final_url="https://omnicloud.io")

    assert extracted.title == "OmniCloud - Secure Enterprise Cloud"
    assert extracted.meta_description == "Next generation enterprise cloud infrastructure."
    assert extracted.og_site_name == "OmniCloud"
    assert "Cloud Modernization for Enterprise" in extracted.headings
    assert "Cloud Migration" in extracted.nav_links
    assert any("OmniCloud helps enterprise teams" in p for p in extracted.body_paragraphs)
    # Verify script content and cookie boilerplate was filtered out
    assert "console.log" not in extracted.cleaned_text
    assert "accept all cookies" not in extracted.cleaned_text.lower()


@pytest.mark.asyncio
async def test_insufficient_business_content_example_com():
    """
    Verify that placeholder / documentation domains like example.com
    return a 422 validation error instead of inventing fake businesses or services.
    """
    from app.services.website_extractor import ExtractedWebsiteContent

    example_com_content = ExtractedWebsiteContent(
        url="https://example.com",
        final_url="https://example.com",
        title="Example Domain",
        meta_description="",
        meta_keywords="",
        og_site_name="",
        headings=[],
        nav_links=[],
        body_paragraphs=[
            "This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission."
        ],
        cleaned_text="This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission."
    )

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://example.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch:

            mock_fetch.return_value = example_com_content

            response = await client.post("/link-analysis", json={"url": "https://example.com"})

            assert response.status_code == 422
            body = response.json()
            assert body["success"] is False
            assert body["error"] == "Insufficient Business Content"
            assert "substantive" in body["detail"].lower() or "placeholder" in body["detail"].lower()


def test_unit_has_sufficient_business_content():
    """Unit test for ExtractedWebsiteContent business validation logic."""
    from app.services.website_extractor import ExtractedWebsiteContent

    # Minimal documentation / placeholder page
    doc_page = ExtractedWebsiteContent(
        url="https://example.com",
        final_url="https://example.com",
        title="Example Domain",
        cleaned_text="This domain is for use in illustrative examples in documents."
    )
    is_sub, reason = doc_page.has_sufficient_business_content()
    assert is_sub is False
    assert "placeholder" in reason.lower() or "illustrative" in reason.lower()

    # Default server page
    nginx_page = ExtractedWebsiteContent(
        url="https://test-server.com",
        final_url="https://test-server.com",
        title="Welcome to nginx!",
        cleaned_text="Welcome to nginx! If you see this page, the nginx web server is successfully installed."
    )
    is_sub, reason = nginx_page.has_sufficient_business_content()
    assert is_sub is False

    # Substantive business page
    business_page = ExtractedWebsiteContent(
        url="https://dxora.com",
        final_url="https://dxora.com",
        title="Dxora Technologies - Enterprise AI & Automation",
        meta_description="Dxora Technologies delivers custom AI agent workflows and enterprise software development.",
        headings=["AI Application Development", "Multi-Platform Automation", "Cloud Infrastructure"],
        body_paragraphs=[
            "We build production AI systems with dedicated engineering teams.",
            "Our clients range from high-growth startups to mid-market enterprises looking to automate core operations."
        ],
        cleaned_text="Dxora Technologies engineers custom AI applications and multi-platform automation pipelines."
    )
    is_sub, _ = business_page.has_sufficient_business_content()
    assert is_sub is True


def test_clean_keyword_phrase_deduplication():
    """Verify that duplicate keyword phrases and redundant connector repetitions are removed."""
    from app.services.analysis_service import AnalysisService

    assert AnalysisService._clean_keyword_phrase("Technology & Software Solutions solutions") == "Technology & Software Solutions"
    assert AnalysisService._clean_keyword_phrase("Top Technology & Software Solutions & Solutions") == "Top Technology & Software Solutions"
    assert AnalysisService._clean_keyword_phrase("software development development company") == "software development company"
    assert AnalysisService._clean_keyword_phrase("AI automation automation") == "AI automation"


@pytest.mark.asyncio
async def test_explicit_services_and_no_duplicate_keywords_dxora():
    """
    Regression test for Dxora (and similar substantive sites):
    - Explicit website services must be used with actual names and marked is_inferred: False.
    - No duplicated keywords (e.g. 'solutions solutions').
    - No unsupported claims (e.g. 'maximum visibility and CTR', 'proven', 'measurable business ROI').
    - Competitor suggestions must be clearly speculative.
    - Target audience recommendations must be marked is_inferred: True.
    """
    import re

    dxora_extracted = ExtractedWebsiteContent(
        url="https://dxora.com",
        final_url="https://dxora.com",
        title="Dxora Technologies – Enterprise AI, Cloud & Digital Transformation",
        meta_description="Dxora Technologies delivers custom software, enterprise AI/LLM engineering, mobile apps, and scalable cloud solutions with 16+ years of proven excellence.",
        headings=["Enterprise AI, Software & Digital Transformation", "What We Do", "Dxora Products"],
        discovered_services=[
            "Custom Software Development",
            "Enterprise AI & LLM Engineering",
            "Mobile App Development",
            "Web App Development",
            "Data Engineering & Analytics",
        ],
        body_paragraphs=[
            "Dxora Technologies delivers custom software development, enterprise AI/LLM engineering, mobile apps, and scalable cloud solutions.",
            "We build production AI systems, cloud architectures, and digital transformation platforms."
        ],
        cleaned_text="Dxora Technologies delivers custom software development, enterprise AI/LLM engineering, mobile apps, and scalable cloud solutions."
    )

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://dxora.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.config.settings.LLM_PROVIDER", "mock"):

            mock_fetch.return_value = dxora_extracted

            response = await client.post("/link-analysis", json={"url": "https://dxora.com"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            analysis = data["analysis"]

            # 1. Services: verify 5 explicit services with is_inferred: False using actual names under "What We Do"
            top_services = analysis["top_services"]
            assert len(top_services) == 5
            expected_names = [
                "Custom Software Development",
                "Enterprise AI & LLM Engineering",
                "Mobile App Development",
                "Web App Development",
                "Data Engineering & Analytics",
            ]
            for s, exp_name in zip(top_services, expected_names):
                assert s["is_inferred"] is False, f"Service {s['service_name']} should be explicit (is_inferred: False)"
                assert s["service_name"] == exp_name
                assert not re.search(r"measurable (?:business )?ROI", s["main_benefit"], re.I)

            # 2. SEO: verify no duplicated keyword phrases and primary keyword is NOT repeated in secondary keywords
            seo = analysis["seo_improvements"]
            primary_kw = seo["primary_keyword"]
            for kw in seo["secondary_keywords"]:
                assert kw.lower() != primary_kw.lower(), f"Primary keyword '{primary_kw}' must not be listed as secondary keyword"
                assert "solutions solutions" not in kw.lower(), f"Duplicate keyword found in: {kw}"
                assert not re.search(r"\b(\w+)\s+\1\b", kw, re.I), f"Repeated word in: {kw}"

            assert "solutions & solutions" not in seo["recommended_title"].lower()
            assert not re.search(r"\b(\w+)\s+\1\b", seo["recommended_title"], re.I)

            # 3. No unsupported claims in SEO and analysis
            assert "maximum visibility and CTR" not in seo["title_structure_explanation"].lower()
            assert not seo["meta_description"].lower().startswith("discover dxora technologies's proven")

            # 4. Competitor analysis: must be speculative
            competitors = analysis["competitor_analysis"]["competitors"]
            assert len(competitors) >= 3
            for c in competitors:
                assert c["is_speculative"] is True
                assert "speculative" in c["notes"].lower() or "hypothetical" in c["notes"].lower()

            # 5. Target audience: must be marked is_inferred: True
            audience = analysis["target_audience"]
            assert audience["is_inferred"] is True
            assert audience["audience_notes"] is not None
            for need in audience["customer_needs"]:
                assert "measurable business roi" not in need.lower()


def test_knows_about_not_treated_as_explicit_services():
    """
    Verify that JSON-LD `knowsAbout` entries are NOT treated as explicit services.
    Only items from actual offerings (hasOfferCatalog, offers) or visible services lists
    may be treated as explicit services.
    """
    from app.services.website_extractor import WebsiteExtractor

    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tech Insights Co</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Tech Insights Co",
            "knowsAbout": [
                "Enterprise AI",
                "Large Language Models (LLM)",
                "Cloud Computing & DevOps",
                "Blockchain Architecture"
            ]
        }
        </script>
    </head>
    <body>
        <h1>Tech Insights Co</h1>
        <p>Tech Insights Co is an independent technology research organization sharing industry knowledge.</p>
    </body>
    </html>
    """

    extractor = WebsiteExtractor()
    extracted = extractor.extract_content(sample_html, original_url="https://techinsights.org", final_url="https://techinsights.org")

    # knowsAbout entries must NOT appear in discovered_services
    for topic in ["Enterprise AI", "Large Language Models (LLM)", "Cloud Computing & DevOps", "Blockchain Architecture"]:
        assert topic not in extracted.discovered_services, f"'{topic}' from knowsAbout should not be in discovered_services"

    assert len(extracted.discovered_services) == 0


def test_no_primary_keyword_duplication_in_secondary_keywords():
    """Verify that secondary keywords never duplicate the primary keyword."""
    from app.services.analysis_service import AnalysisService

    service = AnalysisService()
    raw_seo = {
        "primary_keyword": "Enterprise Cloud Migration",
        "secondary_keywords": [
            "Enterprise Cloud Migration",  # Exact duplicate of primary keyword
            "enterprise cloud migration",  # Case variant duplicate
            "DevOps Consulting",
            "Cloud Infrastructure Support"
        ],
        "recommended_title": "Enterprise Cloud Migration | TechCorp",
        "meta_description": "Modern enterprise cloud migration."
    }

    normalized = service._normalize_seo_improvements(raw_seo, "TechCorp", "Cloud Migration")

    # Primary keyword must NOT be present in secondary_keywords
    assert all(kw.lower() != normalized.primary_keyword.lower() for kw in normalized.secondary_keywords)
    assert "DevOps Consulting" in normalized.secondary_keywords
    assert "Cloud Infrastructure Support" in normalized.secondary_keywords


@pytest.mark.asyncio
async def test_partial_explicit_services_mixed_inferred():
    """
    Verify that when a website provides fewer than 5 explicit services,
    the stated services are marked is_inferred: False and the remaining slots
    are padded with logical inferred services marked is_inferred: True.
    """
    partial_extracted = ExtractedWebsiteContent(
        url="https://boutique-cloud.com",
        final_url="https://boutique-cloud.com",
        title="Boutique Cloud Studio",
        meta_description="Boutique Cloud Studio provides Cloud Migration and Kubernetes Consulting.",
        discovered_services=["Cloud Migration", "Kubernetes Consulting"],
        headings=["Our Core Offerings", "Cloud Migration", "Kubernetes Consulting"],
        cleaned_text="Boutique Cloud Studio provides Cloud Migration and Kubernetes Consulting for midsize companies."
    )

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.services.analysis_service.validate_and_sanitize_url", return_value="https://boutique-cloud.com"), \
             patch("app.services.website_extractor.WebsiteExtractor.fetch_and_extract", new_callable=AsyncMock) as mock_fetch, \
             patch("app.config.settings.LLM_PROVIDER", "mock"):

            mock_fetch.return_value = partial_extracted

            response = await client.post("/link-analysis", json={"url": "https://boutique-cloud.com"})
            assert response.status_code == 200
            data = response.json()

            services = data["analysis"]["top_services"]
            assert len(services) == 5

            # First two services are explicit
            explicit_services = [s for s in services if not s["is_inferred"]]
            inferred_services = [s for s in services if s["is_inferred"]]

            assert len(explicit_services) == 2
            assert len(inferred_services) == 3
            assert explicit_services[0]["service_name"] == "Cloud Migration"
            assert explicit_services[1]["service_name"] == "Kubernetes Consulting"



