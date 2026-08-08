# pskreporter-local

![Compact clustered map view showing live stations and worked-status colors](docs/images/compact-map-view-clustered.png)

`pskreporter-local` is a local-first web application that combines recent amateur-radio reception reports from the documented [PSK Reporter XML query interface](https://www.pskreporter.info/pskdev.html) with your local ADIF log.

Its central purpose is to answer an immediately useful operating question: **Which stations are on the air right now that I have not worked?** The live table places current PSK Reporter activity beside your QSO history, making unworked stations—and stations worked on another band but not the current one—visible at a glance.

The application provides responsive table and map views without requiring a database or cloud account. Your ADIF log stays on the machine running the application and is read-only.

## Live activity meets your log

PSK Reporter can show that a station is transmitting or receiving now, while an ADIF log records whom you have worked in the past. Viewed separately, neither provides the complete operating picture. `pskreporter-local` brings them together in one table so you can quickly identify a potential new QSO while the station is active.

The **QSOs B/T** column compares each station with your log using `band/total` counts:

- `0/0` — you have never worked this station.
- `0/1` — you have worked the station once, but not on the current band.
- `1/1` — your one QSO with the station was on the current band.
- `2/5` — you have two QSOs on the current band and five across all bands.

This is particularly useful during short openings on bands such as 6 and 10 meters: a `0/0` or `0/n` station in the live reports is an immediate visual cue that there may be a new callsign or band contact available now.

![Compact table view with unworked stations highlighted in blue](docs/images/compact-table-view.png)

## Station Inspector

Click or tap a **QSOs B/T** count to open the Station Inspector. It keeps the live report context together with the station's individual contacts from your local ADIF log, and provides direct callsign copy and QRZ controls.

![Station Inspector opened over the individual station map](docs/images/map-station-inspector.png)

## Map view

The **Table** and **Map** buttons switch the filtered results between the sortable report table and a responsive station map. Table remains the default. Map markers and clusters use the same worked-before meaning as the table: blue is an unworked `0/0` station, yellow is a station worked on another band, green is worked on the current band, and gray means the ADIF log is unavailable. Click or tap a marker to open the same Station Inspector used by the table. After the map initially fits the available stations, its center and zoom remain under operator control as reports refresh, filters change, or the display switches between Table and Map.

The map's **Clustered / Individual** selector is remembered in the browser. Clustered is the default and combines nearby stations for a quieter regional view. Individual displays every mapped station and draws unworked markers above the other opportunity states. When multiple stations share an exact grid center, their markers are spread deterministically within the reported Maidenhead square so each remains selectable; the highest-priority opportunity stays at the true grid center.

The clustered view shown at the top of this README keeps a busy opening readable at continental scale. Individual view exposes every mapped station when the operator wants to inspect the activity inside those clusters:

![Individual map view showing every mapped station with unworked stations layered above the others](docs/images/compact-map-view-individual.png)

For a space-efficient operating view, **Station & Query** contains the large header, callsign, direction, intervals, ADIF controls, and advanced query options. It starts open on a fresh page and collapses after the first successful report request; later refreshes do not close it if the operator reopens it. **Filters & Request Details** contains the band and mode filters, mobile sort controls, and XML request trace. Its collapsed summary always shows the active filters and sort order, while result counts, refresh metadata, warnings, and the Table/Map selector remain visible above the operating view.

Stations are grouped by callsign and locator. Their marker is placed at the calculated center of the reported 2-, 4-, 6-, or 8-character Maidenhead grid, so its position is an approximation rather than an exact station location. The map summary reports results that cannot be plotted because the other station has no usable locator.

Leaflet and its marker-clustering extension are bundled with the application. The base-map tiles are loaded from OpenStreetMap only when Map is displayed, so that view requires network access to `tile.openstreetmap.org`; the table and Station Inspector continue to work if tiles are unavailable.

The same compact controls, marker modes, legend, and Station Inspector remain available on narrow mobile screens:

<img src="docs/images/mobile-map-view.png" alt="Mobile map view with compact query and results controls" width="430">

## Features

- Query the last 15, 30, or 60 minutes, with 15 minutes as the default.
- Automatically refresh reports every 5, 10, or 15 minutes, with 10 minutes as the default, and show the last successful display refresh in UTC.
- Keep the current table or map visible while refreshed reports are requested, replacing it only after a successful response and retaining it when a refresh fails.
- Select PSK Reporter's `Sent by`, `Recv by`, or both directions, with both selected initially.
- Show UTC report time, transmitter and receiver callsigns, both Maidenhead grids, sender region and DXCC, signal-to-noise ratio, derived amateur band, mode, and frequency in transceiver-style MHz.
- Copy the other station's callsign directly from a report row or the Station Inspector, including a fallback for browsers that restrict the modern clipboard API on local-network HTTP connections.
- Filter fetched results locally by band and mode.
- Sort every report column ascending or descending, with newest UTC report time as the default.
- Switch filtered results to a clustered, color-coded station map and open the Station Inspector from any marker.
- Distinguish empty results, upstream failures, and invalid XML.
- Cache equivalent upstream queries for at least five minutes.
- Inspect each upstream URL, response status, timing, size, parsed count, and raw XML.
- Configure the operator and service settings in a local JSON file.
- Offer the ten most recently queried callsigns as browser-local suggestions.
- Expose compatible PSK Reporter XML parameters in an expandable advanced-query panel.
- Load an operator-selected `.adi` or `.adif` log into memory and reload it manually.
- Compare every live report with that log and show current-band/all-band QSO counts for the other station.
- Click or tap a **QSOs B/T** count to inspect the station's live report details and its individual contacts from your local ADIF log.

## Requirements

- Python 3.11 or newer
- Network access to `https://retrieve.pskreporter.info`
- Optional for Map view: network access to `https://tile.openstreetmap.org`

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

Run the tests, then start the application on macOS or Linux:

```bash
.venv/bin/pytest
./run.sh
```

On Windows Command Prompt, use:

```bat
.venv\Scripts\python -m pytest
run.cmd
```

Both launchers run Uvicorn at `http://127.0.0.1:8765` with automatic reload enabled.

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Interactive API documentation is available at [http://127.0.0.1:8765/api/docs](http://127.0.0.1:8765/api/docs).

On first launch, **Station & Query** is expanded so the operator can confirm the callsign, report interval, refresh interval, and direction before fetching reports:

![First-launch Station and Query controls ready to fetch reports](docs/images/first-launch-query.png)

## Configuration

The application reads `config.json` from its working directory when it starts. The operator-specific file is ignored by Git; [config.example.json](config.example.json) is the safe template committed to the repository.

```json
{
  "default_callsign": "N0CALL",
  "app_contact": null,
  "adif_file_path": null,
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
| `adif_file_path` | `null` | Absolute path to an ADI log, or a path relative to `config.json`. |
| `cache_ttl_seconds` | `300` | Query-cache lifetime. Values below 300 are raised to 300. |
| `report_limit` | `1000` | Maximum reports requested per upstream query. |
| `http_timeout_seconds` | `10` | Upstream request timeout in seconds. |
| `max_xml_bytes` | `5000000` | Maximum accepted XML response size. |
| `query_url` | Official endpoint | Alternate compatible endpoint, primarily for testing. |

The file is optional; built-in defaults are used if it is absent. If it is present, its JSON must be valid. Unknown setting names, incorrect value types, and invalid default callsigns cause startup to fail with a configuration error so mistakes are visible immediately.

Host and port are server settings and therefore remain Uvicorn command-line arguments. Restart the application after changing `config.json`.

## ADIF log

Set `adif_file_path` to make a local ADI log available to the application:

```json
{
  "default_callsign": "N0CALL",
  "adif_file_path": "logs/operator.adi"
}
```

Relative paths are resolved from the directory containing `config.json`. Absolute paths are useful when the logging software writes elsewhere or the log is mounted from another machine.

The application reads the file at startup and stores its parsed QSO records plus a callsign-count index in memory—no database is used. The expandable **ADIF log** section displays the resolved path, load state, QSO count, file modification time, and a **Reload ADIF** button. Reload reads the file again after logging software changes it; automatic file watching is intentionally deferred.

The expanded **Options** panel keeps the advanced PSK Reporter parameters and ADIF status together without occupying space during normal operation:

![Expanded query options and a successfully loaded ADIF log](docs/images/adif-query-options.png)

When an ADI log is loaded, the report table's **QSOs B/T** column shows `band/total` logged contacts with the other station. For a `Sent by` report this is the receiver; for a `Recv by` report it is the sender. For example, `0/1` means no QSO on the report's current band and one QSO on another band; `2/5` means two on the current band and five across all bands; and `0/0` means the callsign has not been worked. An em dash means no usable ADI log has been loaded. Counts are case-insensitive but otherwise require an exact ADIF `CALL` match, and the band count uses the record's ADIF `BAND` field.

Click or tap any **QSOs B/T** value to open the Station Inspector. It combines the selected live report—direction, grid, location, time, sNR, band, mode, and frequency—with the station's individual logged QSOs, newest first. The first 10 contacts are shown initially, with a control to reveal the complete history. QSO date, UTC time, sNR, band, mode/submode, and frequency are read from the corresponding ADIF fields when present. No external station-profile service is queried.

Live signal reports use PSK Reporter's `sNR` XML attribute. Historical signal reports use the ADIF record's `SNR` field. Many logging programs do not export historical SNR, so an em dash in that column is normal.

Confirmed `0/0` stations—those with no matching QSO anywhere in the loaded ADIF log—receive a bright blue opportunity badge and row highlight. This treatment is not applied when the log is unavailable, so an em dash is never mistaken for a confirmed unworked station.

The path is on the machine running the Python service. If the browser and service are on different machines, copy, synchronize, or mount the ADI file where the service can read it. A missing file, permissions problem, or parse error is reported in the ADIF section without stopping PSK Reporter queries.

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

The primary callsign, direction, and report-interval controls produce `senderCallsign` or `receiverCallsign` and `flowStartSeconds`. The browser-only refresh interval controls when that query is repeated and does not change the upstream parameters. `appcontact` remains an application setting in `config.json`. `callback` is intentionally unavailable because it changes the response from XML to JavaScript, which is incompatible with the parser.

Every advanced option participates in the five-minute cache key. Equivalent options reuse a cached response; changing an upstream option produces a distinct PSK Reporter request.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for a generic installation on another machine, direct local-network serving, service-manager guidance, updates, and security considerations.

Run exactly one application worker in this release. The five-minute cache is stored in process memory, so multiple workers could make duplicate upstream requests.

## Current scope

Exact-call worked-before counts are displayed by current band and across all bands, but controlled portable/base-call matching is not yet implemented. The map plots the center of the other station's reported Maidenhead grid; it does not infer a location when that grid is absent. UDP, MQTT, external station-profile lookup, databases, cloud hosting, and multi-user access remain outside the current scope. Multi-hour history is also excluded because PSK Reporter's real-time XML query does not reliably return the complete requested interval.

Planned increments are:

1. Continue stabilizing the responsive table, map, and XML pipeline through live operating use.
2. Extend the in-memory ADIF counts with controlled portable-call matching and richer worked-before details.
3. Evaluate optional station-profile data without weakening the local-first design.

## Third-party components

The locally bundled map components are Leaflet 1.9.4 (BSD 2-Clause) and Leaflet.markercluster 1.4.1 (MIT). Their license texts are included in `pskreporter_local/static/vendor/`. Map data and imagery are provided by OpenStreetMap contributors under the attribution displayed on the map.

## License

MIT
