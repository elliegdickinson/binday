"""Postcode -> address picker for Stockport.

Most councils need a UPRN before their bin lookup will answer, and there is no
free national postcode->UPRN service (OS Places API is excluded from the OS
Data Hub free credit). So each council needs its own picker, scraped from the
same address form its residents use. This is the first one.

Stockport runs a Verint wizard, and the sting in the tail is that its address
search returns LOCAL gazetteer ids (1010...) while the bin service is keyed on
a different UPRN (1000...). Only the confirm step reveals the real one, so
picking an address takes two stages:

  lookup(postcode)          1. GET  /bin-collections            -> token + cookie
                            2. POST /bin-collections/address    -> 302
                            3. GET  .../address/automatic       -> <option> list
  resolve(postcode, key)    4. POST .../address/automatic       -> confirm page,
                               which links to myaccount with the REAL uprn

Only the address the user actually picks costs the 4th request.
"""
from __future__ import annotations

import html
import re

import httpx

BASE = "https://forms.stockport.gov.uk"
FORM = f"{BASE}/bin-collections"

TOKEN_RE = re.compile(r'__RequestVerificationToken"[^>]*value="([^"]+)"')
OPTION_RE = re.compile(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', re.S)
# The confirm page's link carries unencoded spaces, so match the id, not the
# whole href - and the id is all we need, the address text is decorative.
UPRN_RE = re.compile(
    r"myaccount\.stockport\.gov\.uk/bin-collections/show/(\d+)")

SHOW_URL = ("https://myaccount.stockport.gov.uk/bin-collections/show/"
            "{uprn}/{address}")


def show_url(uprn: str, address: str = "") -> str:
    return SHOW_URL.format(uprn=uprn, address=address.replace(" ", "%20"))


async def _session(client: httpx.AsyncClient, postcode: str) -> str:
    """Steps 1-3. Returns the address-list page's HTML."""
    page = await client.get(FORM)
    token = TOKEN_RE.search(page.text)
    if not token:
        raise RuntimeError("Stockport form changed: no antiforgery token")
    await client.post(f"{FORM}/address", data={
        "__RequestVerificationToken": token.group(1),
        "yourAddress-postcode": postcode,
        "Path": "address",
    })
    listing = await client.get(f"{FORM}/address/automatic")
    return listing.text


def _options(page: str) -> list[dict]:
    out = []
    for value, label in OPTION_RE.findall(page):
        parts = value.split("|")
        if len(parts) < 2 or not parts[0].isdigit():
            continue                      # the "41 addresses found" placeholder
        text = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        out.append({"key": value, "address": text or parts[-1]})
    return out


async def lookup(postcode: str, *, user_agent: str) -> list[dict]:
    """Return [{key, address}, ...] for a postcode. key is opaque - pass it
    back to resolve() to get the UPRN."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=25,
                                 headers={"User-Agent": user_agent}) as client:
        return _options(await _session(client, postcode))


async def resolve(postcode: str, key: str, *, user_agent: str) -> dict:
    """Turn a picked address into {uprn, address, url}."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=25,
                                 headers={"User-Agent": user_agent}) as client:
        listing = await _session(client, postcode)
        token = TOKEN_RE.search(listing)
        if not token:
            raise RuntimeError("Stockport form changed: no token on address list")
        confirm = await client.post(f"{FORM}/address/automatic", data={
            "__RequestVerificationToken": token.group(1),
            "yourAddress-postcode": postcode,
            "yourAddress-address": key,
            "Path": "address",
        })

    found = UPRN_RE.search(confirm.text)
    if not found:
        raise RuntimeError("Stockport confirm page did not name a UPRN")
    address = key.split("|")[-1]
    return {"uprn": found.group(1), "address": address,
            "url": show_url(found.group(1), address)}
