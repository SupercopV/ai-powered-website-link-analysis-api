import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.validators import (
    validate_and_sanitize_url,
    WebsiteInaccessibleError,
    SSRFProtectionError,
)


import json
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.validators import (
    validate_and_sanitize_url,
    WebsiteInaccessibleError,
    SSRFProtectionError,
)


@dataclass
class ExtractedWebsiteContent:
    url: str
    final_url: str
    title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    og_site_name: str = ""
    headings: List[str] = field(default_factory=list)
    nav_links: List[str] = field(default_factory=list)
    body_paragraphs: List[str] = field(default_factory=list)
    discovered_services: List[str] = field(default_factory=list)
    cleaned_text: str = ""

    def to_llm_context(self, max_length: int = 12000) -> str:
        """
        Format extracted website content into a clean, token-efficient text block
        for LLM processing, removing boilerplate and HTML overhead.
        """
        parts = [
            f"Analyzed Website URL: {self.final_url}",
            f"Page Title: {self.title or 'N/A'}",
            f"Meta Description: {self.meta_description or 'N/A'}",
            f"Meta Keywords: {self.meta_keywords or 'N/A'}",
            f"Brand / Site Name: {self.og_site_name or 'N/A'}",
        ]

        if self.discovered_services:
            parts.append("Explicitly Stated Services / Offerings:\n" + "\n".join(f"- {s}" for s in self.discovered_services[:15]))

        if self.headings:
            parts.append("Key Headings (H1/H2/H3):\n" + "\n".join(f"- {h}" for h in self.headings[:25]))

        if self.nav_links:
            parts.append("Navigation / Section Links:\n" + ", ".join(self.nav_links[:30]))

        if self.body_paragraphs:
            parts.append("Main Body Content:\n" + "\n\n".join(self.body_paragraphs))
        elif self.cleaned_text:
            parts.append(f"Page Text Content:\n{self.cleaned_text}")

        full_context = "\n\n".join(parts)
        if len(full_context) > max_length:
            full_context = full_context[:max_length] + "\n...[Content truncated for token cost optimization]..."

        return full_context

    def has_sufficient_business_content(self) -> tuple[bool, str]:
        """
        Validate whether the page contains substantive business, product, or commercial content.
        Prevents hallucinating business operations on documentation placeholders (e.g. example.com),
        parked domains, or empty default server pages.
        """
        combined = f"{self.title} {self.meta_description} {self.cleaned_text}".lower()

        # Check for well-known documentation, illustrative, or parked domain phrases
        documentation_markers = [
            "documentation examples",
            "illustrative examples",
            "this is not a service",
            "example domain",
            "this domain is for use in",
            "domain is established to be used for",
            "this domain is reserved",
            "domain for sale",
            "buy this domain",
            "website under construction",
            "welcome to nginx",
            "apache2 ubuntu default page",
            "iis windows server",
            "default web page",
            "under maintenance",
        ]

        for marker in documentation_markers:
            if marker in combined:
                return (
                    False,
                    f"Page matches known non-business / placeholder pattern: '{marker}'"
                )

        # Check for commercial/business signals in title, meta description, and content
        business_keywords = [
            "services", "solutions", "software", "technology", "consulting",
            "engineering", "products", "platform", "enterprise", "digital",
            "development", "cloud", "ai", "agency", "company", "management",
            "security", "healthcare", "finance", "automation"
        ]
        has_business_signals = any(k in combined for k in business_keywords)

        words = self.cleaned_text.split()
        # Page must have either substantive body words (>=20), business headings, or a substantive business meta description
        if len(words) < 20 and len(self.headings) == 0 and not (self.meta_description and has_business_signals):
            return (
                False,
                f"Page contains minimal content ({len(words)} words) and no business description or headings"
            )

        return (True, "")


class WebsiteExtractor:
    def __init__(self, timeout: float = None, max_size_bytes: int = None, max_redirects: int = None):
        self.timeout = timeout or settings.REQUEST_TIMEOUT_SECONDS
        self.max_size_bytes = max_size_bytes or settings.MAX_CONTENT_LENGTH_BYTES
        self.max_redirects = max_redirects or settings.MAX_REDIRECTS
        self.user_agent = settings.USER_AGENT

    async def fetch_html(self, target_url: str) -> tuple[str, str]:
        """
        Safely fetch raw HTML from target_url with manual redirect tracking
        and SSRF validation on every redirect step.

        Returns:
            tuple[html_content, final_effective_url]
        """
        current_url = target_url
        redirect_count = 0

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(
            verify=True,
            follow_redirects=False,  # Enforce manual redirect handling to inspect SSRF on each hop
            timeout=httpx.Timeout(self.timeout, connect=5.0),
        ) as client:
            while True:
                try:
                    response = await client.get(current_url, headers=headers)
                except httpx.ConnectTimeout:
                    raise WebsiteInaccessibleError(f"Connection to '{current_url}' timed out.")
                except httpx.ReadTimeout:
                    raise WebsiteInaccessibleError(f"Read timeout while waiting for response from '{current_url}'.")
                except httpx.ConnectError as e:
                    raise WebsiteInaccessibleError(f"Failed to connect to '{current_url}': {str(e)}")
                except httpx.RequestError as e:
                    raise WebsiteInaccessibleError(f"Network error while accessing '{current_url}': {str(e)}")

                # Check redirect status codes (301, 302, 303, 307, 308)
                if response.is_redirect:
                    redirect_count += 1
                    if redirect_count > self.max_redirects:
                        raise WebsiteInaccessibleError(f"Too many redirects (exceeded limit of {self.max_redirects}).")

                    location = response.headers.get("Location")
                    if not location:
                        raise WebsiteInaccessibleError("Redirect response received with no Location header.")

                    next_url = urljoin(current_url, location)
                    # Re-validate the destination URL against SSRF
                    current_url = validate_and_sanitize_url(next_url)
                    continue

                # Not a redirect, verify HTTP status
                if response.status_code >= 400:
                    raise WebsiteInaccessibleError(
                        f"Website returned error HTTP status code {response.status_code} ({response.reason_phrase})."
                    )

                # Check content length
                content_length_header = response.headers.get("Content-Length")
                if content_length_header and int(content_length_header) > self.max_size_bytes:
                    raise WebsiteInaccessibleError(
                        f"Website response payload exceeds maximum allowable limit of {self.max_size_bytes} bytes."
                    )

                raw_bytes = response.content
                if len(raw_bytes) > self.max_size_bytes:
                    raise WebsiteInaccessibleError(
                        f"Website response payload exceeds maximum allowable limit of {self.max_size_bytes} bytes."
                    )

                html_text = response.text
                return html_text, str(response.url or current_url)

    def extract_content(self, html: str, original_url: str, final_url: str) -> ExtractedWebsiteContent:
        """
        Parse HTML, extract structured business data (including JSON-LD and noscript fallbacks),
        strip non-content markup (scripts, styles, svg, canvas, iframes),
        and identify explicit service offerings.
        """
        soup = BeautifulSoup(html, "html.parser")

        visible_services: List[str] = []
        catalog_offerings: List[str] = []
        json_ld_descriptions: List[str] = []

        # 1. Parse JSON-LD structured schemas before decomposing scripts
        # Note: Do NOT treat `knowsAbout` entries as explicit services.
        # Only actual offerings (hasOfferCatalog, offers, makesOffer) qualify as catalog offerings.
        for script_tag in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
            try:
                raw_json = script_tag.string
                if not raw_json:
                    continue
                data = json.loads(raw_json)
                graphs = data.get("@graph", [data]) if isinstance(data, dict) else [data]
                for item in graphs:
                    if not isinstance(item, dict):
                        continue

                    # knowsAbout provides background domain topics for context, NOT explicit services
                    knows_about = item.get("knowsAbout", [])
                    if isinstance(knows_about, list):
                        for k in knows_about:
                            if isinstance(k, str) and 3 < len(k.strip()) < 50:
                                json_ld_descriptions.append(f"Domain Focus: {k.strip()}")

                    # Actual Offer catalog / products / services
                    catalog = item.get("hasOfferCatalog", {})
                    if isinstance(catalog, dict):
                        for elem in catalog.get("itemListElement", []):
                            if isinstance(elem, dict) and elem.get("name"):
                                name = elem["name"].strip()
                                if 3 < len(name) < 50 and name not in catalog_offerings:
                                    catalog_offerings.append(name)

                    # makesOffer or offers
                    for off in item.get("makesOffer", []) or item.get("offers", []):
                        if isinstance(off, dict) and off.get("name"):
                            name = off["name"].strip()
                            if 3 < len(name) < 50 and name not in catalog_offerings:
                                catalog_offerings.append(name)

                    desc = item.get("description")
                    if isinstance(desc, str) and len(desc.strip()) > 20:
                        json_ld_descriptions.append(desc.strip())
            except Exception:
                pass

        # 2. Extract content and visible service lists from noscript and DOM
        noscript_headings: List[str] = []
        noscript_paragraphs: List[str] = []
        dom_trees = []

        for ns in soup.find_all("noscript"):
            try:
                ns_soup = BeautifulSoup(ns.decode_contents(), "html.parser")
                dom_trees.append(ns_soup)
                for h in ns_soup.find_all(["h1", "h2", "h3", "h4"]):
                    text = h.get_text(separator=" ", strip=True)
                    if text and len(text) > 3 and text not in noscript_headings:
                        noscript_headings.append(text)
                for p in ns_soup.find_all(["p", "li"]):
                    text = p.get_text(separator=" ", strip=True)
                    if text and len(text) > 20 and not self._is_boilerplate(text):
                        if text not in noscript_paragraphs:
                            noscript_paragraphs.append(text)
            except Exception:
                pass

        dom_trees.append(soup)

        # Extract visible services from sections like "What We Do", "Our Services", "Services", "Our Solutions"
        service_section_headers = ["what we do", "our services", "services", "core services", "what we offer", "our solutions"]
        for tree in dom_trees:
            text_blocks = tree.get_text(separator="\n", strip=True).splitlines()
            i = 0
            while i < len(text_blocks):
                line = text_blocks[i].strip()
                if any(line.lower() == sh or line.lower().startswith(sh + ":") for sh in service_section_headers):
                    j = i + 1
                    while j < len(text_blocks):
                        candidate = text_blocks[j].strip()
                        # Stop if hitting another major section like products, about, contact, or portfolio
                        if any(x in candidate.lower() for x in ["products", "about", "contact", "case studies", "portfolio", "testimonials", "clients", "footer"]):
                            break
                        if 4 <= len(candidate) <= 60 and not any(candidate.lower().startswith(x) for x in ["privacy", "terms", "cookie", "read more"]):
                            if candidate not in visible_services:
                                visible_services.append(candidate)
                        j += 1
                    i = j
                else:
                    i += 1

        # 3. Remove non-content elements (scripts, styles, svg, canvas, iframe)
        for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
            tag.decompose()

        # 4. Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # 5. Extract Meta tags
        meta_desc = ""
        meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)}) or \
                        soup.find("meta", attrs={"property": "og:description"})
        if meta_desc_tag and meta_desc_tag.get("content"):
            meta_desc = meta_desc_tag["content"].strip()

        meta_keywords = ""
        meta_kw_tag = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
        if meta_kw_tag and meta_kw_tag.get("content"):
            meta_keywords = meta_kw_tag["content"].strip()

        og_site_name = ""
        og_tag = soup.find("meta", attrs={"property": "og:site_name"})
        if og_tag and og_tag.get("content"):
            og_site_name = og_tag["content"].strip()

        # 6. Extract explicit services from meta description if structured
        # e.g., "delivers custom software, enterprise AI/LLM engineering, mobile apps, and scalable cloud solutions"
        meta_services: List[str] = []
        if meta_desc:
            match = re.search(r"(?:delivers|offers|provides|specializing in)\s+([^.]+)", meta_desc, flags=re.I)
            if match:
                raw_clause = match.group(1)
                clauses = re.split(r",|\band\b", raw_clause)
                for c in clauses:
                    c_clean = re.sub(r"^(?:with|\d+\+?\s*years?.*)", "", c, flags=re.I).strip()
                    if 4 < len(c_clean) < 45 and not any(w in c_clean.lower() for w in ["excellence", "experience", "proven"]):
                        formatted = c_clean.title()
                        if formatted not in meta_services:
                            meta_services.append(formatted)

        # 7. Extract Headings (H1, H2, H3)
        headings: List[str] = list(noscript_headings)
        for h in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = h.get_text(separator=" ", strip=True)
            if text and len(text) > 3 and text not in headings:
                headings.append(text)

        # 8. Extract Navigation links / menu items
        nav_links: List[str] = []
        for nav in soup.find_all(["nav", "header"]):
            for a in nav.find_all("a"):
                text = a.get_text(separator=" ", strip=True)
                if text and 2 < len(text) < 50 and text not in nav_links:
                    nav_links.append(text)

        # 9. Extract body paragraphs and lists
        paragraphs: List[str] = list(json_ld_descriptions) + list(noscript_paragraphs)
        if meta_desc and len(meta_desc) > 25 and meta_desc not in paragraphs:
            paragraphs.append(meta_desc)

        for element in soup.find_all(["p", "li", "section", "article"]):
            text = element.get_text(separator=" ", strip=True)
            if len(text) > 25 and not self._is_boilerplate(text):
                if text not in paragraphs:
                    paragraphs.append(text)

        cleaned_full_text = " ".join(paragraphs)

        # Prioritize visible services (e.g. "What We Do" on Dxora), followed by catalog offerings (hasOfferCatalog/offers)
        # Note: JSON-LD knowsAbout is strictly excluded from discovered_services
        clean_discovered_services: List[str] = []
        for s in visible_services + catalog_offerings + meta_services:
            s_clean = s.strip()
            if 4 <= len(s_clean) <= 60 and s_clean not in clean_discovered_services:
                clean_discovered_services.append(s_clean)

        return ExtractedWebsiteContent(
            url=original_url,
            final_url=final_url,
            title=title,
            meta_description=meta_desc,
            meta_keywords=meta_keywords,
            og_site_name=og_site_name,
            headings=headings[:30],
            nav_links=nav_links[:30],
            body_paragraphs=paragraphs[:40],
            discovered_services=clean_discovered_services[:15],
            cleaned_text=cleaned_full_text[:12000],
        )

    def _is_boilerplate(self, text: str) -> bool:
        lower = text.lower()
        boilerplate_triggers = [
            "cookie policy",
            "we use cookies",
            "all rights reserved",
            "terms of service",
            "privacy policy",
            "accept all cookies",
            "manage cookies",
        ]
        return any(trigger in lower for trigger in boilerplate_triggers)

    async def fetch_and_extract(self, validated_url: str) -> ExtractedWebsiteContent:
        """
        Orchestrate fetching and content extraction.
        """
        html, final_url = await self.fetch_html(validated_url)
        return self.extract_content(html, original_url=validated_url, final_url=final_url)
