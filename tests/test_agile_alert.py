import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import agile_alert  # noqa: E402


def slot(start, price):
    end = start + timedelta(minutes=30)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"valid_from": iso(start), "valid_to": iso(end), "value_inc_vat": price}


BASE = datetime(2030, 1, 1, 0, 0, tzinfo=timezone.utc)
RATES = [slot(BASE + timedelta(minutes=30 * i), p)
         for i, p in enumerate([12.0, 4.9, 3.1, -0.5, 6.0, 4.99, 5.0, 2.0])]


class CheapWindowsTest(unittest.TestCase):
    def test_groups_consecutive_slots_below_threshold(self):
        windows = agile_alert.cheap_windows(RATES, 5)
        self.assertEqual([[p for _, _, p in w] for w in windows], [[4.9, 3.1, -0.5], [4.99], [2.0]])

    def test_exactly_threshold_is_not_cheap(self):
        windows = agile_alert.cheap_windows([slot(BASE, 5.0)], 5)
        self.assertEqual(windows, [])

    def test_email_mentions_lowest_price_and_negative(self):
        subject, body = agile_alert.build_email(agile_alert.cheap_windows(RATES, 5), 5, "C")
        self.assertIn("5 slots below 5p/kWh", subject)
        self.assertIn("low -0.50p", subject)
        self.assertIn("you get paid", body)
        self.assertIn("London", body)


class MainTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()
        self.rates_file = os.path.join(self.dir, "rates.json")
        self.state_file = os.path.join(self.dir, "state.json")
        with open(self.rates_file, "w") as f:
            json.dump({"results": RATES}, f)
        self.env = mock.patch.dict(os.environ, {"STATE_FILE": self.state_file,
                                                "SMTP_USER": "u", "SMTP_PASSWORD": "p"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_does_not_alert_twice_for_same_slots(self):
        with mock.patch.object(agile_alert, "send_email") as send:
            agile_alert.main(["--rates-file", self.rates_file])
            agile_alert.main(["--rates-file", self.rates_file])
        self.assertEqual(send.call_count, 1)
        with open(self.state_file) as f:
            self.assertEqual(len(json.load(f)), 5)


if __name__ == "__main__":
    unittest.main()
