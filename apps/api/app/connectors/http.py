import httpx


def client_headers() -> dict[str, str]:
    return {"User-Agent": "MireyeAcquisitionInvestigator/0.1 (evidence research client)"}


def async_client(timeout: float = 30) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=min(timeout, 10)),
        follow_redirects=True,
        headers=client_headers(),
        transport=httpx.AsyncHTTPTransport(retries=2),
    )
