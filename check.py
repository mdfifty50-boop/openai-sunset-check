#!/usr/bin/env python3
"""openai-sunset-check: find retiring OpenAI models and endpoints in a codebase.

Zero dependencies (Python 3 standard library only). Usage: python check.py <path> [<path> ...]
Deprecation table sourced from https://platform.openai.com/docs/deprecations.
MIT License.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

SOURCE = "https://platform.openai.com/docs/deprecations"
TABLE_VERIFIED = "2026-11-14"

IMG = "gpt-image-2.6-sunburst or gpt-image-2.6-flare"
TRANSCRIBE = "gpt-live-transcribe or gpt-transcribe"
SOL_PRO = "gpt-6.1-sol (reasoning.mode: pro) in the Responses API"

# (shutdown date, [model ids], replacement, note)
_MODEL_ROWS = [
    # ---- upcoming ----
    ("2026-12-01", ["gpt-image-1-mini", "gpt-image-1.5", "gpt-image-1.5-2025-12-16", "chatgpt-image-latest"], IMG, ""),
    ("2026-12-11", ["gpt-5", "gpt-5-2025-08-07"], "gpt-6.1-sol", ""),
    ("2026-12-11", ["gpt-5-mini", "gpt-5-mini-2025-08-07"], "gpt-6.1-terra", ""),
    ("2026-12-11", ["gpt-5-nano", "gpt-5-nano-2025-08-07"], "gpt-6-luna", ""),
    ("2026-12-11", ["gpt-5-pro", "gpt-5-pro-2025-10-06"], SOL_PRO, ""),
    ("2026-12-11", ["o3", "o3-2025-04-16"], "gpt-6.1-sol", ""),
    ("2026-12-11", ["o3-pro", "o3-pro-2025-06-10"], SOL_PRO, ""),
    ("2027-01-06", ["tts-1", "tts-1-hd", "gpt-4o-mini-tts", "gpt-4o-mini-tts-2025-03-20", "gpt-4o-mini-tts-2025-12-15"], "gpt-realtime-2.1-mini", ""),
    ("2027-01-14", ["gpt-4o-2024-08-06", "gpt-4o-2024-11-20", "gpt-4o-mini-2024-07-18", "gpt-4.1-2025-04-14", "gpt-4.1-mini-2025-04-14"], "gpt-6-luna", ""),
    ("2027-01-14", ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"], "gpt-6-luna",
     "Bare alias: it resolves to a dated snapshot that shuts down on this date, so the call fails even though no date appears in your config."),
    ("2027-01-20", ["gpt-realtime", "gpt-realtime-2025-08-28", "gpt-4o-realtime"], "gpt-realtime-2.1", ""),
    ("2027-01-20", ["gpt-audio", "gpt-audio-2025-08-28", "gpt-4o-audio", "gpt-audio-mini", "gpt-audio-mini-2025-12-15", "gpt-4o-mini-audio"], "gpt-audio-1.5", ""),
    ("2027-01-20", ["gpt-realtime-mini", "gpt-realtime-mini-2025-12-15", "gpt-4o-mini-realtime"], "gpt-realtime-2.1-mini", ""),
    ("2027-01-20", ["gpt-4o-mini-transcribe-2025-03-20"], "gpt-4o-mini-transcribe-2025-12-15",
     "The listed replacement itself shuts down on 2027-02-26; go straight to gpt-live-transcribe or gpt-transcribe."),
    ("2027-02-01", ["gpt-5.5-cyber-preview"], "The most capable cyber model available to you", ""),
    ("2027-02-10", ["gpt-image-2", "gpt-image-2-2026-04-21"], IMG, ""),
    ("2027-02-26", ["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe", "gpt-4o-mini-transcribe-2025-12-15", "gpt-4o-transcribe-diarize"], TRANSCRIBE, ""),
    ("2027-04-01", ["gpt-5.3-codex", "gpt-5.1", "gpt-5.1-2025-11-13"], "gpt-6-sol", ""),
    ("2027-04-01", ["gpt-5.4-nano", "gpt-5.4-nano-2026-03-17"], "gpt-6-luna", ""),
    # ---- already shut down (calls fail today) ----
    ("2026-10-23", ["gpt-3.5-turbo", "gpt-3.5-turbo-0125", "gpt-3.5-turbo-completions"], "gpt-5.6-terra", ""),
    ("2026-10-23", ["gpt-4", "gpt-4-0613", "gpt-4-0613-completions", "gpt-4-completions", "gpt-4-1106-preview",
                    "gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4-turbo-completions", "gpt-4o-2024-05-13",
                    "o1", "o1-2024-12-17", "o3-mini", "o3-mini-2025-01-31"], "gpt-5.6-sol", ""),
    ("2026-10-23", ["o1-pro", "o1-pro-2025-03-19"], "gpt-5.6-sol (reasoning.mode: pro)", ""),
    ("2026-10-23", ["gpt-4.1-nano", "gpt-4.1-nano-2025-04-14"], "gpt-5.6-luna", ""),
    ("2026-10-23", ["gpt-image-1"], IMG, "Listed replacement was gpt-image-2.5-*; current recommendation shown."),
    ("2026-10-23", ["o4-mini", "o4-mini-2025-04-16"], "gpt-5.6-terra", ""),
    ("2026-09-28", ["gpt-3.5-turbo-instruct", "babbage-002", "davinci-002", "gpt-3.5-turbo-1106"], "gpt-5.6-terra", ""),
    ("2026-09-24", ["sora-2", "sora-2-pro", "sora-2-2025-10-06", "sora-2-2025-12-08", "sora-2-pro-2025-10-06"], "No one-to-one replacement", ""),
    ("2026-08-10", ["gpt-5.2-chat-latest", "gpt-5.3-chat-latest"], "gpt-5.6-sol", ""),
    ("2026-07-23", ["gpt-5-chat-latest", "gpt-5-codex", "gpt-5.1-chat-latest", "gpt-5.1-codex", "gpt-5.1-codex-max", "gpt-5.2-codex",
                    "o3-deep-research", "o3-deep-research-2025-06-26", "o4-mini-deep-research", "o4-mini-deep-research-2025-06-26"], "gpt-5.6-sol", ""),
    ("2026-07-23", ["gpt-5.1-codex-mini", "computer-use-preview", "computer-use-preview-2025-03-11",
                    "gpt-4o-mini-search-preview", "gpt-4o-mini-search-preview-2025-03-11",
                    "gpt-4o-search-preview", "gpt-4o-search-preview-2025-03-11"], "gpt-5.6-terra", ""),
    ("2026-07-23", ["gpt-audio-mini-2025-10-06"], "gpt-audio-1.5", ""),
    ("2026-07-23", ["gpt-realtime-mini-2025-10-06"], "gpt-realtime-2.1-mini", ""),
    ("2026-05-12", ["dall-e-2", "dall-e-3"], IMG, "Listed replacements (gpt-image-1/2) are also retiring; current recommendation shown."),
    ("2026-05-07", ["gpt-4o-realtime-preview", "gpt-4o-realtime-preview-2025-06-03", "gpt-4o-realtime-preview-2024-12-17",
                    "gpt-4o-mini-realtime-preview"], "gpt-realtime-2.1", ""),
    ("2026-05-07", ["gpt-4o-audio-preview", "gpt-4o-mini-audio-preview"], "gpt-audio-1.5", ""),
    ("2026-02-17", ["chatgpt-4o-latest"], "gpt-5.6-sol", "Listed replacement gpt-5.1-chat-latest is also shut down."),
]

MODELS = {}
for date, ids, repl, note in _MODEL_ROWS:
    for mid in ids:
        MODELS[mid] = {"shutdownDate": date, "replacement": repl, "note": note}

# Candidate model tokens: optional ft: prefix, a known family prefix, then id chars.
MODEL_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.\-])(ft:)?((?:gpt|chatgpt|o[134]|tts|whisper|dall-e|sora|computer-use|babbage|davinci)(?:-[A-Za-z0-9._]+)*)"
    r"((?::[A-Za-z0-9._\-]*)*)(?![A-Za-z0-9_\-])")

# Features / endpoints: (regex, label, date, replacement, note, flags)
FEATURES = [
    (r"/v1/prompts\b|\bprompts\.(?:create|retrieve|update|list|delete)\s*\(|\bpmpt_[A-Za-z0-9]{8,}",
     "/v1/prompts (reusable prompt object)", "2026-11-30",
     "Move the prompt content into your application code (OpenAI migration guide: /api/docs/guides/prompting/migrate-from-prompt-object)", ""),
    (r"\bwf_[A-Za-z0-9]{16,}\b|agent[ _-]?builder",
     "Agent Builder workflow", "2026-11-30",
     "Agents SDK or ChatGPT Workspace Agents (ChatKit itself stays available)", "wf_ IDs are Agent Builder workflow IDs; text mentions should be checked."),
    (r"/v1/evals\b|\bevals\.(?:create|retrieve|update|list|delete|runs)\b|\beval_[a-f0-9]{16,}\b",
     "Evals API / dashboard / graders", "2026-11-30", "Promptfoo (OpenAI cookbook: moving-from-openai-evals-to-promptfoo)", "Evals become read-only."),
    (r"/v1/(?:assistants|threads)\b|\bbeta\.(?:assistants|threads)\b|\basst_[A-Za-z0-9]{16,}\b|assistants=v[12]\b|openAiAssistant",
     "Assistants API", "2026-08-26", "Responses API + Conversations API (OpenAI migration guide: /api/docs/assistants/migration)", ""),
    (r"fine_tuning\.jobs\.create|/v1/fine_tuning/jobs\b",
     "Self-serve fine-tuning job creation", "2027-01-06",
     "No new fine-tuning jobs; inference on existing fine-tunes runs until the base model shuts down", ""),
    (r"/v1/audio/translations\b|\baudio\.translations\b",
     "/v1/audio/translations", "2027-02-26", "/v1/realtime/translations", ""),
    (r"/v1/videos\b|\bvideos\.(?:create|remix)\s*\(",
     "Videos API", "2026-09-24", "No one-to-one replacement", ""),
    (r"realtime=v1\b", "OpenAI-Beta: realtime=v1 header", "2026-05-12", "Realtime GA interface (remove the beta header)", ""),
]
FEATURES = [(re.compile(rx, re.I if "builder" in rx else 0), label, d, r, n) for rx, label, d, r, n in FEATURES]



def _days_left(date, today):
    return (dt.date.fromisoformat(date) - today).days


def _finding(kind, reference, matched_as, info_date, replacement, note, loc, today):
    days = _days_left(info_date, today)
    row = {
        "type": "finding",
        "kind": kind,
        "reference": reference,
        "matchedAs": matched_as,
        "shutdownDate": info_date,
        "daysLeft": days,
        "status": "already shut down" if days <= 0 else "deprecated",
        "replacement": replacement,
        "note": note,
        "source": SOURCE,
    }
    row.update(loc)
    return row


def scan_string(s, loc, today, extra_feature_hits=()):
    """Scan one string; loc holds file / jsonPath / node. Adds line numbers within the string."""
    out = []
    lines = s.split("\n")
    for i, line in enumerate(lines, 1):
        l = dict(loc)
        if len(lines) > 1 or "line" not in l:
            l["line"] = (loc.get("line") or 1) + i - 1 if "line" in loc else i
        l["snippet"] = line.strip()[:200]
        for m in MODEL_TOKEN.finditer(line):
            ft, base, suffix = m.group(1), m.group(2).rstrip("._"), m.group(3)
            info = MODELS.get(base)
            if not info:
                continue
            ref = m.group(0).rstrip("._")
            note = info["note"]
            matched = base
            if ft:
                note = ("Fine-tune of " + base + ": fine-tunes shut down with their base model. " + note).strip()
            out.append(_finding("fine-tune" if ft else "model", ref, matched, info["shutdownDate"],
                                info["replacement"], note, l, today))
        for rx, label, date, repl, note in FEATURES:
            for m in rx.finditer(line):
                out.append(_finding("endpoint/feature", m.group(0), label, date, repl, note, l, today))
    return out


def _label(obj):
    if isinstance(obj, dict):
        if "type" in obj and "name" in obj and isinstance(obj.get("parameters"), dict):  # n8n node
            return f'{obj["name"]} ({obj["type"]})'
        if "module" in obj and "id" in obj:  # Make module
            return f'#{obj["id"]} {obj["module"]}'
    return None


def scan_json(data, file, today):
    out = []

    def walk(o, path, node):
        lab = _label(o)
        if lab:
            node = lab
            # n8n OpenAI node using the Assistants resource
            if "openai" in str(o.get("type", "")).lower() and o.get("parameters", {}).get("resource") == "assistant":
                out.append(_finding("endpoint/feature", "resource: assistant", "Assistants API", "2026-08-26",
                                    "Responses API + Conversations API (OpenAI migration guide: /api/docs/assistants/migration)",
                                    "n8n OpenAI node set to the Assistant resource.",
                                    {"file": file, "jsonPath": path + ".parameters.resource", "node": node,
                                     "snippet": '"resource": "assistant"'}, today))
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("cachedResultName", "cachedResultUrl"):  # n8n UI caches of the same value
                    continue
                walk(v, f"{path}.{k}" if path else str(k), node)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]", node)
        elif isinstance(o, str):
            loc = {"file": file, "jsonPath": path}
            if node:
                loc["node"] = node
            hits = scan_string(o, loc, today)
            if "\n" not in o:
                for h in hits:
                    h.pop("line", None)
            out.extend(hits)

    walk(data, "", None)
    return out


def scan_text(text, file, today):
    t = text.strip()
    if t[:1] in "{[":
        try:
            return scan_json(json.loads(t), file, today), "json"
        except ValueError:
            pass
    return scan_string(text, {"file": file}, today), "text"


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = (r.get("file"), r.get("jsonPath"), r.get("line"), r["reference"], r["matchedAs"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


# ---------------------------------------------------------------- CLI

SCAN_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".toml", ".env",
            ".ini", ".cfg", ".go", ".rb", ".php", ".java", ".kt", ".cs", ".rs", ".swift", ".sh", ".ipynb",
            ".md", ".txt", ".tf", ".sql", ".vue", ".svelte", ".dart", ".scala", ".ex", ".exs", ".lua"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".tox",
             "site-packages", ".mypy_cache", ".pytest_cache", "vendor"}
MAX_BYTES = 2_000_000
FT_NOTE = "gpt-6-luna does not support fine-tuning, so a fine-tune needs a re-design (prompting or another model), not a rename."


def iter_files(root, include_all=False):
    if os.path.isfile(root):
        yield root
        return
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            p = os.path.join(d, f)
            ext = os.path.splitext(f)[1].lower()
            if include_all or ext in SCAN_EXT or f.startswith(".env") or f in ("Dockerfile",):
                yield p


def scan_path(root, today, include_all=False):
    rows = []
    for p in iter_files(root, include_all):
        try:
            if os.path.getsize(p) > MAX_BYTES:
                continue
            with open(p, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        rel = os.path.relpath(p, root) if os.path.isdir(root) else p
        found, _ = scan_text(text, rel, today)
        rows.extend(found)
    rows = dedupe(rows)
    for r in rows:
        if r["kind"] == "fine-tune" and r["replacement"] == "gpt-6-luna":
            r["note"] = (r["note"] + " " + FT_NOTE).strip()
    rows.sort(key=lambda r: (r["shutdownDate"], r.get("file") or "", r.get("line") or 0))
    return rows


def _where(r):
    w = r.get("file") or ""
    if r.get("line"):
        w += f":{r['line']}"
    if r.get("node"):
        w += f"  [{r['node']}]"
    if r.get("jsonPath"):
        w += f"  {r['jsonPath']}"
    return w


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check.py", description="Find retiring OpenAI models and endpoints in code, JSON, YAML, n8n and Make exports.")
    ap.add_argument("paths", nargs="*", default=["."], help="files or folders to scan (default: .)")
    ap.add_argument("--json", action="store_true", help="print findings as JSON")
    ap.add_argument("--fail-within", type=int, default=None, metavar="DAYS",
                    help="exit 1 if any finding shuts down within DAYS days (already shut down counts). Default: exit 1 on any finding")
    ap.add_argument("--no-fail", action="store_true", help="always exit 0")
    ap.add_argument("--all-files", action="store_true", help="scan every file, not just known text/code extensions")
    ap.add_argument("--today", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    rows = []
    for p in a.paths:
        if not os.path.exists(p):
            print(f"check.py: no such path: {p}", file=sys.stderr)
            return 2
        rows.extend(scan_path(p, today, a.all_files))
    if a.json:
        print(json.dumps({"tableVerified": TABLE_VERIFIED, "source": SOURCE, "findings": rows}, indent=2))
    else:
        if not rows:
            print(f"No retiring OpenAI models or endpoints found (table verified {TABLE_VERIFIED}).")
        for r in rows:
            when = f"SHUT DOWN {r['shutdownDate']}" if r["daysLeft"] <= 0 else f"{r['shutdownDate']} ({r['daysLeft']} days)"
            print(f"{_where(r)}\n  {r['reference']}  ->  {r['replacement']}\n  shutdown: {when}")
            if r["note"]:
                print(f"  note: {r['note']}")
        if rows:
            files = len({r.get('file') for r in rows})
            print(f"\n{len(rows)} finding(s) in {files} file(s). Dates from {SOURCE} (verified {TABLE_VERIFIED}).")
            print("Need it migrated and tested for you? Migration Pack from $99: https://rudoodtujjar.gumroad.com/l/csdpjv")
    if a.no_fail or not rows:
        return 0
    if a.fail_within is None:
        return 1
    return 1 if any(r["daysLeft"] <= a.fail_within for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
