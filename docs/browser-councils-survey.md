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

## Tried and rejected: the Netcall / Liberty Create cluster

Croydon, North Hertfordshire and Sevenoaks (`/w/webpage/`, `oncreate.app`).
**These genuinely need a browser.** Investigated 23 Sep 2026:

- The address field is a debounced jQuery typeahead. It fires on real key
  events only - synthetic `input`/`keyup`/`change` events dispatched into the
  page produce no request at all.
- The page issues a `webpage_token` and a `CSRF` var, and exposes an
  `/w/ajax?webpage_subpage_id=…&webpage_token=…` endpoint, but the submit URLs
  are signed against the session token. UKBinCollectionData's own author
  documented the same conclusion in `NorthHertfordshireDistrictCouncil.py`:
  *"No public UPRN shortcut exists - submit URLs carry an auth signature bound
  to the session-issued webpage_token."*

Replicating it would mean reconstructing the widget payload format
(`payload[PAG…][PWG…]`) and the signing, and would break whenever the council
rebuilds the page. Not worth it for three councils.

## Tried and parked: Neath Port Talbot

Plain HTTP works fine - it's an Umbraco form (`__RequestVerificationToken` +
`ufprt`), postcode → addresses → results page, all scriptable. **But the
results page has no dates on it.** It gives a collection day and a week colour
("Blue Week") and expects you to derive the calendar from the cycle. Doable,
but it's cycle logic rather than a scrape, so it's a different job.

## What the platform fingerprint does and doesn't tell you

Sharing a platform with a solved council does **not** mean a council is
solvable. Syncfusion worked because the data was sitting in the HTML as JSON.
Liberty Create shares a URL shape and nothing else useful. Judge each cluster
by whether the data is in the response, not by the vendor.

## Spike: Jadu / Firmstep (AchieveForms) - **viable**

Spiked Gloucester on 23 Sep 2026. Unlike Liberty Create, **this cluster does
not need a browser**, and the strongest evidence is that we already ship 28 of
them: 28 of the 29 UKBinCollectionData modules that use `apibroker/runLookup`
have no `web_driver` flag and are in this build today.

Reproduced Gloucester's flow in plain `httpx`, no browser:

1. `GET /service/<name>` - the page embeds `FS.FormDefinition` containing
   `form_uri` (`sandbox-publish://AF-Process-…/AF-Stage-…/definition.json`).
2. `GET /authapi/isauthenticated?uri=<double-encoded form url>&hostname=…` →
   `auth-session` id.
3. `POST /apibroker/runLookup?id=<lookupId>&sid=<sid>&app_name=AF-Renderer::Self`
   with `{"formValues": {"Section 1": {<field>: {"value": …}}}}` →
   `integration.transformed.rows_data`.

Confirmed working headlessly:

| Step | Lookup id | Input | Result |
|---|---|---|---|
| Postcode → addresses | `57fb9bf5aa4b8` | `find_postcode` | 12 addresses with UPRNs for GL2 0RR |
| UPRN → service ids | `63f72ddc8ca25` | `binUprn` | `RefuseSackId`, `RecyclingId`, `FoodId`, `GardenId` |
| Service id → dates | `645df93e1b901` | **not identified** | - |

The third step's field name wasn't found by guessing, and the form issues it
through a transport that a patched `XMLHttpRequest` didn't catch. Capturing it
is a matter of persistence, not a blocker - the first two steps prove the
transport, the session and the data are all reachable without a browser.

**But the "one module unlocks 18" hope is wrong.** The *transport* is shared;
the lookup ids, section names and field names are per-council and have to be
discovered from each council's own form. Budget roughly a couple of hours per
council, not one shared module for the cluster.

## Suggested order of attack

1. ~~Wakefield~~ - **done**.
2. ~~Whitespace / Netcall~~ - **rejected**, see above.
3. ~~Spike Jadu / Firmstep~~ - **done, and it's viable** (see above). Each of
   the 18 is its own job of a couple of hours, so do them on demand rather than
   as a batch.
4. **Headless Chrome instead.** If coverage matters more than tidiness, adding
   a browser to the deployment unlocks all 90 at once through
   UKBinCollectionData, rather than writing 90 modules. It costs a bigger
   machine (~1GB rather than 512MB) and slower lookups. For anything past the
   Firmstep cluster this is almost certainly the better trade.

## Reproducing this

The probe was ad hoc. To redo it, fetch each `web_driver` council's `url` from
UKBinCollectionData's `tests/input.json` and check the response for: a
platform fingerprint, a `<form>`, a postcode/UPRN input, a CSRF token, and
whether any collection dates appear in the HTML. Be polite - one request per
council, modest concurrency, and an identifying User-Agent.
