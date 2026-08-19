from html.parser import HTMLParser
from urllib.parse import urlparse

from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, ListingArtifact, SourceType, utcnow


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored and data.strip():
            self.parts.append(data.strip())


class ListingAdapter:
    async def fetch(self, url: str) -> tuple[ListingArtifact, list[Evidence]]:
        parsed = urlparse(url)
        artifact = ListingArtifact(url=url, source=parsed.netloc, retrieved_at=utcnow())
        if parsed.scheme not in {"http", "https"}:
            artifact.limitations.append("Only HTTP(S) listing URLs are supported.")
            return artifact, []
        try:
            async with async_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "html" not in content_type and "text" not in content_type:
                    artifact.limitations.append(f"Unsupported listing content type: {content_type}")
                    return artifact, []
                parser = _TextExtractor()
                parser.feed(response.text)
                artifact.raw_text = " ".join(parser.parts)[:200_000]
        except Exception as exc:
            artifact.limitations.append(f"Listing retrieval unavailable: {type(exc).__name__}")
            return artifact, []
        evidence = Evidence(
            source_type=SourceType.LISTING,
            source=EvidenceSource(publisher=parsed.netloc, dataset="Property listing", url=url),
            field_name="listing_text",
            value=artifact.raw_text,
            semantic_scope="seller/listing claims",
            confidence=0.7,
            limitations=[
                "Listing content is a claim source and has not been independently verified."
            ],
        )
        return artifact, [evidence]
