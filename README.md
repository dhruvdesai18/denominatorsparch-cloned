# Denominator

Medical Device Post-Market Safety System — hackathon build.

7-agent pipeline (5 agents + rate engine + human decision gate) that
ingests FDA MAUDE complaints, computes complaint rates against exposure
data, and generates draft Safety Action Packs for QMS review — with a
mandatory human decision gate before any regulatory action.

## Structure
- `agents/` — `DenominatorAgent` base class + 5 pipeline agents (placeholders, filled in Days 3-9)
- `config/` — `CacheManager` (disk cache for LLM outputs) and `token_counter.py` (budget tracker)
- `data/` — data contract CSVs (complaints, exposure, baseline, document_map) + schema README
- `docs/` — architecture spec / diagram
- `tests/` — unit tests

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
python3 config/token_counter.py
```

## Budget
147,000 tokens (21,000 x 7 people via Manus). Only 3 planned LLM calls
(Agents #1, #2, #5) totaling ~$16.44 — everything else is free APIs or
pure Python. See `config/token_counter.py`.

## Non-negotiables
- Human decision gate before any QMS action.
- Rate engine refuses unsafe calculations rather than guessing.
- Safety Action Packs are always `DRAFT` status — never auto-published.
- All synthetic/placeholder data must be clearly labeled as such.
