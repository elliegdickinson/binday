"""binday - subscribable bin-collection calendars for UK councils.

Wraps UKBinCollectionData (MIT) and serves an .ics per address that calendar
apps can subscribe to, so the dates stay current instead of going stale the
day they are downloaded.

Councils are scraped, so every lookup is cached hard (see CACHE_TTL) and rate
limited per IP. Be a good citizen: one fetch per address per day is plenty.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import browser, postcodes
from .ics import build
from .pickers import stockport, syncfusion, wakefield

HERE = pathlib.Path(__file__).parent
COUNCILS: dict = json.loads((HERE / "data" / "councils.json").read_text())

CONTACT = "https://github.com/elliegdickinson/binday"
USER_AGENT = f"bindayBot/0.1 (+{CONTACT})"

CACHE_TTL = 12 * 60 * 60        # seconds - councils publish at most daily
RATE_LIMIT = 30                 # requests per IP per window
RATE_WINDOW = 300               # seconds

COLLECT_TIMEOUT = 45            # seconds, plain-HTTP councils
BROWSER_TIMEOUT = 150           # seconds - Chromium has to start and drive a form
# Chromium is the memory hog on this box, so browser lookups queue rather than
# run together. Everything else stays concurrent.
BROWSER_SLOTS = asyncio.Semaphore(1)

browser.use_system_chromedriver()

# Councils with a postcode -> address picker. Everything else either needs no
# UPRN at all, or asks the user to supply one until a picker is written.
# Each entry is (list addresses, resolve one to a uprn + url).
_SM_LOOKUP, _SM_RESOLVE, _SM_COLLECT = syncfusion.STAFFS_MOORLANDS
_HP_LOOKUP, _HP_RESOLVE, _HP_COLLECT = syncfusion.HIGH_PEAK

PICKERS = {
    "StockportBoroughCouncil": (stockport.lookup, stockport.resolve),
    "StaffordshireMoorlandsDistrictCouncil": (_SM_LOOKUP, _SM_RESOLVE),
    "HighPeakCouncil": (_HP_LOOKUP, _HP_RESOLVE),
    "WakefieldCityCouncil": (wakefield.lookup, wakefield.resolve),
}

# Councils collected natively instead of through UKBinCollectionData, because
# upstream drives them with Selenium and this app has no browser.
COLLECTORS = {
    "StaffordshireMoorlandsDistrictCouncil": _SM_COLLECT,
    "HighPeakCouncil": _HP_COLLECT,
    "WakefieldCityCouncil": wakefield.collect,
}

# ONS local-authority code -> council keys. A handful of codes carry more than
# one council upstream, so this maps to a list and the caller asks rather than
# guessing.
BY_LAD: dict[str, list[str]] = {}
for _key, _value in COUNCILS.items():
    if _value.get("lad"):
        BY_LAD.setdefault(_value["lad"], []).append(_key)

app = FastAPI(title="binday", docs_url="/api/docs", redoc_url=None)

_cache: dict[str, tuple[float, object]] = {}
_hits: dict[str, list[float]] = defaultdict(list)


def _cached(key: str):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    return None


def _store(key: str, value):
    # Never cache an empty result: a council having a bad minute must not
    # poison the cache for the next 12 hours.
    if value:
        _cache[key] = (time.time(), value)
    return value


def _rate_limit(request: Request) -> None:
    ip = (request.headers.get("fly-client-ip")
          or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "?"))
    now = time.time()
    recent = [t for t in _hits[ip] if now - t < RATE_WINDOW]
    if len(recent) >= RATE_LIMIT:
        raise HTTPException(429, "Too many requests - please slow down.")
    recent.append(now)
    _hits[ip] = recent


def _council_or_404(key: str) -> dict:
    council = COUNCILS.get(key)
    if not council:
        raise HTTPException(404, f"Unknown council: {key}")
    return council


# --------------------------------------------------------------------------- #

def _identifiable(key: str, value: dict) -> bool:
    """Can we actually pin this council's lookup to the user's own property?

    Some upstream entries are just a url with one test property's id baked
    into it. With no inputs and no picker we would happily serve a stranger's
    bin dates to everyone, so those count as unsupported, not ready.
    """
    return bool(value["needs"]) or key in PICKERS


@app.get("/api/councils")
async def councils() -> JSONResponse:
    """Every council this build can serve, and what each one needs."""
    listing = [
        {
            "key": key,
            "name": value["name"],
            "needs": value["needs"],
            "picker": key in PICKERS,
            "supported": _identifiable(key, value),
            "browser": bool(value.get("browser")),
            # Ready = a postcode is enough, because either no UPRN is needed
            # or a picker can find it.
            "ready": _identifiable(key, value)
                     and ("uprn" not in value["needs"] or key in PICKERS),
            "note": value["note"],
        }
        for key, value in sorted(COUNCILS.items(), key=lambda kv: kv[1]["name"])
    ]
    return JSONResponse({"count": len(listing), "councils": listing})


@app.get("/api/lookup")
async def lookup(request: Request, postcode: str) -> JSONResponse:
    """Work out which council covers a postcode, so nobody has to pick one."""
    _rate_limit(request)
    postcode = " ".join(postcode.upper().split())
    if not postcodes.looks_like_postcode(postcode):
        raise HTTPException(400, "That doesn't look like a UK postcode.")

    key = f"lad:{postcode}"
    if (hit := _cached(key)) is None:
        found = await postcodes.district(postcode, user_agent=USER_AGENT)
        if not found:
            # Unknown postcode, or postcodes.io is having a moment. Either way
            # the user can still choose their council by hand.
            return JSONResponse({"district": None, "councils": []})
        hit = _store(key, found)

    matches = [
        {
            "key": k,
            "name": COUNCILS[k]["name"],
            "needs": COUNCILS[k]["needs"],
            "picker": k in PICKERS,
            "browser": bool(COUNCILS[k].get("browser")),
            "supported": _identifiable(k, COUNCILS[k]),
            "ready": _identifiable(k, COUNCILS[k])
                     and ("uprn" not in COUNCILS[k]["needs"] or k in PICKERS),
        }
        for k in BY_LAD.get(hit["code"], [])
    ]
    return JSONResponse({"district": hit, "councils": matches})


@app.get("/api/addresses")
async def addresses(request: Request, council: str, postcode: str) -> JSONResponse:
    """Postcode -> pickable addresses, for councils that have a picker."""
    _rate_limit(request)
    _council_or_404(council)
    picker = PICKERS.get(council)
    if not picker:
        raise HTTPException(
            400, f"No address lookup for {council} yet - enter your UPRN.")

    postcode = " ".join(postcode.upper().split())
    key = f"addr:{council}:{postcode}"
    if (hit := _cached(key)) is not None:
        return JSONResponse({"addresses": hit, "cached": True})

    try:
        found = await picker[0](postcode, user_agent=USER_AGENT)
    except Exception as exc:                                  # noqa: BLE001
        raise HTTPException(502, f"Council lookup failed: {exc}") from exc
    return JSONResponse({"addresses": _store(key, found), "cached": False})


@app.get("/api/resolve")
async def resolve(request: Request, council: str, postcode: str,
                  key: str) -> JSONResponse:
    """Turn a picked address into the uprn its council's bin service wants."""
    _rate_limit(request)
    _council_or_404(council)
    picker = PICKERS.get(council)
    if not picker:
        raise HTTPException(400, f"No address lookup for {council} yet.")

    postcode = " ".join(postcode.upper().split())
    cache_key = f"resolve:{council}:{key}"
    if (hit := _cached(cache_key)) is not None:
        return JSONResponse({**hit, "cached": True})

    try:
        found = await picker[1](postcode, key, user_agent=USER_AGENT)
    except Exception as exc:                                  # noqa: BLE001
        raise HTTPException(502, f"Could not confirm that address: {exc}") from exc
    return JSONResponse({**_store(cache_key, found), "cached": False})


def _collect(council: str, url: str, extra: dict) -> list[dict]:
    """Run UKBinCollectionData. Blocking, so callers push it to a thread."""
    if native := COLLECTORS.get(council):
        return native(council, url, extra, user_agent=USER_AGENT)

    from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp

    runner = UKBinCollectionApp()
    args = [council, url]
    for flag, value in extra.items():
        if value:
            args += [f"--{flag}", str(value)]
    runner.set_args(args)
    return json.loads(runner.run()).get("bins", [])


@app.get("/feed/{council}.ics")
async def feed(
    request: Request,
    council: str,
    uprn: str = Query("", max_length=40),
    postcode: str = Query("", max_length=12),
    number: str = Query("", max_length=20),
    url: str = Query("", max_length=500),
    label: str = Query("", max_length=80),
) -> Response:
    """The subscribable calendar. Also what the download button saves."""
    _rate_limit(request)
    meta = _council_or_404(council)

    # Stockport's bin pages are addressed by uprn, so a bare uprn is enough to
    # rebuild the url; the address text in it is decorative.
    if council == "StockportBoroughCouncil" and uprn and not url:
        url = stockport.show_url(uprn, label)

    # Never fall back to the registry url unless the council's lookup is
    # genuinely address-independent - that url carries one test property's id,
    # and serving it would mean handing out someone else's collection dates.
    if not any((uprn, postcode, number, url)):
        if not _identifiable(council, meta):
            raise HTTPException(
                501, f"{meta['name']} isn't supported yet - its lookup needs a "
                     "property id we can't work out from a postcode.")
        raise HTTPException(400, "Tell us which property to look up.")

    target = url or meta["url"]

    needs_browser = meta.get("browser") and council not in COLLECTORS
    cache_key = f"feed:{council}:{uprn}:{postcode}:{number}:{target}"
    if (hit := _cached(cache_key)) is None:
        async def run():
            return await asyncio.wait_for(
                asyncio.to_thread(_collect, council, target, {
                    "uprn": uprn, "postcode": postcode, "number": number,
                }),
                timeout=BROWSER_TIMEOUT if needs_browser else COLLECT_TIMEOUT,
            )
        try:
            if needs_browser:
                async with BROWSER_SLOTS:
                    hit = await run()
            else:
                hit = await run()
        except asyncio.TimeoutError:
            raise HTTPException(504, "The council's site did not respond.")
        except Exception as exc:                              # noqa: BLE001
            raise HTTPException(502, f"Could not read collections: {exc}") from exc
        if not hit:
            raise HTTPException(404, "No collections found for that address.")
        _store(cache_key, hit)

    body = build(hit, place=label or postcode or "your address",
                 council=meta["name"], council_url=meta["url"])
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="bin-collections.ics"',
            "Cache-Control": f"public, max-age={CACHE_TTL}",
        },
    )


@app.get("/api/health")
async def health() -> dict:
    ready = sum(1 for k, v in COUNCILS.items()
                if _identifiable(k, v)
                and ("uprn" not in v["needs"] or k in PICKERS))
    return {"ok": True, "councils": len(COUNCILS), "ready": ready,
            "auto_detectable": len(BY_LAD),
            "browser": sum(1 for v in COUNCILS.values() if v.get("browser"))}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(HERE.parent / "static" / "index.html")


# Brand assets and tokens ship with the app; they change rarely, so cache hard.
app.mount("/assets", StaticFiles(directory=HERE.parent / "static" / "assets"),
          name="assets")


@app.get("/tokens-brand.css")
async def brand_tokens() -> FileResponse:
    return FileResponse(HERE.parent / "static" / "tokens-brand.css",
                        media_type="text/css",
                        headers={"Cache-Control": "public, max-age=604800"})
