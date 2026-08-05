# Deployment

`pskreporter-local` can run on any machine with Python 3.11 or newer and network access to PSK Reporter. It includes the Uvicorn command-line HTTP server, so a separate web-server product is optional.

These examples use a POSIX-style shell. Adjust executable paths for the host's shell or operating system.

## 1. Obtain and install the application

Clone the repository or unpack a release, then enter the application directory:

```bash
git clone REPOSITORY_URL pskreporter-local
cd pskreporter-local
```

Create a dedicated virtual environment and install the application:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
```

The installation account needs write access to the application directory only for installation and updates. The running application needs read access to the installed code and configuration.

## 2. Create the configuration

Copy the supplied template:

```bash
cp config.example.json config.json
```

Edit `config.json` before starting the application. At minimum, replace `N0CALL` with the operator's callsign:

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

`app_contact` may be `null` or a contact email address. The remaining defaults are appropriate for the first release and normally do not need adjustment.

The application looks for `config.json` in its working directory. A service manager must therefore use the directory containing this file as the process working directory. Restart the application after every configuration change.

The real `config.json` is ignored by Git, preventing an operator's callsign or contact address from being committed accidentally. Keep a separate protected backup if the host's deployment process replaces the entire application directory.

## 3. Start the command-line server

For access only from the host itself, bind Uvicorn to the loopback interface:

```bash
.venv/bin/python -m uvicorn pskreporter_local.app:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/` on that machine.

For direct access from other machines on a trusted local network, listen on all interfaces:

```bash
.venv/bin/python -m uvicorn pskreporter_local.app:app --host 0.0.0.0 --port 8765
```

Open the application from another machine using the server's real hostname or address:

```text
http://SERVER_HOSTNAME_OR_ADDRESS:8765/
```

The host firewall must permit inbound TCP traffic to the chosen port from the trusted network. `0.0.0.0` is a listening address, not an address to enter in a browser.

Do not use `python3 -m http.server`: it can serve static files but cannot run the `/api/reports` service that retrieves and normalizes PSK Reporter XML.

## 4. Verify the installation

Check the health endpoint:

```bash
curl http://SERVER_HOSTNAME_OR_ADDRESS:8765/api/health
```

A healthy instance returns JSON containing `"status":"ok"`. Then open the main page and confirm that:

- the callsign from `config.json` appears in the query form;
- a 15-minute request returns reports or a clear empty-result message; and
- the XML request trace shows the upstream request and response.

If startup reports a configuration error, validate the JSON syntax and setting names against `config.example.json`. The application deliberately rejects unknown keys and incorrectly typed values.

## 5. Run the application automatically

For a persistent installation, configure the platform's service manager or process supervisor with these properties:

- working directory: the directory containing `config.json`;
- command: `.venv/bin/python -m uvicorn pskreporter_local.app:app --host HOST --port PORT`;
- worker count: exactly one;
- restart after process failures and machine reboots; and
- capture standard output and error in the platform's logs.

Use `127.0.0.1` for `HOST` when an existing platform proxy will publish the application. Use `0.0.0.0` for direct trusted-network access. A reverse proxy is not required, and this guide does not depend on a particular proxy or service manager.

The single-worker requirement matters because the five-minute PSK Reporter cache is held in process memory. Multiple workers would maintain separate caches and could repeat equivalent upstream queries.

## 6. Update an installation

Stop the application, preserve `config.json`, update and reinstall the code, then start it again:

```bash
git pull --ff-only
.venv/bin/python -m pip install .
```

Run the health check and a 15-minute query after every update. Because `config.json` is ignored by Git, a normal `git pull` leaves it in place.

## Security boundary

This release has no authentication and displays public reception reports. Limit direct access to a trusted network. Add the platform's normal authentication and HTTPS controls before publishing it on the internet or before adding private ADIF, logging, or callsign-account data.
