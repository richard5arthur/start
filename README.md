# Octopus Agile price alert

Checks Octopus Agile electricity prices (the same data shown on
[octopriceuk.app/agile](https://www.octopriceuk.app/agile)) and emails
rrwwallace@gmail.com when any half-hour slot is **below 5p/kWh** (inc VAT).

Prices come straight from the public Octopus Energy API, which is the data source
behind octopriceuk.app. That's more reliable than scraping the page, which is
rendered in the browser with JavaScript. The current Agile product is found
automatically, so nothing breaks when Octopus releases a new Agile version.

Each email groups back-to-back cheap slots into windows, shows times in UK local
time, and flags negative prices (you get paid to use power). Slots already emailed
about are remembered, so you aren't sent the same slot twice.

## Setup (runs free on GitHub Actions)

1. **Create a Gmail app password**: Google Account → Security → 2-Step Verification
   → App passwords. (Your normal Gmail password won't work.)
2. In this repo on GitHub go to **Settings → Secrets and variables → Actions** and add:
   - Secret `SMTP_USER`: your Gmail address, e.g. `rrwwallace@gmail.com`
   - Secret `SMTP_PASSWORD`: the 16-character app password
   - Variable `AGILE_REGION` (optional, default `C` = London): your region letter, below
   - Variable `PRICE_THRESHOLD` (optional, default `5`): the alert threshold in p/kWh
3. Open **Actions → Agile price alert → Run workflow** to test it straight away.

After that it runs every hour by itself. Note: GitHub pauses scheduled workflows
after 60 days without any commits to the repo. It emails you when it does this, and
you can turn it back on from the Actions tab.

### Region letters

| Letter | Region | Letter | Region |
|---|---|---|---|
| A | Eastern England | H | Southern England |
| B | East Midlands | J | South Eastern England |
| C | London | K | South Wales |
| D | Merseyside and North Wales | L | South Western England |
| E | West Midlands | M | Yorkshire |
| F | North Eastern England | N | Southern Scotland |
| G | North Western England | P | Northern Scotland |

You can find your region by putting your postcode into octopriceuk.app.

## Running it on your own computer

Python 3.9+ only. No packages to install.

```sh
export SMTP_USER=rrwwallace@gmail.com SMTP_PASSWORD='your app password' AGILE_REGION=C
python3 agile_alert.py --dry-run   # print what would be sent
python3 agile_alert.py             # send the email
```

To run it hourly, add a cron entry such as `7 * * * * cd /path/to/repo && python3 agile_alert.py`.

All the settings: `PRICE_THRESHOLD` (default `5`), `AGILE_REGION` (default `C`),
`ALERT_TO` (default `rrwwallace@gmail.com`), `SMTP_HOST`/`SMTP_PORT`
(default Gmail, `smtp.gmail.com:465`), `AGILE_PRODUCT` (to pin a specific
Agile product code), `STATE_FILE` (default `alerted_slots.json`).

## Tests

```sh
python3 -m unittest discover -s tests
```
