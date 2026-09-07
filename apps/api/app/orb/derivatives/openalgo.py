from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime, timezone
from typing import Any, Iterable, Sequence

import httpx

from .contracts import (
    FuturesSnapshot,
    Greeks,
    OptionChainSnapshot,
    OptionQuote,
    OptionStrike,
    OptionType,
    digest,
    utc_now_ns,
)


class OpenAlgoError(RuntimeError):
    pass


class OpenAlgoProtocolError(OpenAlgoError):
    pass


class OpenAlgoAuthError(OpenAlgoError):
    """401/403 from the vendor: credentials rejected. Never retried, never logged with key."""


class OpenAlgoUnavailable(OpenAlgoError):
    """429/transient-5xx exhausted bounded retries, or final 5xx. Safe to surface as 503 downstream."""


def _parse_expiry(value: str) -> date:
    value = value.strip().upper()
    for fmt in ("%d%b%y", "%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise OpenAlgoProtocolError(f"unsupported expiry date: {value!r}")


def _payload_hash(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class OpenAlgoDataProvider:
    """Broker-neutral OpenAlgo data adapter.

    Security properties:
      * API key is never included in exceptions/repr.
      * bounded timeouts/retries only; no infinite retry loop.
      * 429/5xx retry, validation/4xx fail fast.
      * caller controls timestamps for deterministic replay tests.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 4.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.075,
        client: httpx.Client | None = None,
        source_instance: str = "default",
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must be http(s)")
        if not api_key:
            raise ValueError("api_key is required")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.source_instance = source_instance
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout_seconds))

    def __repr__(self) -> str:
        return f"OpenAlgoDataProvider(base_url={self.base_url!r}, source_instance={self.source_instance!r})"

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OpenAlgoDataProvider":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {"apikey": self._api_key, **payload}
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        last: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.post(url, json=body, timeout=self.timeout_seconds)
                if response.status_code == 429 or response.status_code >= 500:
                    last = OpenAlgoUnavailable(f"transient HTTP {response.status_code} from {endpoint}")
                    if attempt < self.max_retries:
                        time.sleep(self.backoff_seconds * (2 ** attempt))
                        continue
                    raise last
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as hse:
                    code = hse.response.status_code if hse.response is not None else 0
                    if code in (401, 403):
                        raise OpenAlgoAuthError(f"OpenAlgo rejected credentials (HTTP {code})") from hse
                    raise OpenAlgoProtocolError(f"OpenAlgo HTTP {code} from {endpoint}") from hse
                try:
                    data = response.json()
                except ValueError as jde:
                    raise OpenAlgoProtocolError(f"OpenAlgo returned non-JSON body from {endpoint}") from jde
                if not isinstance(data, dict):
                    raise OpenAlgoProtocolError("OpenAlgo response must be a JSON object")
                if str(data.get("status", "")).lower() != "success":
                    msg = str(data.get("message", "OpenAlgo returned error"))[:300]
                    raise OpenAlgoError(msg.replace(self._api_key, "***"))
                return data
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = exc
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (2 ** attempt))
                    continue
                break
        raise OpenAlgoUnavailable(
            f"OpenAlgo request failed after bounded retries: {type(last).__name__ if last else 'HTTP_ERROR'}")

    def quote(self, symbol: str, exchange: str, *, now_ns: int | None = None, expiry_date: date | None = None) -> FuturesSnapshot:
        data = self._post("quotes", {"symbol": symbol, "exchange": exchange})
        q = data.get("data") or {}
        now = utc_now_ns() if now_ns is None else now_ns
        try:
            return FuturesSnapshot(
                symbol=symbol.upper(), exchange=exchange.upper(), expiry_date=expiry_date,
                ltp=float(q["ltp"]), bid=float(q.get("bid") or 0), ask=float(q.get("ask") or 0),
                open=float(q.get("open") or 0), high=float(q.get("high") or 0), low=float(q.get("low") or 0),
                prev_close=float(q.get("prev_close") or 0), volume=float(q.get("volume") or 0), oi=float(q.get("oi") or 0),
                as_of_ns=now, received_ns=now, provider_payload_hash=_payload_hash(data),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenAlgoProtocolError(f"invalid quote response for {symbol}: {type(exc).__name__}") from exc

    def expiries(self, symbol: str, exchange: str, instrumenttype: str = "options") -> tuple[date, ...]:
        data = self._post("expiry", {"symbol": symbol, "exchange": exchange, "instrumenttype": instrumenttype})
        values = data.get("data") or []
        if not isinstance(values, list):
            raise OpenAlgoProtocolError("expiry data must be an array")
        return tuple(sorted(_parse_expiry(str(x)) for x in values))


    def search_instruments(self, query: str, exchange: str | None = None) -> tuple[dict[str, Any], ...]:
        payload: dict[str, Any] = {"query": query}
        if exchange:
            payload["exchange"] = exchange
        data = self._post("search", payload)
        rows = data.get("data") or []
        if not isinstance(rows, list):
            raise OpenAlgoProtocolError("search data must be an array")
        return tuple(x for x in rows if isinstance(x, dict))

    def resolve_nearest_future(self, underlying: str, derivatives_exchange: str, *, on_or_after: date) -> tuple[str, date] | None:
        """Resolve a real future from OpenAlgo master data; never invent symbols."""
        expiries = self.expiries(underlying, derivatives_exchange, "futures")
        candidates = [d for d in expiries if d >= on_or_after]
        if not candidates:
            return None
        wanted = min(candidates)
        rows = self.search_instruments(underlying, derivatives_exchange)
        matches: list[tuple[str, date]] = []
        for row in rows:
            itype = str(row.get("instrumenttype") or "").upper()
            symbol = str(row.get("symbol") or "")
            raw_expiry = row.get("expiry")
            if "FUT" not in itype or not symbol or not raw_expiry:
                continue
            try:
                exp = _parse_expiry(str(raw_expiry))
            except OpenAlgoProtocolError:
                continue
            name = str(row.get("name") or "").upper()
            if exp == wanted and (name == underlying.upper() or symbol.upper().startswith(underlying.upper())):
                matches.append((symbol, exp))
        if not matches:
            return None
        matches.sort(key=lambda x: x[0])
        return matches[0]

    def synthetic_future(self, *, underlying: str, exchange: str, expiry_date: date) -> float:
        data = self._post("syntheticfuture", {
            "underlying": underlying, "exchange": exchange,
            "expiry_date": expiry_date.strftime("%d%b%y").upper(),
        })
        try:
            value = float(data["synthetic_future_price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenAlgoProtocolError("syntheticfuture response missing price") from exc
        if value <= 0:
            raise OpenAlgoProtocolError("syntheticfuture price must be positive")
        return value

    def option_chain(
        self,
        *,
        underlying: str,
        exchange: str,
        expiry_date: date,
        strike_count: int | None = None,
        now_ns: int | None = None,
    ) -> OptionChainSnapshot:
        payload: dict[str, Any] = {
            "underlying": underlying,
            "exchange": exchange,
            "expiry_date": expiry_date.strftime("%d%b%y").upper(),
        }
        if strike_count is not None:
            if not 1 <= strike_count <= 100:
                raise ValueError("strike_count must be 1..100")
            payload["strike_count"] = strike_count
        data = self._post("optionchain", payload)
        now = utc_now_ns() if now_ns is None else now_ns
        rows: list[OptionStrike] = []
        chain_data = data.get("chain")
        if not isinstance(chain_data, list):
            raise OpenAlgoProtocolError("option chain missing chain array")
        for raw in chain_data:
            if not isinstance(raw, dict):
                continue
            strike = float(raw["strike"])
            def leg(key: str, kind: OptionType) -> OptionQuote | None:
                x = raw.get(key)
                if not isinstance(x, dict) or not x.get("symbol"):
                    return None
                # G4: missing exchange contract metadata fails closed. A fabricated
                # lot_size/tick_size would corrupt GEX/wall math multiplicatively, so
                # the whole chain is rejected (→ UNAVAILABLE downstream), never defaulted.
                # Real vendor field-name mapping is confirmed at G1 capture.
                if x.get("lotsize") in (None, "") or x.get("tick_size") in (None, ""):
                    raise OpenAlgoProtocolError(
                        f"CONTRACT_METADATA_MISSING: {key} leg of strike {strike} has no lotsize/tick_size")
                return OptionQuote(
                    symbol=str(x["symbol"]), option_type=kind, strike=strike, label=str(x.get("label") or ""),
                    ltp=float(x.get("ltp") or 0), bid=float(x.get("bid") or 0), ask=float(x.get("ask") or 0),
                    open=float(x.get("open") or 0), high=float(x.get("high") or 0), low=float(x.get("low") or 0),
                    prev_close=float(x.get("prev_close") or 0), volume=float(x.get("volume") or 0), oi=float(x.get("oi") or 0),
                    lot_size=int(float(x["lotsize"])), tick_size=float(x["tick_size"]),
                )
            rows.append(OptionStrike(strike=strike, ce=leg("ce", OptionType.CE), pe=leg("pe", OptionType.PE)))
        rows.sort(key=lambda r: r.strike)
        try:
            exp = _parse_expiry(str(data.get("expiry_date") or payload["expiry_date"]))
            return OptionChainSnapshot(
                source="openalgo", source_instance=self.source_instance,
                underlying=str(data.get("underlying") or underlying).upper(), underlying_exchange=exchange.upper(),
                options_exchange="NFO" if exchange.upper() in {"NSE", "NSE_INDEX", "NFO"} else "BFO",
                expiry_date=exp, underlying_ltp=float(data["underlying_ltp"]), atm_strike=float(data["atm_strike"]),
                as_of_ns=now, received_ns=now, rows=tuple(rows), provider_payload_hash=_payload_hash(data),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenAlgoProtocolError(f"invalid option chain response: {type(exc).__name__}") from exc

    def multi_option_greeks(
        self,
        symbols: Sequence[tuple[str, str]],
        *,
        interest_rate_pct: float = 0.0,
        forward_price: float | None = None,
        underlying_symbol: str | None = None,
        underlying_exchange: str | None = None,
        expiry_time: str | None = None,
        batch_size: int = 100,
    ) -> tuple[Greeks, ...]:
        if batch_size < 1 or batch_size > 500:
            raise ValueError("batch_size must be 1..500")
        results: list[Greeks] = []
        for start in range(0, len(symbols), batch_size):
            part = symbols[start:start + batch_size]
            items: list[dict[str, Any]] = []
            for symbol, exchange in part:
                item: dict[str, Any] = {"symbol": symbol, "exchange": exchange}
                if forward_price is not None:
                    item["forward_price"] = forward_price
                if underlying_symbol:
                    item["underlying_symbol"] = underlying_symbol
                if underlying_exchange:
                    item["underlying_exchange"] = underlying_exchange
                if expiry_time:
                    item["expiry_time"] = expiry_time
                items.append(item)
            payload: dict[str, Any] = {"symbols": items, "interest_rate": interest_rate_pct}
            data = self._post("multioptiongreeks", payload)
            rows = data.get("data") or []
            if not isinstance(rows, list):
                raise OpenAlgoProtocolError("multioptiongreeks data must be an array")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                status = str(row.get("status", "error")).lower()
                if status != "success":
                    continue
                gr = row.get("greeks") or {}
                try:
                    results.append(Greeks(
                        symbol=str(row["symbol"]), strike=float(row["strike"]), option_type=OptionType(str(row["option_type"]).upper()),
                        days_to_expiry=float(row.get("days_to_expiry") or 0), forward_price=float(row.get("spot_price") or forward_price or 0),
                        option_price=float(row.get("option_price") or 0), implied_volatility_pct=float(row.get("implied_volatility") or 0),
                        delta=float(gr.get("delta") or 0), gamma=max(float(gr.get("gamma") or 0), 0.0),
                        theta_per_day=float(gr.get("theta") or 0), vega_per_vol_point=float(gr.get("vega") or 0), rho=float(gr.get("rho") or 0),
                        model="OPENALGO_BLACK76", status="VALID" if float(row.get("implied_volatility") or 0) > 0 else "PARTIAL",
                        reason=str(row.get("note") or "")[:300],
                    ))
                except (KeyError, ValueError, TypeError):
                    continue
        return tuple(results)

    def greeks_for_chain(
        self,
        chain: OptionChainSnapshot,
        *,
        interest_rate_pct: float = 0.0,
        forward_symbol: str | None = None,
        batch_size: int = 100,
    ) -> tuple[Greeks, ...]:
        symbols: list[tuple[str, str]] = []
        for row in chain.rows:
            if row.ce and row.ce.ltp > 0:
                symbols.append((row.ce.symbol, chain.options_exchange))
            if row.pe and row.pe.ltp > 0:
                symbols.append((row.pe.symbol, chain.options_exchange))
        return self.multi_option_greeks(
            symbols, interest_rate_pct=interest_rate_pct,
            underlying_symbol=forward_symbol or chain.underlying,
            underlying_exchange=chain.options_exchange if forward_symbol else chain.underlying_exchange,
            batch_size=batch_size,
        )
