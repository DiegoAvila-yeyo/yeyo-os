"""YeyoOS — HTTP request workflow handler."""

import logging

logger = logging.getLogger("yeyoos.workflows.handlers.http")


async def handle_http_request(config: dict, variables: dict) -> dict:
    """Perform an HTTP request.

    Config:
        url (str): Target URL.
        method (str): HTTP method (default ``"GET"``).
        headers (dict): Extra request headers (default ``{}``).
        body (dict | str | None): Request body (default ``None``).
        timeout (int): Request timeout in seconds (default 30).

    Returns:
        dict with ``status_code``, ``body``, and ``headers``.
    """
    url: str = config.get("url", "")
    method: str = config.get("method", "GET").upper()
    headers: dict = config.get("headers", {})
    body = config.get("body", None)
    timeout: int = config.get("timeout", 30)

    if not url:
        return {"error": "url is required"}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            kwargs: dict = {"headers": headers}

            if body is not None:
                if isinstance(body, dict):
                    kwargs["json"] = body
                else:
                    kwargs["content"] = str(body)

            resp = await client.request(method, url, **kwargs)

        response_headers = dict(resp.headers)
        logger.info("HTTP %s %s → %d", method, url, resp.status_code)
        return {
            "status_code": resp.status_code,
            "body": resp.text,
            "headers": response_headers,
        }

    except Exception as e:
        logger.exception("HTTP request failed")
        return {"error": str(e)}
