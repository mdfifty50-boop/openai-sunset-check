import json
import os
import subprocess
import sys
import unittest
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIX = os.path.join(HERE, "fixtures")
sys.path.insert(0, ROOT)
import check  # noqa: E402

TODAY = dt.date(2026, 11, 14)


def scan(name):
    return check.scan_path(os.path.join(FIX, name), TODAY)


def refs(rows):
    return sorted((r["matchedAs"], r["shutdownDate"]) for r in rows)


class Fixtures(unittest.TestCase):
    def test_python_o3_and_tts(self):
        rows = scan("bot_o3_tts.py")
        self.assertEqual(refs(rows), [("o3", "2026-12-11"), ("tts-1", "2027-01-06")])
        self.assertEqual({r["line"] for r in rows}, {6, 10})
        o3 = [r for r in rows if r["matchedAs"] == "o3"][0]
        self.assertEqual(o3["replacement"], "gpt-6.1-sol")
        self.assertEqual(o3["daysLeft"], 27)

    def test_clean_file_has_no_findings(self):
        self.assertEqual(scan("clean.py"), [])

    def test_n8n_export(self):
        rows = scan("n8n_gpt4o_mini.json")
        self.assertEqual(len(rows), 1)  # cachedResultName duplicate is ignored
        r = rows[0]
        self.assertEqual((r["matchedAs"], r["shutdownDate"], r["replacement"]), ("gpt-4o-mini", "2027-01-14", "gpt-6-luna"))
        self.assertIn("OpenAI Chat Model", r["node"])
        self.assertEqual(r["jsonPath"], "nodes[1].parameters.model.value")

    def test_make_export(self):
        rows = scan("make_scenario.json")
        self.assertEqual(refs(rows), [("gpt-4.1-mini", "2027-01-14"), ("whisper-1", "2027-02-26")])
        self.assertTrue(all(r["node"].startswith("#") for r in rows))

    def test_yaml_finetune_prompt_and_image(self):
        rows = scan("config.yaml")
        got = refs(rows)
        self.assertIn(("gpt-4o-mini-2024-07-18", "2027-01-14"), got)
        self.assertIn(("/v1/prompts (reusable prompt object)", "2026-11-30"), got)
        self.assertIn(("gpt-image-2", "2027-02-10"), got)
        ft = [r for r in rows if r["kind"] == "fine-tune"][0]
        self.assertIn("does not support fine-tuning", ft["note"])

    def test_endpoints(self):
        got = refs(scan("endpoints.js"))
        self.assertIn(("/v1/audio/translations", "2027-02-26"), got)
        self.assertIn(("Self-serve fine-tuning job creation", "2027-01-06"), got)
        self.assertIn(("gpt-4.1", "2027-01-14"), got)

    def test_no_false_positive_on_new_models(self):
        rows = check.scan_text('m = "gpt-6-luna"; n = "gpt-6.1-sol"; p = "gpt-5.6-terra-2"', "x.py", TODAY)[0]
        self.assertEqual(rows, [])


class Table(unittest.TestCase):
    def test_key_dates(self):
        expect = {"gpt-5": "2026-12-11", "o3-pro": "2026-12-11", "tts-1": "2027-01-06", "gpt-4o-mini-tts": "2027-01-06",
                  "gpt-4o": "2027-01-14", "gpt-4.1": "2027-01-14", "gpt-realtime": "2027-01-20",
                  "gpt-image-2": "2027-02-10", "whisper-1": "2027-02-26", "gpt-4o-transcribe": "2027-02-26",
                  "gpt-5.1": "2027-04-01", "gpt-5.3-codex": "2027-04-01", "gpt-5.4-nano": "2027-04-01"}
        for m, d in expect.items():
            self.assertEqual(check.MODELS[m]["shutdownDate"], d, m)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(ROOT, "check.py"), *args, "--today", "2026-11-14"],
                              capture_output=True, text=True)

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(os.path.join(FIX, "clean.py")).returncode, 0)
        self.assertEqual(self.run_cli(FIX).returncode, 1)
        self.assertEqual(self.run_cli(FIX, "--no-fail").returncode, 0)
        # nearest fixture deadline is 16 days away (/v1/prompts on 2026-11-30)
        self.assertEqual(self.run_cli(FIX, "--fail-within", "10").returncode, 0)
        self.assertEqual(self.run_cli(FIX, "--fail-within", "30").returncode, 1)

    def test_json_output(self):
        out = self.run_cli(FIX, "--json", "--no-fail")
        data = json.loads(out.stdout)
        self.assertGreaterEqual(len(data["findings"]), 10)
        self.assertEqual(data["tableVerified"], "2026-11-14")


if __name__ == "__main__":
    unittest.main()
