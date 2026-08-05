# pskreporter-local

A local-first web interface for exploring recent amateur-radio reception reports from the documented [PSK Reporter XML query interface](https://www.pskreporter.info/pskdev.html).

The first iteration provides a responsive report table, normalized JSON API, defensive XML parsing, band derivation, and a five-minute in-memory query cache. It runs on macOS for development and can be deployed unchanged to a Linux host on the local network.

## Current features

- Search by your callsign with the same 15-minute to 24-hour lookback choices as PSK Reporter.
- Choose PSK Reporter's `Sent by`, `Recv by`, or both directions together.
- Display report time in UTC, age, sender, receiver, receiver locator, frequency, band, and mode.
- Filter retrieved reports locally by band and mode without making another upstream request.
- Distinguish valid empty results, upstream service failures, and invalid XML responses.
- Cache each equivalent callsign, direction, and lookback query for at least five minutes.
- Preserve sender and receiver locators for the future map milestone.
- Expose `/api/health`, `/api/reports`, and interactive API documentation.

UDP, MQTT, ADIF, QRZ lookup, mapping, databases, and multi-user access are intentionally outside this iteration.

## Requirements

- Python 3.11 or newer
- Network access to `https://retrieve.pskreporter.info`

## Run locally on macOS or Linux

Create an isolated Python environment and install the application with its test tools:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -e '.[dev]'
```

Run the automated tests:

```bash
./.venv/bin/pytest
```

Start the development server:

```bash
./.venv/bin/uvicorn pskreporter_local.app:app --host 127.0.0.1 --port 8765 --reload
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/) and enter your callsign. The API documentation is available at [http://127.0.0.1:8765/api/docs](http://127.0.0.1:8765/api/docs).

`Sent by` queries PSK Reporter with `senderCallsign`. `Recv by` uses `receiverCallsign`. When both switches are selected, the service performs and caches the two documented queries separately, then merges duplicate reception records for display.

The expandable XML request trace shows each upstream URL, HTTP status, duration, response size, parsed-report count, cache state, and raw XML. `PSKR_APP_CONTACT`, when configured, is redacted from the displayed URL.

## Configuration

Configuration is read from environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PSKR_QUERY_URL` | Official query endpoint | Override only for testing or a compatible mirror. |
| `PSKR_CACHE_TTL_SECONDS` | `300` | Cache lifetime; values below 300 are raised to 300. |
| `PSKR_REPORT_LIMIT` | `1000` | Maximum reports requested from PSK Reporter. |
| `PSKR_HTTP_TIMEOUT_SECONDS` | `10` | Overall upstream HTTP timeout. |
| `PSKR_MAX_XML_BYTES` | `5000000` | Maximum accepted XML response size. |
| `PSKR_APP_CONTACT` | unset | Optional contact sent to PSK Reporter as `appcontact`. |

Host and port are Uvicorn settings rather than application environment variables. Keep the development server on `127.0.0.1`. The supplied Linux service also keeps FastAPI on loopback and publishes it through Nginx.

## Linux deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for a `systemd` and Nginx deployment at `http://10.176.1.6/`.

This release must run with one application worker because its cache is in memory. A later persistent or shared cache can safely support multiple worker processes.

## Project direction

Development proceeds in complete, verified milestones:

1. Responsive report table and normalized XML pipeline.
2. Responsive world map consuming the same normalized reports.
3. Read-only ADIF integration and worked-before indicators.

## License

MIT
