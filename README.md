# Clara AI — Automation Pipeline

> **Demo Call → Retell Agent Draft → Onboarding Update → Agent v2**

Fully automated, zero-cost pipeline that processes call transcripts and generates
Retell AI voice agent configurations — with versioning, changelogs, and task tracking.

---

## Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE A                               │
│                                                                 │
│  inputs/demo/                                                   │
│  account_XXX_demo.txt                                           │
│       │                                                         │
│       ▼                                                         │
│  [1] Read transcript                                            │
│       │                                                         │
│       ▼                                                         │
│  [2] Groq LLM Extraction                                        │
│      (llama-3.3-70b-versatile — free tier)                      │
│       │                                                         │
│       ▼                                                         │
│  [3] Account Memo JSON (v1)         ──► outputs/accounts/       │
│      + Retell Agent Spec (v1)            account_XXX/v1/        │
│       │                                  ├── memo.json          │
│       ▼                                  └── agent_spec.json    │
│  [4] Task Tracker Item              ──► outputs/tasks.json      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE B                               │
│                                                                 │
│  inputs/onboarding/                                             │
│  account_XXX_onboarding.txt                                     │
│       │                                                         │
│       ▼                                                         │
│  [1] Load v1 memo (from Pipeline A output)                      │
│       │                                                         │
│       ▼                                                         │
│  [2] Groq LLM Patch                                             │
│      (applies onboarding changes to v1 memo)                    │
│       │                                                         │
│       ▼                                                         │
│  [3] Account Memo JSON (v2)         ──► outputs/accounts/       │
│      + Retell Agent Spec (v2)            account_XXX/v2/        │
│      + Changelog (diff v1→v2)            ├── memo.json          │
│       │                                  ├── agent_spec.json    │
│       ▼                                  └── changes.json       │
│  [4] Task Tracker Item              ──► changelog/              │
│                                          account_XXX_changes.md │
└─────────────────────────────────────────────────────────────────┘
```

---

## Zero-Cost Stack

| Component | Tool | Why it's free |
|---|---|---|
| Automation orchestrator | n8n (Docker, self-hosted) | Self-hosted = free forever |
| LLM extraction | Groq free tier (llama-3.3-70b) | No credit card, generous free limits |
| Storage | Local JSON files in repo | No external service needed |
| Task tracker | Local `tasks.json` | Built-in; optional Trello free API |
| Retell | Agent Spec JSON output | Manual import if API not free |

---

## Project Structure

```
clara-ai-pipeline/
├── README.md
├── docker-compose.yml         ← Starts n8n locally
├── .env.example               ← Copy to .env and fill in keys
├── requirements.txt           ← Python dependencies (for script mode)
│
├── workflows/
│   └── n8n_pipeline.json      ← Import this into n8n
│
├── scripts/
│   ├── extractor.py           ← LLM extraction + patch logic
│   ├── agent_spec_generator.py← Generates Retell agent spec + prompt
│   ├── changelog_generator.py ← Diffs v1→v2 memos
│   ├── task_tracker.py        ← Task tracking (local + optional Trello)
│   ├── pipeline_a.py          ← Pipeline A orchestrator
│   ├── pipeline_b.py          ← Pipeline B orchestrator
│   └── batch_runner.py        ← Batch-runs all 10 files
│
├── inputs/
│   ├── demo/                  ← 5 demo call transcripts (.txt)
│   └── onboarding/            ← 5 onboarding call transcripts (.txt)
│
├── outputs/
│   ├── tasks.json             ← All task tracker items
│   ├── batch_summary.json     ← Batch run report
│   └── accounts/
│       └── account_001/
│           ├── v1/
│           │   ├── memo.json
│           │   └── agent_spec.json
│           └── v2/
│               ├── memo.json
│               ├── agent_spec.json
│               └── changes.json
│
└── changelog/
    └── account_001_changes.md  ← Human-readable diff per account
```

---

## Setup Instructions

### Step 1 — Clone the repo and set up environment

```bash
git clone <(https://github.com/Giridhar083/clara-ai-pipeline)>
cd clara-ai-pipeline

cp .env.example .env
```

Open `.env` and add your **Groq free API key**:
```
GROQ_API_KEY=API_Key

### Step 2 — Add your transcript files

Place your transcript `.txt` files in:
- `inputs/demo/` — name them `account_001_demo.txt`, `account_002_demo.txt`, etc.
- `inputs/onboarding/` — name them `account_001_onboarding.txt`, etc.

The filename prefix (e.g. `account_001`) becomes the `account_id`.  
Sample transcripts are already included for all 5 accounts.

---

### Step 3 — Choose your run method

You have two options: **n8n workflow** (recommended) or **Python scripts directly**.

---

#### Option A — Run via n8n (recommended)

**Requires:** Docker and Docker Compose installed.

```bash
# Start n8n
docker-compose up -d

# Open n8n in your browser
open http://localhost:5678
# Login: admin / claraai123 (or whatever you set in .env)
```

**Import the workflow:**
1. In n8n, click **Workflows** → **Import from file**
2. Select `workflows/n8n_pipeline.json`
3. Click **Save**

**Set your Groq API key in n8n:**
1. Go to **Settings** → **Environment Variables** (or it auto-reads from docker-compose env)
2. Confirm `GROQ_API_KEY` is visible

**Run the pipeline:**
1. Open the `Clara AI — Full Pipeline (A + B)` workflow
2. Click **Execute Workflow** (top right)
3. Both Pipeline A and Pipeline B will run in parallel
4. Watch the execution log for progress

> **Note:** Pipeline B reads v1 outputs from Pipeline A. If running for the first time,
> Pipeline A finishes first (it processes faster). If B fails because v1 isn't ready,
> just re-run B after A completes.

---

#### Option B — Run via Python scripts

**Requires:** Python 3.10+ installed.

```bash
# Install dependencies
pip install -r requirements.txt

# Load environment variables
export $(cat .env | xargs)

# Run everything at once (recommended)
python scripts/batch_runner.py

# Or run pipelines separately:
python scripts/batch_runner.py --pipeline a   # Demo calls only
python scripts/batch_runner.py --pipeline b   # Onboarding calls only (requires A to be done)

# Or run a single file:
python scripts/pipeline_a.py --file inputs/demo/account_001_demo.txt
python scripts/pipeline_b.py --file inputs/onboarding/account_001_onboarding.txt
```

---

### Step 4 — View outputs

After running, your outputs will be at:

```
outputs/
├── tasks.json                   ← All task tracking items
├── batch_summary.json           ← Full run report with stats
└── accounts/
    ├── account_001/
    │   ├── v1/memo.json         ← Extracted business data
    │   ├── v1/agent_spec.json   ← Retell agent config (v1)
    │   ├── v2/memo.json
    │   ├── v2/agent_spec.json   ← Updated config (v2)
    │   └── v2/changes.json      ← Machine-readable diff
    └── ...

changelog/
├── account_001_changes.md       ← Human-readable v1→v2 diff
└── ...
```

---

## Retell Agent Import (Manual Steps)

If Retell's free tier does not allow programmatic agent creation via API:

1. Open Retell dashboard at **https://app.retell.ai**
2. Click **Create Agent**
3. Open `outputs/accounts/account_XXX/v1/agent_spec.json`
4. Copy the value of `"system_prompt"` into Retell's **System Prompt** field
5. Set the voice to match `voice_style.voice_id` (e.g. `rachel`)
6. Configure call transfer using `call_transfer_protocol.primary_transfer_number`
7. Save the agent

For v2 updates: repeat using `v2/agent_spec.json`.

---

## Output Format Details

### Account Memo JSON (`memo.json`)
Structured business configuration extracted from the call transcript:
```json
{
  "account_id": "account_001",
  "company_name": "Arctic Air HVAC",
  "business_hours": { "days": "...", "start": "...", "end": "...", "timezone": "..." },
  "office_address": "...",
  "services_supported": ["HVAC Repair", "..."],
  "emergency_definition": ["complete system failure in extreme heat", "..."],
  "emergency_routing_rules": { "primary_contact_name": "...", ... },
  "non_emergency_routing_rules": { ... },
  "call_transfer_rules": { "transfer_number": "...", ... },
  "special_routing_rules": [{ "trigger": "...", "action": "...", ... }],
  "integration_constraints": ["never create jobs in ServiceTitan"],
  "pricing_instructions": "...",
  "after_hours_flow_summary": "...",
  "office_hours_flow_summary": "...",
  "tone_instructions": "...",
  "questions_or_unknowns": [],
  "notes": "..."
}
```

### Retell Agent Spec (`agent_spec.json`)
```json
{
  "agent_name": "...",
  "account_id": "...",
  "version": "v1",
  "voice_style": { ... },
  "system_prompt": "<full multi-section prompt>",
  "key_variables": { ... },
  "tool_invocation_placeholders": { ... },
  "call_transfer_protocol": { ... },
  "fallback_protocol": { ... },
  "emergency_protocol": { ... },
  "conversation_hygiene": { ... }
}
```

---

## Idempotency

Running the pipeline twice on the same inputs is safe:
- Output files are overwritten (same content, no duplicates)
- Task tracker entries replace by `task_id` (no duplicate tasks)
- Changelog is regenerated fresh each time

---

## Known Limitations

1. **Groq free tier rate limits** — If processing all 10 files at once, you may hit rate limits. The batch runner adds a 2-second delay between files. If you see 429 errors, increase the delay in `batch_runner.py`.

2. **LLM hallucination** — The extractor is instructed to use `null` for missing fields, but LLMs can occasionally infer details not in the transcript. Always review `questions_or_unknowns` in the memo.

3. **n8n Pipeline B timing** — In the n8n workflow, Pipeline A and B are triggered simultaneously. B will fail if A hasn't written v1 outputs yet. Re-run B after A completes, or run them sequentially by removing the parallel connection.

4. **Retell API access** — Retell may not allow programmatic agent creation on free tier. The pipeline outputs a complete spec JSON; see "Retell Agent Import" above for manual steps.

5. **No audio transcription** — This pipeline takes `.txt` transcripts as input. If you only have audio files, transcribe them first using [Whisper locally](https://github.com/openai/whisper): `whisper audio.mp3 --output_format txt`

---

## What I Would Improve with Production Access

1. **Webhooks** — Trigger pipelines automatically when a new recording lands in a Google Drive folder or S3 bucket
2. **Retell API integration** — Auto-create/update agents via Retell API instead of manual import
3. **Structured output enforcement** — Use Groq's JSON mode with a strict schema to eliminate any parse failures
4. **Supabase storage** — Replace local JSON files with Supabase for multi-user access and real-time dashboards
5. **Confidence scoring** — Add per-field confidence scores to flag extractions that need human review
6. **Audio pipeline** — Integrate Whisper locally to accept raw recordings as input
7. **Review UI** — A simple web dashboard to review, approve, and push agent specs to Retell

---

## Groq Free Tier Usage Estimate

Each transcript requires approximately 2 Groq API calls:
- Pipeline A: 1 call per demo file (5 calls total)
- Pipeline B: 1 call per onboarding file (5 calls total)
- **Total: ~10 calls, ~25,000 tokens**

Groq free tier allows **14,400 requests/day** and generous token limits.  
This entire assignment runs well within free limits.
