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
postcode ──► /api/addresses ──► pick ──► /api/resolve ──► /feed/<council>.ics
                                                              │
                                        calendar app re-fetches every ~12h
```

## Coverage, honestly

| | Councils |
|---|---|
| In this build (no headless browser needed) | 259 |
| **Work from a postcode alone** | **51** |
| Need you to supply a UPRN yourself | 192 |
| Not supported: lookup needs a property id we can't derive | 16 |
| Excluded for now (need headless Chrome) | 93 |

Of the 51, one (Stockport) gets there via a postcode → address picker; the
rest take a postcode and house number directly.

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
  main.py               FastAPI: councils, addresses, resolve, feed
  ics.py                bin list -> iCalendar
  data/councils.json    generated from UKBinCollectionData's input.json
  pickers/stockport.py  postcode -> address -> uprn
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
