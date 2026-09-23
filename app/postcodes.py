"""Postcode -> local authority, via postcodes.io.

postcodes.io is free, open and needs no key, and it returns the ONS
local-authority-district code (`codes.admin_district`) - the same code
UKBinCollectionData records as LAD24CD. That pairing is what lets us work out
someone's council from their postcode instead of making them pick it.

It is a third party, so a failure here is never fatal: the caller falls back
to asking the user to choose.
"""
from __future__ import annotations

import re

import httpx

API = "https://api.postcodes.io/postcodes/{postcode}"
VALID = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$", re.I)


def looks_like_postcode(value: str) -> bool:
    return bool(VALID.match(" ".join(value.split())))


async def district(postcode: str, *, user_agent: str) -> dict | None:
    """Return {name, code} for the postcode's council, or None if unknown."""
    postcode = " ".join(postcode.upper().split())
    if not looks_like_postcode(postcode):
        return None

    try:
        async with httpx.AsyncClient(timeout=12,
                                     headers={"User-Agent": user_agent}) as client:
            response = await client.get(API.format(postcode=postcode.replace(" ", "")))
        if response.status_code != 200:
            return None
        result = (response.json() or {}).get("result") or {}
    except Exception:                                          # noqa: BLE001
        return None                                            # never fatal

    code = (result.get("codes") or {}).get("admin_district")
    name = result.get("admin_district")
    if not code or code.startswith("("):      # postcodes.io uses "(pseudo)" codes
        return None
    return {"name": name, "code": code}
