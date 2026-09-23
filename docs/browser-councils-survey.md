# Which "needs a browser" councils actually need one?

Survey of the 91 councils UKBinCollectionData flags `web_driver` and this build
therefore excludes. Run 23 Sep 2026: one GET to each council's configured URL,
fingerprinting the response.

The premise is already proven - Staffordshire Moorlands and High Peak were both
flagged `web_driver` and neither needs a browser. The flag records how the
upstream scraper was *written*, not what the site *requires*.

## Platform clusters

Fingerprinted from the live page, not the module source.

| Platform | Councils | Notes |
|---|---:|---|
| Jadu / Firmstep (AchieveForms) | 18 | Biggest cluster by far. One module could unlock many. Sessions are fiddly. |
| Whitespace | 3 | `oncreate.app`, `/w/webpage/` paths. |
| Netcall / Liberty Create | 2 | Same `/w/webpage/` shape as Whitespace. |
| iTouchVision | 2 | `iapp.itouchvision.com`. |
| Syncfusion Public Dashboard | 0 | Arun fingerprinted but is a **false positive** - it only shares the `e-list-item` CSS class. Staffordshire Moorlands and High Peak were the only two. |
| Unknown / bespoke | 65 | Case by case. |

The 18 Jadu/Firmstep councils: Angus, Broxbourne, East Suffolk, Gloucester,
Hillingdon, Maidstone, Midlothian, North Devon, North East Derbyshire, North
Warwickshire, Portsmouth, Reigate and Banstead, Tendring, Three Rivers,
Waltham Forest, Windsor and Maidenhead, Wirral, Wrexham.

## Serve a real server-rendered form

16 of the 91 return a genuine `<form>` with a postcode/UPRN input or a CSRF
token, and are not an SPA shell:

Northumberland, Broadland, Wokingham, Windsor and Maidenhead, Uttlesford,
Rushcliffe, Peterborough, Mid Ulster, Mid Suffolk, Redbridge, East Riding,
Croydon, Bexley, Ashford, Argyll and Bute, Angus.

**A form is not a guarantee.** Windsor and Maidenhead returns 200 with a form
but zero dates in the HTML - it fetches them over XHR afterwards. Always check
for actual dates before committing to a council.

## Confirmed working without a browser

| Council | How | Status |
|---|---|---|
| **Wakefield** | search `/pick-your-address`, follow the link it gives back | **Done** - `app/pickers/wakefield.py` |

Wakefield had a sting in the tail: `?uprn=` **alone returns the page with no
collections on it**. Only the complete parameter set the address search hands
back (uprn, address, usrn, easting, northing) produces dates, so the link must
be followed exactly as given.

## Suggested order of attack

1. ~~Wakefield~~ - **done**.
2. **Whitespace (3) + Netcall (2)** - five councils across two similar
   `/w/webpage/` platforms; likely one small module each, same shape as
   `syncfusion.py`.
3. **Jadu / Firmstep (18)** - the big prize, and the most work. AchieveForms
   posts through a session-bound JSON API; worth a spike on one council
   (Tendring or Gloucester, both on `achieveservice.com`) before committing.
4. **The remaining bespoke ones** - only worth it for a council someone
   actually asks for.

## Reproducing this

The probe was ad hoc. To redo it, fetch each `web_driver` council's `url` from
UKBinCollectionData's `tests/input.json` and check the response for: a
platform fingerprint, a `<form>`, a postcode/UPRN input, a CSRF token, and
whether any collection dates appear in the HTML. Be polite - one request per
council, modest concurrency, and an identifying User-Agent.
