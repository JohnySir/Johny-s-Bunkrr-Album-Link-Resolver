import asyncio
import base64
import json
import os
import re
from typing import List, Optional, Tuple, Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit, urlencode, parse_qsl, quote

import aiohttp
from aiohttp import ClientSession, ClientTimeout, client_exceptions
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

API_URLS = (
    "https://get.bunkrr.su/api/_001_v2",
    "https://apidl.bunkr.ru/api/_001_v2",
)

def get_random_user_agent() -> str:
    try:
        return UserAgent().random
    except Exception:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def _b64_to_bytes(b64_str: str) -> bytes:
    return base64.b64decode(b64_str)

def _xor_with_key(data: bytes, key: str) -> str:
    key_bytes = key.encode("utf-8")
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ key_bytes[i % len(key_bytes)]
    return out.decode("utf-8", errors="replace")

def get_api_urls(domain: str) -> List[str]:
    """Generate API URLs based on the provided domain."""
    # Common API patterns for bunkr variants
    return [
        f"https://get.{domain}/api/_001_v2",
        f"https://apidl.{domain}/api/_001_v2",
        "https://get.bunkrr.su/api/_001_v2",  # Hardcoded fallbacks
        "https://apidl.bunkr.ru/api/_001_v2",
    ]

async def resolve_bunkr_url(
    file_id: str,
    domain: str = "bunkrr.su",
    ogname: Optional[str] = None,
    session: Optional[ClientSession] = None,
    max_retries: int = 3,
    backoff_base: float = 1.5,
) -> str:
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": get_random_user_agent(),
        "Origin": f"https://get.{domain}",
        "Referer": f"https://get.{domain}/file/{file_id}",
        "Accept-Language": "en-US,en;q=0.8",
    }

    api_urls = get_api_urls(domain)

    async def _call_with_retry(sess: ClientSession) -> dict:
        last_exc = None
        for api_url in api_urls:
            for attempt in range(max_retries):
                try:
                    async with sess.post(api_url, json={"id": file_id}, headers=headers) as resp:
                        if resp.status == 429:
                            retry_after = resp.headers.get("Retry-After")
                            delay = float(retry_after) if retry_after and retry_after.isdigit() else backoff_base * (2**attempt)
                            await asyncio.sleep(delay)
                            continue
                        resp.raise_for_status()
                        data = await resp.json()
                        if data.get("encrypted"):
                            return data
                        last_exc = ValueError(f"Invalid response from {api_url}: {data}")
                        break
                except Exception as e:
                    last_exc = e
                    await asyncio.sleep(backoff_base * (2**attempt))
        raise last_exc or RuntimeError("Failed to resolve via API")

    if session:
        data = await _call_with_retry(session)
    else:
        async with ClientSession() as sess:
            data = await _call_with_retry(sess)

    timestamp = data["timestamp"]
    enc_url = data["url"]
    key = f"SECRET_KEY_{timestamp // 3600}"
    dec_url = _xor_with_key(_b64_to_bytes(enc_url), key)

    if ogname:
        sep = "&" if "?" in dec_url else "?"
        dec_url = f"{dec_url}{sep}n={quote(ogname)}"
    return dec_url

def sanitize(name: Optional[str]) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name) if name else "album"

class BunkrResolver:
    def __init__(self, session: ClientSession):
        self.session = session
        self.base_domain = "bunkrr.su"

    async def fetch_album_info(self, url: str) -> Tuple[Optional[str], List[dict]]:
        parts = urlsplit(url)
        self.base_domain = parts.netloc.replace("www.", "")
        
        def with_advanced(u: str) -> str:
            u_parts = urlsplit(u)
            q = dict(parse_qsl(u_parts.query))
            q["advanced"] = "1"
            return urlunsplit((u_parts.scheme, u_parts.netloc, u_parts.path, urlencode(q), u_parts.fragment))

        target_url = with_advanced(url)
        headers = {"User-Agent": get_random_user_agent(), "Referer": f"https://{self.base_domain}/"}

        try:
            async with self.session.get(target_url, headers=headers) as resp:
                resp.raise_for_status()
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                
                album_name = None
                album_info = soup.find("div", class_="sm:text-lg")
                if album_info:
                    album_name = album_info.find("h1").text.strip()

                album_files = self._parse_album_files(soup)
                if not album_files:
                    # Fallback to scraping if advanced JSON is missing
                    album_files = self._scrape_blocks(soup, target_url)
                
                return album_name, album_files
        except Exception as e:
            print(f"Error fetching album: {e}")
            return None, []

    def _parse_album_files(self, soup: BeautifulSoup) -> List[dict]:
        def normalize_json(raw: str) -> str:
            out = re.sub(r"(?m)^(\s*)([A-Za-z0-9_]+):", r'\1"\2":', raw)
            out = re.sub(r",\s*([}\]])", r"\1", out)
            out = out.replace("\\'", "'")
            out = re.sub(r"\\(?![\\\\\"/bfnrtu])", r"\\\\", out)
            return out

        for script in soup.find_all("script"):
            text = script.string or script.get_text()
            if text and "window.albumFiles" in text:
                m = re.search(r"window\.albumFiles\s*=\s*(\[.*?]);", text, re.S)
                if m:
                    try:
                        return json.loads(normalize_json(m.group(1)))
                    except: pass
        return []

    def _scrape_blocks(self, soup: BeautifulSoup, base_url: str) -> List[dict]:
        blocks = []
        for div in soup.find_all("div", class_=re.compile(r"grid-(images|videos)_box-txt")):
            a = div.find_previous_sibling("a", href=True) or (div.parent.find("a", href=True) if div.parent else None)
            if a:
                href = urljoin(base_url, a.get("href"))
                m = re.search(r"/(f|i|v)/([A-Za-z0-9]+)", href)
                if m:
                    name = div.find("p").text.strip() if div.find("p") else ""
                    blocks.append({"slug": m.group(2), "name": name, "type": m.group(1)})
        return blocks

    async def get_direct_url(self, item: dict, album_url: str) -> Optional[str]:
        # Try direct CDN from advanced JSON first
        cdn_origin = item.get("cdnOrigin")
        cdn_endpoint = item.get("cdnEndpoint")
        if cdn_origin and cdn_endpoint:
            return urljoin(cdn_origin, cdn_endpoint)
        
        # Fallback to resolving the file page
        slug = item.get("slug")
        if not slug: return None
        
        file_url = urljoin(album_url, f"/f/{slug}")
        headers = {"User-Agent": get_random_user_agent(), "Referer": album_url}
        
        try:
            async with self.session.get(file_url, headers=headers) as resp:
                if resp.status == 200:
                    ctype = resp.headers.get("Content-Type", "")
                    if "text/html" not in ctype:
                        return str(resp.url)
                    
                    # It's an HTML bridge page, use API
                    html = await resp.text()
                    file_id = self._extract_file_id(html)
                    if file_id:
                        ogname = self._extract_ogname(html) or item.get("name")
                        return await resolve_bunkr_url(file_id, self.base_domain, ogname, self.session)
        except: pass
        return None

    def _extract_file_id(self, html: str) -> Optional[str]:
        m = re.search(r"""data-(file-)?id\s*=\s*["']?(\d+)["']?""", html, re.I)
        return m.group(2) if m else None

    def _extract_ogname(self, html: str) -> Optional[str]:
        m = re.search(r"""var\s+ogname\s*=\s*["']([^"']+)["']""", html, re.I)
        return m.group(1).strip() if m else None

async def check_link(session: ClientSession, url: str) -> bool:
    headers = {"User-Agent": get_random_user_agent()}
    try:
        # Try HEAD first
        async with session.head(url, headers=headers, allow_redirects=True, timeout=10) as resp:
            if resp.status in (200, 206):
                ctype = resp.headers.get("Content-Type", "")
                if any(t in ctype.lower() for t in ("image", "video", "audio", "application/octet-stream")):
                    return True
        
        # Fallback to small GET range if HEAD fails or is inconclusive
        headers["Range"] = "bytes=0-1024"
        async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as resp:
            if resp.status in (200, 206):
                ctype = resp.headers.get("Content-Type", "")
                return "text/html" not in ctype.lower()
    except: pass
    return False
