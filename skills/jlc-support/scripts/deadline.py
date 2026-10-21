"""Turn "received at X, confirm within N hours" into an absolute deadline with time zones.

Usage:
  python -I deadline.py --received "2026-09-29 16:02" --tz +08:00 --hours 72
  python -I deadline.py --received 2026-09-29T16:02+08:00 --hours 48 --show-tz=-07:00

--received   when the confirmation mail arrived. Either include an offset
             (2026-09-29T16:02+08:00) or give --tz.
--tz         offset of --received when it has none: +08:00, -0700, UTC, or an IANA
             name such as Asia/Taipei (IANA names need the OS or the tzdata package).
--hours      the deadline stated in the mail (48, 72, 0.5 ...).
--show-tz    extra zones to print the deadline in (repeatable). UTC is always shown.
             Write negative offsets as --show-tz=-07:00 so they are not read as options.
--now        override the current time for "remaining" (same formats as --received).
--json       also write the result as JSON to this path.

Prints the received time, the deadline in the received zone, in UTC and in every
--show-tz zone (with weekday), and the time remaining. Write the deadline line into
WORKLOG and tell the user. The script never contacts anything and changes no files
except --json.

Exit codes: 0 deadline in the future, 1 deadline already passed, 2 input error.
Standard library only.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone

OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")


def parse_zone(text):
    text = text.strip()
    if text.upper() in ("UTC", "Z", "GMT"):
        return timezone.utc
    m = OFFSET_RE.match(text)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        return timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(text)
    except Exception as e:  # ZoneInfoNotFoundError, missing tzdata on Windows, bad key
        raise ValueError(f"unknown time zone {text!r} ({type(e).__name__}); "
                         "use an offset such as +08:00") from None


def parse_time(text, zone=None):
    value = datetime.fromisoformat(text.strip().replace(" ", "T", 1))
    if value.tzinfo is None:
        if zone is None:
            raise ValueError(f"{text!r} has no offset; add one or pass --tz")
        value = value.replace(tzinfo=zone)
    return value


def label(dt):
    off = dt.strftime("%z")
    zone = "UTC" if off == "+0000" else f"UTC{off[:3]}:{off[3:]}"
    return f"{dt:%Y-%m-%d %H:%M} {dt:%a} ({zone})"


def span(delta):
    minutes = int(abs(delta).total_seconds() // 60)
    d, rest = divmod(minutes, 24 * 60)
    h, m = divmod(rest, 60)
    return f"{d} d {h} h {m} min" if d else f"{h} h {m} min"


def compute(received, hours, now, show_zones):
    deadline = received + timedelta(hours=hours)
    remaining = deadline - now
    zones = [received.tzinfo, timezone.utc] + [z for z in show_zones]
    shown, seen = [], set()
    for z in zones:
        text = label(deadline.astimezone(z))
        if text not in seen:
            seen.add(text)
            shown.append(text)
    return {
        "received": label(received),
        "hours": hours,
        "deadline": shown,
        "deadline_utc_iso": deadline.astimezone(timezone.utc).isoformat(),
        "now": label(now.astimezone(received.tzinfo)),
        "expired": remaining.total_seconds() <= 0,
        "remaining": span(remaining),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Absolute deadline for a JLC confirmation mail (read-only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 in the future, 1 already passed, 2 input error.\n"
               'Example:\n  python -I deadline.py --received "2026-09-29 16:02" --tz +08:00 --hours 72')
    ap.add_argument("--received", required=True)
    ap.add_argument("--tz")
    ap.add_argument("--hours", required=True, type=float)
    ap.add_argument("--show-tz", action="append", default=[])
    ap.add_argument("--now")
    ap.add_argument("--json")
    args = ap.parse_args(argv)

    try:
        zone = parse_zone(args.tz) if args.tz else None
        received = parse_time(args.received, zone)
        now = parse_time(args.now, received.tzinfo) if args.now else datetime.now(timezone.utc)
        extra = [parse_zone(z) for z in args.show_tz]
        if args.hours <= 0:
            raise ValueError("--hours must be positive")
    except ValueError as e:
        print(f"ERROR: {e}")
        return 2

    result = compute(received, args.hours, now, extra)
    print(f"received:  {result['received']}")
    for i, text in enumerate(result["deadline"]):
        print(f"{'deadline:' if i == 0 else '':10} {text}")
    state = "EXPIRED" if result["expired"] else "remaining"
    print(f"{state + ':':10} {result['remaining']} (as of {result['now']})")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
    return 1 if result["expired"] else 0


if __name__ == "__main__":
    sys.exit(main())
