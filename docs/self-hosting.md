# Self-hosting

## Running persistently

### systemd (user service, Linux)

`~/.config/systemd/user/profdash.service`:

```ini
[Unit]
Description=profdash dashboard
After=network-online.target

[Service]
WorkingDirectory=/home/YOU/my-outreach
ExecStart=%h/.local/bin/prof serve --host 0.0.0.0 --port 8000 --no-open
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now profdash.service
loginctl enable-linger          # keep it running after logout
journalctl --user -u profdash -f
```

> systemd gotcha: `WorkingDirectory=` must NOT be quoted even when the
> path contains spaces; `Environment=VAR="..."` lines ARE quoted.

### Workers as timers

`~/.config/systemd/user/profdash-tasks.{service,timer}`:

```ini
# .service
[Unit]
Description=profdash agent task worker

[Service]
Type=oneshot
WorkingDirectory=/home/YOU/my-outreach
ExecStart=%h/.local/bin/prof worker tasks --batch-size 5

# .timer
[Unit]
Description=Run profdash task worker

[Timer]
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
```

Same pattern for Gmail scanning (`prof worker gmail-scan`,
`OnUnitActiveSec=30min`) — enable that timer only after `prof setup-gmail`.

### cron alternative

```cron
*/10 * * * * cd /home/YOU/my-outreach && prof worker tasks --batch-size 5 >> worker.log 2>&1
*/30 * * * * cd /home/YOU/my-outreach && prof worker gmail-scan >> gmail.log 2>&1
0 4 * * *   cd /home/YOU/my-outreach && prof backup >> backup.log 2>&1
```

## Security model (read this)

- **Password.** `prof set-password` protects the whole dashboard; browsers
  ask for it once per session (any username works). Only a salted scrypt
  hash is stored, in the database's `config` table. `prof set-password
  --clear` removes it. The `PROFDASH_PASSWORD` environment variable, if
  set, is used instead (handy for systemd units).
- `prof serve --host <anything but localhost>` refuses to start without a
  password (`--insecure` overrides that, for a LAN you fully trust).
- **The password travels with every request.** Over plain `http://` anyone
  on the same network can read it. On your own LAN that's usually
  acceptable; across the internet, always put profdash behind HTTPS:
  Tailscale (`tailscale serve 8000`), Cloudflare Tunnel, or a reverse proxy
  (Caddy, nginx) with a certificate. Don't port-forward plain HTTP.
- Write requests (status changes, notes, tasks) from another website are
  rejected (same-origin check), so a malicious page open in your browser
  can't change your data.
- The Gmail token sits in `~/.config/profdash/` — file permissions are
  yours to keep tight.
- All writes are local SQLite. `prof backup` nightly is cheap insurance.

## LAN access

`prof serve --host 0.0.0.0` binds all interfaces (set a password first
with `prof set-password`); open the port if you run a firewall:

```bash
sudo ufw allow 8000/tcp    # example
```

## Multiple machines

The state is one SQLite file plus the token file. To move machines:
`prof backup`, copy the `.sqlite.gz`, restore by unzipping into
`data/profdash.sqlite` on the new machine.
