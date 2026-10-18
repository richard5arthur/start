#!/usr/bin/env python3
"""Email an alert when Octopus Agile electricity prices drop below a threshold.

octopriceuk.app/agile is a front end over the public Octopus Energy API, so this
script reads the same half-hourly Agile unit rates straight from that API rather
than scraping the rendered page. Uses only the Python standard library.

Configuration is read from environment variables (see README.md).
"""

import argparse
import json
import os
import smtplib
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

API_BASE = "https://api.octopus.energy/v1"
UK_TZ = ZoneInfo("Europe/London")

REGIONS = {
    "A": "Eastern England",
    "B": "East Midlands",
    "C": "London",
    "D": "Merseyside and North Wales",
    "E": "West Midlands",
    "F": "North Eastern England",
    "G": "North Western England",
    "H": "Southern England",
    "J": "South Eastern England",
    "K": "South Wales",
    "L": "South Western England",
    "M": "Yorkshire",
    "N": "Southern Scotland",
    "P": "Northern Scotland",
}


def get_json(url, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "agile-price-alert/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def find_agile_product():
    """Return the code of the current Agile import product, e.g. AGILE-24-10-01."""
    data = get_json(f"{API_BASE}/products/", {"brand": "OCTOPUS_ENERGY", "is_variable": "true"})
    agile = [
        p for p in data["results"]
        if p["code"].startswith("AGILE")
        and p.get("direction") == "IMPORT"
        and not p.get("is_business")
        and p.get("available_to") is None
    ]
    if not agile:
        raise RuntimeError("No current Agile import product found in the Octopus API")
    agile.sort(key=lambda p: p["available_from"], reverse=True)
    return agile[0]["code"]


def fetch_rates(product, region, period_from):
    tariff = f"E-1R-{product}-{region}"
    url = f"{API_BASE}/products/{product}/electricity-tariffs/{tariff}/standard-unit-rates/"
    params = {"period_from": period_from.strftime("%Y-%m-%dT%H:%M:%SZ"), "page_size": 1500}
    rates = []
    while url:
        data = get_json(url, params)
        rates.extend(data["results"])
        url, params = data.get("next"), None
    return rates


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def cheap_windows(rates, threshold):
    """Group consecutive half-hour slots priced below `threshold` p/kWh (inc VAT).

    Returns a list of windows, each a list of (start, end, price) tuples, in time order.
    """
    slots = sorted(
        (parse_time(r["valid_from"]), parse_time(r["valid_to"]), r["value_inc_vat"])
        for r in rates
        if r["value_inc_vat"] < threshold
    )
    windows = []
    for slot in slots:
        if windows and windows[-1][-1][1] == slot[0]:
            windows[-1].append(slot)
        else:
            windows.append([slot])
    return windows


def fmt(dt):
    return dt.astimezone(UK_TZ).strftime("%a %d %b %H:%M")


def build_email(windows, threshold, region):
    slot_count = sum(len(w) for w in windows)
    lowest = min(p for w in windows for _, _, p in w)
    subject = (
        f"Octopus Agile: {slot_count} slot{'s' if slot_count != 1 else ''} below "
        f"{threshold:g}p/kWh (low {lowest:.2f}p)"
    )
    lines = [
        f"Agile prices below {threshold:g}p/kWh (inc VAT), region {region} "
        f"({REGIONS.get(region, 'unknown')}). Times are UK local time.",
        "",
    ]
    for w in windows:
        prices = [p for _, _, p in w]
        lines.append(
            f"{fmt(w[0][0])} - {w[-1][1].astimezone(UK_TZ):%H:%M}: "
            f"min {min(prices):.2f}p, avg {sum(prices) / len(prices):.2f}p"
        )
        for start, end, price in w:
            note = "  (negative: you get paid)" if price < 0 else ""
            lines.append(f"    {start.astimezone(UK_TZ):%H:%M}-{end.astimezone(UK_TZ):%H:%M}  {price:6.2f}p{note}")
        lines.append("")
    lines.append("Full prices: https://www.octopriceuk.app/agile")
    return subject, "\n".join(lines)


def send_email(subject, body, to_addr):
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("ALERT_FROM", user)
    msg["To"] = to_addr
    msg.set_content(body)

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)


def load_state(path):
    try:
        with open(path) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_state(path, alerted, now):
    # Only keep slots that haven't finished yet so the file stays small.
    keep = sorted(s for s in alerted if parse_time(s) > now - timedelta(hours=1))
    with open(path, "w") as f:
        json.dump(keep, f)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print the alert instead of emailing it")
    parser.add_argument("--rates-file", help="read rates from a JSON file instead of the API (for testing)")
    args = parser.parse_args(argv)

    threshold = float(os.environ.get("PRICE_THRESHOLD", "5"))
    region = os.environ.get("AGILE_REGION", "C").upper()
    to_addr = os.environ.get("ALERT_TO", "rrwwallace@gmail.com")
    state_file = os.environ.get("STATE_FILE", "alerted_slots.json")
    if region not in REGIONS:
        sys.exit(f"AGILE_REGION must be one of {', '.join(REGIONS)} (got {region!r})")

    now = datetime.now(timezone.utc)
    if args.rates_file:
        with open(args.rates_file) as f:
            rates = json.load(f)["results"]
    else:
        product = os.environ.get("AGILE_PRODUCT") or find_agile_product()
        print(f"Using product {product}, region {region} ({REGIONS[region]})")
        # Start from the beginning of the current half-hour so the slot in progress is included.
        slot_start = now.replace(minute=0 if now.minute < 30 else 30, second=0, microsecond=0)
        rates = fetch_rates(product, region, slot_start)
    print(f"Fetched {len(rates)} half-hour prices")

    # Skip slots already emailed about on a previous run.
    alerted = set() if args.dry_run else load_state(state_file)
    fresh = [r for r in rates if r["valid_from"] not in alerted and parse_time(r["valid_to"]) > now]
    windows = cheap_windows(fresh, threshold)
    if not windows:
        print(f"No new slots below {threshold:g}p/kWh")
        return

    subject, body = build_email(windows, threshold, region)
    if args.dry_run:
        print(f"Subject: {subject}\n\n{body}")
        return

    send_email(subject, body, to_addr)
    print(f"Sent alert to {to_addr}: {subject}")
    alerted.update(start.strftime("%Y-%m-%dT%H:%M:%SZ") for w in windows for start, _, _ in w)
    save_state(state_file, alerted, now)


if __name__ == "__main__":
    main()
