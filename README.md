# Bin Day

Put your UK bin collections in your calendar, and keep them there.

Enter a postcode, pick your address, get a calendar URL you can subscribe to.
Because it is a subscription rather than a download, the dates stay current
instead of going stale the moment you save them.

## How it works

Collection dates come from [UKBinCollectionData][ukbcd] (MIT), which maintains
scrapers for 353 UK councils. This app wraps it with an address picker, an
iCalendar feed and hard caching.

```
postcode ──► /api/lookup ──► council (via postcodes.io + LAD24CD)
                │
                ├─ has a picker ──► /api/addresses ──► pick ──► /api/resolve ─┐
                └─ needs a house number ─────────────────────────────────────┤
                                                                             ▼
                                                        /feed/<council>.ics
                                                                │
                                          calendar app re-fetches every ~12h
```

Nobody picks their council from a list of 352: [postcodes.io][pio] is free and
keyless and returns the ONS local-authority code, which is the same code
UKBinCollectionData records as `LAD24CD`. **334 of the 352 councils match from
a postcode alone.** The manual list is still there for the 18 without a code,
the ONS codes that carry more than one council upstream, and anyone placed
wrongly. postcodes.io failing is never fatal - it falls back to the list.

## Coverage

| | Councils |
|---|---|
| **Total** | **352** |
| Work from a postcode alone | 106 |
| Need you to supply a UPRN yourself | 229 |
| Not supported: lookup needs a property id we can't derive | 20 |
| Collected through headless Chromium | 90 |
| Collected natively despite upstream using Selenium | 3 |
| Auto-detectable from a postcode (have an LAD code) | 334 |

The image ships Chromium, so the councils UKBinCollectionData drives through
Selenium work too. They are slower (tens of seconds rather than a couple) and
are queued one at a time, because Chromium is the memory hog on a small box.
Everything else stays concurrent.

Three councils - Staffordshire Moorlands, High Peak and Wakefield - are flagged
`web_driver` upstream but are collected natively over plain HTTP here, because
it is faster and cheaper than starting a browser. See `app/pickers/`.

### Address lookup is still the gap

192 councils are keyed on a UPRN and **there is no free national postcode →
UPRN service** - OS Places API is explicitly excluded from the OS Data Hub free
credit (£0.0282 per lookup, no free tier). So each of those needs its own
address picker scraped from its own council form. Four exist so far
(`app/pickers/`); until a council has one, the site asks for a UPRN and points
at findmyaddress.co.uk.

## Running it

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn app.main:app --port 8099 --reload
```

Deploy (Fly.io, scales to zero):

```bash
fly launch --no-deploy   # first time only
fly deploy
```

## Being a good citizen

This scrapes council websites, so:

- Every lookup is cached for 12 hours, per address.
- Requests are rate limited per IP (30 per 5 minutes).
- The User-Agent identifies the bot and links back here.
- Empty results are never cached, so a council having a bad minute doesn't
  poison the cache for the rest of the day.

`forms.stockport.gov.uk/robots.txt` is `Disallow: /`, and other councils may be
similar. That is a grey area for a public service rather than a personal
script. If a council objects, remove it from `app/data/councils.json`.

Nothing is stored: no accounts, no database, no addresses on disk. The feed URL
contains the UPRN, which is how it stays stateless.

## Layout

```
app/
  main.py               FastAPI: lookup, councils, addresses, resolve, feed
  postcodes.py          postcode -> local authority, via postcodes.io
  ics.py                bin list -> iCalendar
  data/councils.json    generated from UKBinCollectionData's input.json
  pickers/stockport.py  postcode -> address -> uprn
  pickers/syncfusion.py Public Dashboard councils: picker + collector, no browser
  pickers/wakefield.py  Wakefield: picker + collector, no browser
static/index.html       the whole front end
static/assets/          brand kit logos and swatches
static/tokens-brand.css brand kit CSS variables
tokens/brand-tokens.json  brand kit design tokens
CLAUDE.md               brand rules (kit)
docs/BRAND_GUIDELINES.md  brand guidelines (kit, source of truth)
docs/BRAND_DECISIONS.md   decisions this build made on top of them
tools/build_registry.py regenerates councils.json from upstream

```

Regenerate the council registry after bumping `uk_bin_collection`:

```bash
python3 tools/build_registry.py
```

## Councils that block us

A few councils put a bot challenge in front of their bin pages - Sunderland
serves a Cloudflare managed challenge. Those are listed in `BLOCKED` in
`app/main.py`: the site says so up front and links to the council's own page
rather than letting someone fill a form that cannot succeed. Nothing here tries
to get around a challenge.

If a council lifts it, delete the entry and it works again.

## Caveats

- Not official. Councils change their sites and scrapers break.
- Some councils return only the next collection per bin (Stockport returns
  two dates); others return a year or more. The feed shows whatever the
  council gives, from a week ago onwards.
- Bin names come from the council verbatim, so they vary a lot
  ("Wheeled Bin (180ltr)", "Domestic Waste Collection Service").

[ukbcd]: https://github.com/robbrad/UKBinCollectionData
[pio]: https://postcodes.io/
