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

Nobody picks their council from a list of 259: [postcodes.io][pio] is free and
keyless and returns the ONS local-authority code, which is the same code
UKBinCollectionData records as `LAD24CD`. **244 of the 259 councils match from
a postcode alone.** The manual list is still there for the 15 without a code,
the three ONS codes that carry more than one council upstream, and anyone
placed wrongly. postcodes.io failing is never fatal - it falls back to the
list.

## Coverage, honestly

| | Councils |
|---|---|
| In this build (no headless browser needed) | 260 |
| **Work from a postcode alone** | **52** |
| Need you to supply a UPRN yourself | 192 |
| Not supported: lookup needs a property id we can't derive | 16 |
| Excluded for now (need headless Chrome) | 92 |
| Auto-detectable from a postcode (have an LAD code) | 245 |

Of the 52, two (Stockport and Staffordshire Moorlands) get there via a
postcode → address picker; the rest take a postcode and house number directly.

**Some "needs a browser" councils don't.** Staffordshire Moorlands is driven
upstream through Selenium because its Syncfusion dashboard renders
client-side - but the page is a Razor Page whose handlers are ordinary form
posts, and the data is embedded as JSON before Syncfusion touches it. Plain
HTTP gets all of it. `app/pickers/staffsmoorlands.py` does the lookup *and*
the collection natively, and `COLLECTORS` in `main.py` routes around
UKBinCollectionData for it. Any of the other 92 on the same platform (High
Peak, for one) can be done the same way.

The gap is address lookup, not collection data. 192 of the councils here are
keyed on a UPRN, and **there is no free national postcode → UPRN service** —
OS Places API is explicitly excluded from the OS Data Hub free credit
(£0.0282 per lookup, no free tier). So each of those councils needs its own
picker scraped from its own address form. See `app/pickers/stockport.py` for
the pattern; it is about 100 lines per council.

Until a council has a picker, the site asks the user for their UPRN and points
them at findmyaddress.co.uk.

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
  pickers/staffsmoorlands.py  picker + native collector, no browser
static/index.html       the whole front end
tools/build_registry.py regenerates councils.json from upstream
BRAND.md                brand guidelines
```

Regenerate the council registry after bumping `uk_bin_collection`:

```bash
python3 tools/build_registry.py
```

## Caveats

- Not official. Councils change their sites and scrapers break.
- Some councils return only the next collection per bin (Stockport returns
  two dates); others return a year or more. The feed shows whatever the
  council gives, from a week ago onwards.
- Bin names come from the council verbatim, so they vary a lot
  ("Wheeled Bin (180ltr)", "Domestic Waste Collection Service").

[ukbcd]: https://github.com/robbrad/UKBinCollectionData
[pio]: https://postcodes.io/
