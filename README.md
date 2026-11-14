# openai-sunset-check

Scans your code, JSON/YAML configs and n8n/Make exports for OpenAI models and endpoints that are being retired, and prints each hit with its shutdown date and replacement.

Zero dependencies: one Python file (standard library only; CI tests Python 3.10 and 3.13), plus a GitHub Action.

## Usage

### CLI

```bash
curl -O https://raw.githubusercontent.com/mdfifty50-boop/openai-sunset-check/main/check.py
python check.py path/to/your/project          # or a single file, e.g. an n8n workflow export
python check.py . --json                      # machine-readable output
python check.py . --fail-within 30            # exit 1 only if something shuts down within 30 days
python check.py . --no-fail                   # report only, always exit 0
```

Example output:

```
bot.py:6
  o3  ->  gpt-6.1-sol
  shutdown: 2026-12-11 (27 days)
workflow.json  [OpenAI Chat Model (@n8n/n8n-nodes-langchain.lmChatOpenAi)]  nodes[1].parameters.model.value
  gpt-4o-mini  ->  gpt-6-luna
  shutdown: 2027-01-14 (61 days)
```

By default the exit code is 1 when anything is found, so it can gate CI.

### GitHub Action

```yaml
name: openai-sunset-check
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: mdfifty50-boop/openai-sunset-check@v1
        with:
          path: .              # files or folders, space separated
          fail-within: "45"    # optional: fail only if a shutdown is within 45 days
          # no-fail: "true"    # optional: report without failing
```

## What it detects

- Model IDs in any text, including dated snapshots (`gpt-4o-2024-08-06`) and fine-tunes (`ft:gpt-4o-mini-2024-07-18:org::id`)
- Bare aliases (`gpt-4o`, `gpt-4.1-mini`) that resolve to a retiring snapshot
- n8n and Make exports: reports the node/module name and JSON path
- Endpoints and features: `/v1/prompts` and `pmpt_` IDs, Agent Builder `wf_` IDs, Evals, fine-tuning job creation, `/v1/audio/translations`, Assistants API, and already shut-down items

## Shutdown dates

Source: [platform.openai.com/docs/deprecations](https://platform.openai.com/docs/deprecations), checked 14 Nov 2026. Always confirm against that page before acting.

| Shutdown | Affected | Replacement |
|---|---|---|
| 30 Nov 2026 | Agent Builder | Agents SDK or ChatGPT Workspace Agents |
| 30 Nov 2026 | Evals (dashboard, API, graders) become read-only | Promptfoo |
| 30 Nov 2026 | `/v1/prompts` and reusable prompt objects | Prompt content in your own code |
| 1 Dec 2026 | `gpt-image-1-mini`, `gpt-image-1.5`, `chatgpt-image-latest` | `gpt-image-2.6-sunburst` or `gpt-image-2.6-flare` |
| 11 Dec 2026 | `gpt-5`, `o3` | `gpt-6.1-sol` |
| 11 Dec 2026 | `gpt-5-mini` | `gpt-6.1-terra` |
| 11 Dec 2026 | `gpt-5-nano` | `gpt-6-luna` |
| 11 Dec 2026 | `gpt-5-pro`, `o3-pro` | `gpt-6.1-sol` (`reasoning.mode: pro`) |
| 6 Jan 2027 | `tts-1`, `tts-1-hd`, `gpt-4o-mini-tts` | `gpt-realtime-2.1-mini` |
| 6 Jan 2027 | Self-serve fine-tuning job creation | No new jobs; existing fine-tunes run until their base model shuts down |
| 14 Jan 2027 | `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `gpt-4.1-mini` (and their fine-tunes) | `gpt-6-luna` |
| 20 Jan 2027 | `gpt-realtime`, `gpt-audio`, `gpt-4o-realtime`, `gpt-4o-audio`, mini variants | `gpt-realtime-2.1(-mini)` / `gpt-audio-1.5` |
| 1 Feb 2027 | `gpt-5.5-cyber-preview` | Most capable cyber model available to you |
| 10 Feb 2027 | `gpt-image-2` | `gpt-image-2.6-sunburst` or `gpt-image-2.6-flare` |
| 26 Feb 2027 | `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-transcribe-diarize` | `gpt-live-transcribe` or `gpt-transcribe` |
| 26 Feb 2027 | `/v1/audio/translations` | `/v1/realtime/translations` |
| 1 Apr 2027 | `gpt-5.1`, `gpt-5.3-codex` | `gpt-6-sol` |
| 1 Apr 2027 | `gpt-5.4-nano` | `gpt-6-luna` |

Note on fine-tunes: fine-tuned models shut down with their base model, and `gpt-6-luna` does not support fine-tuning (per its model page), so a `gpt-4o`/`gpt-4.1` fine-tune needs a re-design rather than a model rename.

## Limits

It is a pattern scanner, not a runtime check. Model names built at runtime (string concatenation, values in a database or secret store) are not seen. For the authoritative list from your own account, call `GET /v1/models` and read each model's `shutdown_date`.

## Related

- No repo? Paste a file or an n8n/Make export into the free [Apify scanner](https://apify.com/fifty50labs/openai-deprecation-scanner).
- Need it migrated and tested for you? [$79 Migration Pack](https://rudoodtujjar.gumroad.com/l/csdpjv)

## License

MIT
