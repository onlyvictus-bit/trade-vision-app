# BUILD-2 official-source fixtures — provenance ledger

All artifacts under `official/` are either byte-identical official documents
or verbatim observed text. Synthetic architecture fixtures live one level up
(`../*.json`, provenance `TEST_ARCHITECTURE_FIXTURE`) and are never mixed
with this set: the official loader builds a separate registry.

## Artifacts

| File | What | Source URI | Retrieved | SHA-256 |
|---|---|---|---|---|
| `nse_cmtr71775_2026_holidays.pdf` | NSE circular NSE/CMTR/71775, 2026 trading holidays (byte artifact; corroborates API rows + Muhurat note) | https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf | 2026-09-15 | `1466db29f0b18d8b66524c6e47a8798f6dc8cdef4cf641e01b607e5925579274` |
| `nse_holiday_master_api_2026.json` | NSE holiday-master API `type=trading`, segments CM/COM/FO, verbatim response transcription | https://www.nseindia.com/api/holiday-master?type=trading | 2026-09-15 | pinned by `SourceReceiptV1.content_hash` at load (see test) |
| `mcx_crude_oil_jan2026_spec.pdf` | MCX crude-oil January-2026 contract specification PDF (byte artifact; series existence + product identity) | https://www.mcxindia.com/docs/default-source/products/contract-specification/crude-oil/crude-oil-january-2026-contract-onwards267be8c1-650a-4baa-aabd-ffcc9364c100.pdf | 2026-09-15 | `347d6512f5c296b7eef128fd8b65dcf91e1fda54a64e6f832b0209315ecaa7cb` |
| `mcx_observed_2026.txt` | Verbatim MCX holiday table, session hours, Muhurat note, crude product facts | https://www.mcxindia.com/market-operations/trading-surveillance/trading-holidays and https://www.mcxindia.com/products/energy/crude-oil | 2026-09-15 | pinned by `SourceReceiptV1.content_hash` at load (see test) |

Parser: `official-extract.v1` (row mapping in `official_calendars.json` +
`tests/official_support.py`). Extraction is verbatim transcription only; no
field is inferred. `available_at` for every official record is the retrieval
instant (knowledge begins at retrieval — AS_KNOWN_THEN). `published_at` is
set only where the source states it (NSE circular date 2025-12-12).

## Explicit non-claims

- These examples do **not** constitute historical calendar coverage, a live
  feed, an instrument master, or settlement sourcing. BUILD-0 readiness stays:
  `EXCHANGE_CALENDAR_HISTORY = NEEDS_VERSIONED_FILE`,
  `COMMODITY_INSTRUMENT_MASTER = UNAVAILABLE`,
  `SETTLEMENT_CONTEXT = NEEDS_EXTERNAL_FEED`. No manifest change was made.
- NSE regular-session hours (09:15–15:30) were **not** observed in the official
  artifacts above, so the official set contains **no NSE regular-day session
  profile**. Official NSE records therefore prove holiday/exception semantics
  only. The NSE regular profile remains the legacy compatibility adapter.
- MCX tick/lot/expiry/settlement for crude futures were **not** observed and
  are absent from the official contract record (explicit missingness).
- Symbol spellings (RELIANCE) come from repository legacy fixtures, not from
  these official documents, and are labeled as such in the loader.
- Venue timezones (Asia/Kolkata) record exchange domicile per the official
  Indian-exchange sites; session times in these documents are IST.
