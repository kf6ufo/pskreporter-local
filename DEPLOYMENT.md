# Linux deployment

This deployment serves the application at `http://10.176.1.6/` through Nginx. FastAPI remains bound to `127.0.0.1:8765`, so it is reachable only through the local reverse proxy.

The commands below target Debian or Ubuntu. Adapt package names and Nginx paths for another Linux distribution.

## 1. Prepare the server

Connect to the Linux host and install the required system packages:

```bash
ssh YOUR_LINUX_USER@10.176.1.6
sudo apt update
sudo apt install -y git nginx python3 python3-venv
```

Create a dedicated service account and clone the repository:

```bash
sudo useradd --system --home-dir /opt/pskreporter-local --shell /usr/sbin/nologin pskreporter
sudo git clone https://github.com/kf6ufo/pskreporter-local.git /opt/pskreporter-local
sudo chown -R pskreporter:pskreporter /opt/pskreporter-local
```

If the service account already exists, `useradd` will report that fact and can be skipped.

## 2. Install the application

```bash
sudo -u pskreporter python3 -m venv /opt/pskreporter-local/.venv
sudo -u pskreporter /opt/pskreporter-local/.venv/bin/python -m pip install --upgrade pip
sudo -u pskreporter /opt/pskreporter-local/.venv/bin/pip install /opt/pskreporter-local
```

Optionally identify yourself to the PSK Reporter operator by adding an email address to the systemd unit:

```ini
Environment=PSKR_APP_CONTACT=you@example.com
```

## 3. Install the systemd service

```bash
sudo cp /opt/pskreporter-local/deploy/pskreporter-local.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pskreporter-local
sudo systemctl status pskreporter-local
curl http://127.0.0.1:8765/api/health
```

Run exactly one application worker in this release. The five-minute cache is held in process memory, so multiple workers could independently query PSK Reporter.

View application logs with:

```bash
sudo journalctl -u pskreporter-local -f
```

## 4. Configure Nginx

If Nginx does not already serve a site on `10.176.1.6:80`:

```bash
sudo cp /opt/pskreporter-local/deploy/nginx-pskreporter-local.conf /etc/nginx/sites-available/pskreporter-local
sudo ln -s /etc/nginx/sites-available/pskreporter-local /etc/nginx/sites-enabled/pskreporter-local
sudo nginx -t
sudo systemctl reload nginx
```

If that address already has an Nginx site, merge the `location /` proxy settings into the existing server block instead of enabling a second block on the same address and port.

From the Mac, open:

```text
http://10.176.1.6/
```

The Linux firewall must allow TCP port 80 from the Mac's trusted LAN. The exact firewall rule depends on the server's firewall and network prefix; restrict it to the local network rather than opening it globally.

## 5. Update an installed copy

After changes have been committed and pushed:

```bash
cd /opt/pskreporter-local
sudo -u pskreporter git pull --ff-only
sudo -u pskreporter .venv/bin/pip install .
sudo systemctl restart pskreporter-local
curl http://127.0.0.1:8765/api/health
```

## Direct LAN test without Nginx

For a short-lived test only, FastAPI can listen directly on every server interface:

```bash
./.venv/bin/uvicorn pskreporter_local.app:app --host 0.0.0.0 --port 8765
```

Then browse to `http://10.176.1.6:8765/`. Do not use this development-style command as the permanent service.

## HTTPS and private data

The initial application displays public reception reports and contains no login. Before exposing it outside the trusted LAN, or before adding ADIF and QRZ data, add authentication and HTTPS. Nginx can later terminate HTTPS without changing the application URLs.
