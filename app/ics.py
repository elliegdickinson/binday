"""Turn a UKBinCollectionData bin list into a subscribable iCalendar feed."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

PRODID = "-//binday//UK bin collections//EN"


def fold(line: str) -> str:
    """RFC 5545 content lines must not exceed 75 octets."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    chunks, rest = [raw[:75]], raw[75:]
    while rest:
        chunks.append(b" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(c.decode("utf-8", "ignore") for c in chunks)


def esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", r"\;")
                .replace(",", r"\,").replace("\n", r"\n"))


def _parse(value: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def build(bins: list[dict], *, place: str, council: str,
          council_url: str = "", reminder_hour: int = 19) -> str:
    """bins is UKBinCollectionData's output: [{type, collectionDate}, ...]

    One all-day event per collection day, listing every bin due that day, with
    an alarm the evening before. Bins with an unparseable date are skipped
    rather than guessed at.
    """
    # Some councils hand back years of history (Hackney starts in 2024). Nobody
    # wants that in their calendar, so keep only the recent past and forward.
    cutoff = date.today() - timedelta(days=7)

    days: dict[date, list[str]] = defaultdict(list)
    for item in bins:
        when = _parse(str(item.get("collectionDate", "")).strip())
        kind = str(item.get("type", "")).strip()
        if when and when >= cutoff and kind and kind not in days[when]:
            days[when].append(kind)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trigger = f"-PT{24 - reminder_hour}H"
    ident = hashlib.sha1(f"{council}|{place}".encode()).hexdigest()[:10]

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc('Bin collections - ' + place)}",
        f"X-WR-CALDESC:{esc('Bin collection days for ' + place + ' (' + council + ')')}",
        "X-PUBLISHED-TTL:PT12H",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
    ]

    for when in sorted(days):
        kinds = days[when]
        summary = "Bins out: " + " + ".join(kinds)
        detail = "\n".join(kinds)
        if council_url:
            detail += f"\n\nSource: {council_url}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{when:%Y%m%d}-{ident}@binday",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{when:%Y%m%d}",
            f"DTEND;VALUE=DATE:{when + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{esc(summary)}",
            f"DESCRIPTION:{esc(detail)}",
            f"LOCATION:{esc(place)}",
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"TRIGGER:{trigger}",
            f"DESCRIPTION:{esc(summary + ' tonight')}",
            "END:VALARM",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"
