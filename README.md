# pskreporter-local

`pskreporter-local` is a local-first web application for viewing recent amateur-radio reception reports from the documented [PSK Reporter XML query interface](https://www.pskreporter.info/pskdev.html).

The first release is intentionally table-focused. It provides a responsive live operating view without requiring a database, cloud account, or browser access to PSK Reporter itself.

## Features

- Query the last 15, 30, or 60 minutes, with 15 minutes as the default.
- Select PSK Reporter's `Sent by`, `Recv by`, or both directions.
- Show UTC report time, transmitter and receiver callsigns, both Maidenhead grids, sender region and DXCC, frequency in transceiver-style MHz, derived amateur band, and mode.
- Filter fetched results locally by band and mode.
- Distinguish empty results, upstream failures, and invalid XML.
- Cache equivalent upstream queries for at least five minutes.
- Inspect each upstream URL, response status, timing, size, parsed count, and raw XML.
- Configure the operator and service settings in a local JSON file.
- Offer the ten most recently queried callsigns as browser-local suggestions.
- Expose compatible PSK Reporter XML parameters in an expandable advanced-query panel.

## Requirements

- Python 3.11 or newer
- Network access to `https://retrieve.pskreporter.info`

## Quick start

Create a virtual environment and install the application with its test tools:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Create your local configuration:

```bash
cp config.example.json config.json
```

Edit `config.json` and replace `N0CALL` with your callsign. You may set `app_contact` to an email address or leave it as `null`.

Run the tests, then start the application:

```bash
.venv/bin/pytest
.venv/bin/python -m uvicorn pskreporter_local.app:app --host 127.0.0.1 --port 8765 --reload
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Interactive API documentation is available at [http://127.0.0.1:8765/api/docs](http://127.0.0.1:8765/api/docs).

## Configuration

The application reads `config.json` from its working directory when it starts. The operator-specific file is ignored by Git; [config.example.json](config.example.json) is the safe template committed to the repository.

```json
{
  "default_callsign": "N0CALL",
  "app_contact": null,
  "cache_ttl_seconds": 300,
  "report_limit": 1000,
  "http_timeout_seconds": 10,
  "max_xml_bytes": 5000000,
  "query_url": "https://retrieve.pskreporter.info/query"
}
```

| JSON setting | Default | Purpose |
| --- | --- | --- |
| `default_callsign` | `null` | Callsign initially shown in the query form. It can still be changed in the browser. |
| `app_contact` | `null` | Optional contact sent to PSK Reporter as `appcontact`; it is redacted in the displayed trace URL. |
| `cache_ttl_seconds` | `300` | Query-cache lifetime. Values below 300 are raised to 300. |
| `report_limit` | `1000` | Maximum reports requested per upstream query. |
| `http_timeout_seconds` | `10` | Upstream request timeout in seconds. |
| `max_xml_bytes` | `5000000` | Maximum accepted XML response size. |
| `query_url` | Official endpoint | Alternate compatible endpoint, primarily for testing. |

The file is optional; built-in defaults are used if it is absent. If it is present, its JSON must be valid. Unknown setting names, incorrect value types, and invalid default callsigns cause startup to fail with a configuration error so mistakes are visible immediately.

Host and port are server settings and therefore remain Uvicorn command-line arguments. Restart the application after changing `config.json`.

## How queries work

The browser talks only to the local FastAPI service. `Sent by` uses PSK Reporter's `senderCallsign` parameter; `Recv by` uses `receiverCallsign`. Selecting both performs and caches the two documented XML queries separately, then merges duplicate reports for display.

The XML trace shows the interval and report limit requested as well as the oldest report actually returned. If the configured limit is reached, the interface warns that results may be incomplete.

### Advanced query options

The collapsed **Advanced query options** panel exposes the compatible parameters from PSK Reporter's documented XML query interface:

| Parameter | Initial value | Effect |
| --- | --- | --- |
| `mode` | Any | Ask PSK Reporter for one mode. This is separate from the local results filter. |
| `frange` | Empty | Limit frequency in Hz using `lower-upper`, such as `14000000-14100000`. |
| `rptlimit` | `report_limit` from `config.json` | Limit returned reception reports for this query. |
| `lastseqno` | Empty | Return records at or above a sequence number. |
| `modify` | None | Set `grid` to interpret the entered callsign value as a grid square. |
| `rronly` | Enabled | Return reception-report records only. |
| `noactive` | Enabled | Exclude active-monitor records. |
| `nolocator` | Enabled | Include reports that do not contain a locator. |
| `statistics` | Disabled | Ask the upstream response to include statistical information. |

The primary callsign, direction, and lookback controls produce `senderCallsign` or `receiverCallsign` and `flowStartSeconds`. `appcontact` remains an application setting in `config.json`. `callback` is intentionally unavailable because it changes the response from XML to JavaScript, which is incompatible with the parser.

Every advanced option participates in the five-minute cache key. Equivalent options reuse a cached response; changing an upstream option produces a distinct PSK Reporter request.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for a generic installation on another machine, direct local-network serving, service-manager guidance, updates, and security considerations.

Run exactly one application worker in this release. The five-minute cache is stored in process memory, so multiple workers could make duplicate upstream requests.

## Current scope

UDP, MQTT, ADIF, QRZ lookup, mapping, databases, cloud hosting, and multi-user access are outside this first release. Multi-hour history is also excluded because PSK Reporter's real-time XML query does not reliably return the complete requested interval.

Planned increments are:

1. Complete and stabilize the responsive report table and XML pipeline.
2. Add read-only ADIF integration and worked-before indicators.
3. Consider mapping after the table and ADIF workflow are reliable.

## License

MIT
