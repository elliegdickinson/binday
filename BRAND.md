# Bin Day - brand guidelines

> "Everyday things work better when they're simple."

**Your bins. Your calendar. Sorted.**

## Tone of voice

Friendly, clear, slightly cheeky, never corporate. Useful first, fun second.

Write like a helpful neighbour, not a council leaflet and not a startup.
Short sentences. Contractions. The joke never gets in the way of the answer.

| Say | Don't say |
|---|---|
| What bin is it this week? | Check your waste collection schedule |
| Pop in your postcode and we'll find your next collections. | Enter your postcode to initiate a lookup |
| No account. No faff. | Sign up free in seconds |
| Put it out tonight. | Collection is scheduled for tomorrow morning |
| That's the bins sorted. You may now return to more interesting things. | Success! Your calendar has been updated. |
| We can't do Coventry yet. | Council not currently supported |

Never exaggerate the data. It is scraped from councils and can be wrong - say
so plainly and point at the council.

## Colour

| Token | Hex | Use |
|---|---|---|
| Bin Day Green | `#C8FF38` | Highlight blocks, the strapline marker, the calendar CTA panel. Never for body text. |
| Electric Blue | `#456CFF` | Primary buttons and links. |
| Cream | `#F7F4EA` | Page background. |
| Ink | `#161616` | Headings and body text. |
| Mid Grey | `#6B6B6B` | Secondary text, captions. |
| White | `#FFFFFF` | Cards. |

Bin Day Green is a highlight, not a background for long text - ink on lime at
small sizes is tiring. Use it in blocks, behind short lines.

### Waste categories

| Category | Hex |
|---|---|
| General waste | `#4D4D4D` |
| Recycling | `#456CFF` |
| Garden waste | `#2F7D32` |
| Food waste | `#F57C1F` |
| Paper / card | `#A855E8` |

**Extension for real council data.** Councils mostly name bins by colour
("Blue bin", "Brown bin"), and that is how people think about them - a purple
tile labelled "Blue bin" is nonsense. So:

1. If the bin's name contains a colour, the tile takes that literal colour.
2. Otherwise the tile takes its waste-category colour from the table above.

The icon always follows the waste category, whichever rule set the colour.

Black bins lift to `#4D4D4D` rather than true black, so the tile reads as an
object rather than a hole.

## Typography

- **Headings and the wordmark:** Space Grotesk, 700. Tight tracking
  (`-0.03em`) at large sizes. Headings are big and confident.
- **Body and UI:** Atkinson Hyperlegible, 400/700. Chosen for legibility -
  this is a utility, and people read it in a hurry.
- **Annotations:** Caveat, for the occasional handwritten aside. One per
  screen at most, never carrying information you can't afford to miss.

## Wordmark

`BIN DAY` set in Space Grotesk 700, all caps, tight, with a small bin glyph
after the Y. Strapline sits beneath on a Bin Day Green block, with "Sorted."
underlined.

Variations: ink on cream, ink on Bin Day Green, white on ink. Do not restyle
the letterforms, stretch it, or add a gradient.

## Layout

Cream page, white cards, soft corners (14px), hairline borders. Generous
space. One question per screen. Results are cards in a row on desktop and a
stack on mobile, each showing icon, bin name, relative date ("Tomorrow",
"In 8 days") and, the day before collection, "Put it out tonight."

**Bins go out the night before.** So "Put it out tonight" belongs on the day
*before* a collection and nowhere else - on collection day itself it is a day
late, and the card says "Should already be out." instead. Getting this wrong
tells people to miss their collection.

Must work at 360px wide.

## Third-party widgets

The Ko-fi support button is the one piece of third-party UI on the page. It
takes Electric Blue rather than Ko-fi's default `#00b9fe`, which sits badly
next to the lime. Any future widget does the same: brand colours, or it doesn't
go on.

It floats bottom-left over the content, as those widgets do. Keep the page's
bottom padding generous so it doesn't crowd the last card.

## Avoid

- Stock photos of smiling people recycling.
- Gradients, glassmorphism, heavy shadows.
- Corporate hedging ("we aim to provide").
- Implying the data is official.
