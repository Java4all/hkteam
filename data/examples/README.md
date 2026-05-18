# Demo incident inputs (Chainlit UI)

Use these in **Chainlit** — click a **starter** button or copy from a `.txt` file.

On a GPU instance, open Chainlit via port-forward (e.g. http://localhost:7860 after `brev port-forward ... --port 7860:7860`).

## Paste format

The UI treats the **last line** as **location**; everything above is **description**:

```text
<what happened — one or more lines>
<location — city, street, landmark>
```

Minimum 12 characters total.

## Files

| File | Scenario |
|------|----------|
| `01-utilities-water-main.txt` | Water main rupture (utilities) |
| `02-flood-and-utilities.txt` | Flood + pipe burst (multi-agent) |
| `03-cyber-hospital.txt` | Hospital ransomware (cyber) |
| `04-flood-critical.txt` | City-wide flood (CRITICAL) |
| `05-infrastructure-bridge.txt` | Bridge damage (infrastructure) |
| `06-public-safety-crowd.txt` | Large crowd (public safety) |
| `07-utilities-substation.txt` | Power substation fire (utilities) |
| `08-cyber-municipal.txt` | City hall cyber incident (cyber) |

Structured list: `incidents.yaml` (same content; used by UI starters).

## Terminal demo (no UI)

```bash
make demo
# or
CRISIS_USE_MOCK_LLM=true python -m crisis.scripts.run_demo
```
