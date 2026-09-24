# Brand decisions specific to this build

The brand is defined by [`CLAUDE.md`](../CLAUDE.md), [`BRAND_GUIDELINES.md`](BRAND_GUIDELINES.md)
and [`tokens/brand-tokens.json`](../tokens/brand-tokens.json). Those are the
source of truth.

This file records only the decisions the guidelines don't cover, and the one
place this build deliberately departs from them.

## "Put it out tonight" is a one-day window

Bins go out the night **before** collection, so that line belongs on the day
before and nowhere else. On collection day it is a day late and would make
someone miss their collection; the card says "Should already be out." instead.

This was shipped wrong once. It is the only copy on the site that can cost the
reader something, so treat it as a correctness rule, not a tone one.

## Bin tiles: the council's colour wins over the category colour

The guidelines give five category colours (general, recycling, garden, food,
paper/card) and say never to rely on colour alone.

But councils name bins by colour - Stockport has a "Blue bin" for paper and
card. Rendering that tile in the paper/card purple would produce a purple tile
labelled "Blue bin", which is nonsense to the person holding the bin.

So: **if a bin's name contains a colour, the tile takes that colour.**
Otherwise it takes its category colour from the kit. The icon always follows
the waste category, and the written label is always present, so the
"never colour alone" rule still holds.

Brown has no kit equivalent and uses `#8A5A2B`.

To revert to strict category colours, drop `BIN_COLOURS` from
`static/index.html` and always resolve through `BY_WASTE`.

## Logo files

The kit's logo PNGs carry roughly 30% padding, and it is asymmetric - sizing by
height would misalign the mark in the navigation. `bin-day-logo-web.png` and
`bin-day-mark-web.png` are trimmed, downscaled, colour-quantised derivatives of
`bin-day-logo-transparent.png` for on-page use. Nothing is recoloured,
distorted or restyled; regenerate them from the transparent master if it
changes.

Minimum heights on the page: 48px in navigation, 64px in the footer, 40px below
560px wide. Below that the stacked two-line lockup stops being readable.

## The kit's bin mark has a stray fragment

`assets/logo/bin-day-mark.png` (and the 192/512 variants) carry a small black
wedge in the upper left. It is a leftover piece of the **Y from DAY**, kept
when the mark was cropped out of the lockup. Invisible at favicon size,
obvious at home-screen size.

`bin-day-mark-clean.png` is cut from `bin-day-logo-transparent.png` with the Y
masked off, and the favicon and app icons derive from it. **Worth fixing in the
master** - once the kit's mark is clean, delete the derivative and regenerate
from it.

## Icons

- `favicon.ico` - 16/32/48, transparent, served at the root because that is
  what browsers, bookmarks and link previews request whether or not the page
  links to one.
- `icon-180/192/512.png` - home-screen icons on **cream**, not transparent: iOS
  puts a black plate behind a transparent icon.
- `site.webmanifest` makes it installable, which suits something people check
  weekly from a phone.

## Graphic language

Personality comes from scale, type and a small fixed vocabulary - not decoration.

- **Hero bin** is inline SVG (not the PNG), so the lid can animate and it stays
  crisp. It fills its column and overhangs by a **fixed 12px**: the gutter is
  24px, so the bleed can never scroll the page sideways. An earlier version used
  a percentage overhang and a ray that sat outside the viewBox, which overflowed
  at 1024px.
- **BrandRays** is one `<symbol id="brand-rays">`, referenced with `<use>`. Its
  stroke weight is a custom property (`--ray-w`) so the same shape works at hero
  scale and at 24px inline. **Budget for the page is three uses**: the hero mark,
  the *first* urgent collection, and the success state. Several urgent bins do
  not each get rays.
- **The sticker** is a night-before reminder only. On collection day it is not a
  reminder, so that case is quiet text - a playful sticker saying "should
  already be out" would be the wrong tone as well as the wrong information.
- **Collection icons** are one family: chunky flat vector, ink outline,
  category-colour fill, drawn like the logo. Always beside a written label.
- **`SORTED.`** lives at the very bottom, cropped by the page edge at 9% stroke,
  and sits clear of the footer credit rather than behind it. One instance only.
- **The hero bin** is oversized and crops against the hero edge. The section uses
  `overflow-x: clip` so the crop can never scroll the page sideways - a fixed
  margin alone was not enough once the bin got big.
- **Timing type** is sized with container queries (`18cqi`), not viewport units:
  "TOMORROW" is eight characters and overflowed a four-up grid at a fixed 48px.
- **The lime panel pattern** is a calendar grid at ~3%. If it reads as dots, it
  is too strong.

All motion sits inside `@media (prefers-reduced-motion: no-preference)`, and
`celebrate()` checks the query itself before creating anything.

## Calendar buttons carry other people's logos, not their buttons

The calendar panel offers Apple Calendar, Google Calendar and Outlook by name.
The marks are Simple Icons' official paths, inlined rather than installed: this
page has no package manager and one job, and a CDN script for three icons would
be a third-party request on every load.

The provider's colour lives **in the mark and nowhere else**. Cream or white
background, ink text, ink border, 12px radius, 56px high. A lime Bin Day panel
holding three brand-coloured provider buttons reads as someone else's UI pasted
into ours, and the row stops being scannable.

Order follows the device, and nothing is ever hidden - a wrong guess costs a
glance, not a dead end. `navigator.userAgentData.platform` is the signal where
it exists, the UA string only where it doesn't. Anything we cannot place keeps
the default order and shows no "Recommended" badge, because a confident label
on a guess is worse than no label.

## Only claim the thing that actually happened

Only the Apple button can be verified: `webcal:` hands the feed to the OS and
the window losing focus is the proof. That path keeps "That's the bins sorted."

Google and Outlook open a tab somewhere else. We cannot see whether the person
finished, so they get "opened in a new tab - finish adding Bin Day there".
**Copying the link no longer shows the success state either** - a copied link is
not a subscription, and saying it is trains people to ignore the message.

Facebook, Instagram and Messenger open links in their own in-app browser, which
blocks the `webcal:` handover. That failure names itself and says to open the
page in Safari or Chrome, because "it didn't work" sends people away.

## Councils that refuse automated lookups

Some councils put a bot challenge in front of their bin pages - Sunderland
returns `cf-mitigated: challenge` from Cloudflare. That is a door someone chose
to close, not a scraper bug and not something to work around.

`BLOCKED` in `app/main.py` lists them with what to tell the reader, and the
council is marked "Not supported yet" with a link to its own page, so nobody
fills a form that cannot win. A live 403 from any other council gets the same
words instead of a raw error. Re-check occasionally: a council can turn this off
as easily as it turned it on.

## Third-party widgets

The Ko-fi button is the only third-party UI. It is recoloured to Electric Blue
rather than Ko-fi's default `#00b9fe`, which fights the lime. Any future widget
does the same: brand colours, or it doesn't go on.

It floats bottom-left over the content, so the page keeps generous bottom
padding.
