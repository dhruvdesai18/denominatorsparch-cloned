# Data Contracts

Four CSV schemas shared across all agents. All data in this repo is
synthetic/placeholder for hackathon use and must remain clearly labeled
as such — no real patient or complaint data.

## complaints.csv
| column | type | notes |
|---|---|---|
| complaint_id | string | unique per complaint |
| device_code | string | SKI/SKJ/SKL-style product code |
| event_date | date (YYYY-MM-DD) | |
| event_type | string | e.g. malfunction, injury, death |
| narrative | string | free-text complaint description |
| source | string | e.g. MAUDE |

## exposure.csv
| column | type | notes |
|---|---|---|
| device_code | string | joins to complaints.device_code |
| period_start | date | |
| period_end | date | |
| units_distributed | int | denominator input |
| units_in_field | int | denominator input |

## baseline.csv
| column | type | notes |
|---|---|---|
| device_code | string | |
| baseline_rate_pct | float | historical complaint rate, % |
| baseline_period_start | date | |
| baseline_period_end | date | |
| source | string | |

## document_map.csv
| column | type | notes |
|---|---|---|
| document_id | string | |
| document_type | string | one of: CAPA, PMS/PSUR, SOP |
| device_code | string | |
| qms_reference | string | QMS document identifier |
| status | string | DRAFT only — never auto-published |

## Validation rules
- `device_code` must exist in all four files consistently.
- Dates must be ISO 8601 (`YYYY-MM-DD`).
- Rate calculations (complaints / exposure * 100) must never divide by zero —
  the rate engine refuses the calculation instead of guessing.
- `document_map.status` must always start as `DRAFT`; nothing in this
  pipeline auto-publishes to QMS.
