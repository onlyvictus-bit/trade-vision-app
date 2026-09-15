# BUILD-2 official-source fixtures — provenance ledger

All artifacts under `official/` are either byte-identical official documents
or verbatim observed text. Synthetic architecture fixtures live one level up
(`../*.json`, provenance `TEST_ARCHITECTURE_FIXTURE`) and are never mixed
with this set: the official loader builds a separate registry.

## Artifacts

| File | What | Source URI | Retrieved | SHA-256 |
|---|---|---|---|---|
| `nse_cmtr71775_2026_holidays.pdf` | NSE circular NSE/CMTR/71775, 2026 trading holidays (byte artifact; corroborates API rows + Muhurat note) | https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf | 2026-09-15 | `1466db29f0b18d8b66524c6e47a8798f6dc8cdef4cf641e01b607e5925579274` |
| `nse_holiday_master_api_2026.json` | NSE holiday-master API `type=trading`, segments CM/COM/FO, verbatim response transcription | https://www.nseindia.com/api/holiday-master?type=trading | 2026-09-15 | `5d228002284d150478553dffd34fdd0d3a0a10196f42aabd49846f57952e84fb` (pinned as `NSE_API_SHA`, asserted at load) |
| `mcx_crude_oil_jan2026_spec.pdf` | MCX crude-oil January-2026 contract specification PDF (byte artifact; series existence + product identity) | https://www.mcxindia.com/docs/default-source/products/contract-specification/crude-oil/crude-oil-january-2026-contract-onwards267be8c1-650a-4baa-aabd-ffcc9364c100.pdf | 2026-09-15 | `347d6512f5c296b7eef128fd8b65dcf91e1fda54a64e6f832b0209315ecaa7cb` |
| `mcx_observed_2026.txt` | Verbatim MCX holiday table, session hours, Muhurat note, crude product facts | https://www.mcxindia.com/market-operations/trading-surveillance/trading-holidays and https://www.mcxindia.com/products/energy/crude-oil | 2026-09-15 | `fde9f8f4707b5e23732bb0a4e680c82a06a43a51de8e84f8a47c223c286d64da` (pinned as `MCX_TXT_SHA`, asserted at load) |

Parser: `official-extract.v1` (row mapping in `official_calendars.json` +
`tests/official_support.py`). Extraction is verbatim transcription only; no
field is inferred. `available_at` for every official record is the retrieval
instant (knowledge begins at retrieval — AS_KNOWN_THEN).

## Temporal provenance (Blocker 1)

- `published_at` is set only where the source states it: the NSE circular
  date 2025-12-12 belongs ONLY to `OF-NSE-CIRCULAR` (circular NSE/CMTR/71775).
- The NSE holiday-master API artifact states no publication timestamp, so
  `OF-NSE-API.published_at` is None (unknown stays unknown). No API-backed
  venue, session, instrument, or calendar fact inherits the circular date;
  each carries `published_at=None` with `available_at` equal to the
  retrieval instant (retrieval-time availability remains causal).

## Effective dating (Blocker 2)

- No pinned artifact states an effective start for any official venue,
  session, instrument, or product fact, so every official
  `effective_from` is None. No `2020-01-01` (or any other invented date)
  appears in the official registry.

## MCX evening close (Blocker 3)

- The pinned MCX text observes Morning Session 09:00–17:00 and Evening
  Session "5:00pm - 11:30 / 11:55pm" with NO source-backed rule selecting
  which close applies to which product/date. The selection rule is
  unresolved.
- The official set therefore models NO exact MCX evening close: neither
  23:30 nor 23:55 appears in any constructed official session/calendar
  fact. `OF-MCX-DAY-V1` is a midnight-minute placeholder that never matches
  real trading times; PARTIAL rows (Ganesh, Dassera) keep
  `tradable_intervals_override=null` and preserve the observed
  MORNING_CLOSED / EVENING_OPEN facts plus the raw ambiguity marker
  `MCX_EVENING_CLOSE_AMBIGUOUS_2330_2355_RULE_UNRESOLVED` as
  `contract_events`. Exact evening membership requiring the unknown boundary
  fails closed (UNAVAILABLE) instead of reporting OPEN/CLOSED from a guess.
  Exact cross-midnight/session machinery is proven by the synthetic set.

## Close / settlement semantics (Blocker 4)

- The pinned MCX text explicitly says settlement references were NOT
  observed. Official MCX session/profile objects therefore carry
  `close_semantics="UNSPECIFIED"` and
  `settlement_semantics="UNSPECIFIED"`. Session end, last traded price,
  daily settlement, and final settlement are never equated.

## Crude contract identity (Blocker 5)

- The "Crude Oil January 2026 Contract Onwards" row proves series/listing
  existence ONLY — not `contract_month`, expiry, listing date, last-trade
  timestamp, lot, tick, or settlement. No exact `ContractProfileV1` is built
  from it; asking for the guessed `OF-MCX-COMM:CRUDEOIL-2026-01` returns
  `CONTRACT_NOT_FOUND` / UNAVAILABLE.
- "100 Barrels" was observed on OPTIONS series titles, never as a futures
  `trading_unit` field, so no futures trading unit is claimed.
- Kept product-level facts (genuinely observed): the MCX crude-oil product
  exists (`OF-MCX-COMM:CRUDEOIL`) with underlying CME/NYMEX benchmark WTI.
  Tick, expiry, lot, settlement, and price precision remain unavailable.

## Muhurat timing (Blocker 6)

- The pinned MCX text announces "Muhurat trading WILL be conducted on
  Sunday, November 08, 2026" with "Timings ... notified subsequently":
  UNKNOWN TIMING is not CLOSED.
- MCX 2026-11-08 has no holiday-table row proving closure, so there is NO
  active `CLOSED_HOLIDAY` record for the date. The announcement survives as
  a non-active SPECIAL evidence record (lifecycle DRAFT) carrying
  `MUHURAT_TRADING_ANNOUNCED_TIMINGS_PENDING_CIRCULAR`; exact MCX membership
  on the date stays UNAVAILABLE (`CALENDAR_UNAVAILABLE`), never whole-day
  CLOSED.
- NSE 2026-11-08 keeps ACTIVE `CLOSED_HOLIDAY` rows (the API proves normal
 -session closure) WITH the separate `MUHURAT_...` event: regular-session
  closed and special-session timing unknown are preserved as two distinct
  facts, never collapsed into "no trading all day".

## Hash binding (Blocker 7)

- Every row in `official_calendars.json` names its exact `source_receipt_id`
  (NSE rows → `OF-NSE-API`; MCX rows → `OF-MCX-PAGE`). At load each
  `CalendarRecordV1` receives `source_hash` equal to that receipt's
  `content_hash` over the RAW PINNED SOURCE BYTES (not this mapping file),
  with `source_document_id`, `published_at`, and `available_at` bound from
  the same receipt. Broad venue-based inference is never used.

## Instrument provenance (Blocker 8)

- Symbol spellings (RELIANCE, NIFTY) come from the repository legacy fixture
  `tests/fixtures/market_identity/instruments.json`, NOT from NSE documents.
  The `LEGACY-MARKET-IDENTITY-INSTRUMENT-FIXTURE` receipt (`LEGACY_TEST_FIXTURE`
  / `TRADE_VISION_REPOSITORY`, content hash of the actual fixture bytes,
  `published_at=None`) is their sole instrument provenance. No instrument
  whose identity comes from a repository fixture claims only an exchange
  holiday API. Venue/calendar facts still use official NSE receipts
  independently. "Official registry" therefore means "official calendar and
  product evidence plus explicitly labeled repository support stubs" — never
  exchange-certified instruments.

## Explicit non-claims

- These examples do **not** constitute historical calendar coverage, a live
  feed, an instrument master, or settlement sourcing. BUILD-0 readiness stays:
  `EXCHANGE_CALENDAR_HISTORY = NEEDS_VERSIONED_FILE`,
  `COMMODITY_INSTRUMENT_MASTER = UNAVAILABLE`,
  `SETTLEMENT_CONTEXT = NEEDS_EXTERNAL_FEED`. No manifest change was made.
- NSE regular-session hours (09:15–15:30) were **not** observed in the official
  artifacts above, so the official set contains **no NSE regular-day session
  profile with observed hours** (`OF-NSE-DAY-V1` is a placeholder never
  consulted for holidays). Official NSE records therefore prove
  holiday/exception semantics only. The NSE regular profile remains the legacy
  compatibility adapter.
- MCX tick/lot/expiry/settlement for crude futures were **not** observed and
  no exact official crude contract exists (explicit missingness).
- Symbol spellings (RELIANCE, NIFTY) come from repository legacy fixtures, not from
  these official documents, and are labeled as such in the loader (see
  Instrument provenance above).
- Venue timezones (Asia/Kolkata) record exchange domicile per the official
  Indian-exchange sites; session times in these documents are IST.
