# Deployment notes

## Caddy
- `Caddyfile` → `/etc/caddy/Caddyfile`
- Token lives at `/etc/caddy/cf.env` (not in git) — Cloudflare API token with Zone:DNS:Edit on hoens.fun
- systemd override: `/etc/systemd/system/caddy.service.d/override.conf` with `EnvironmentFile=/etc/caddy/cf.env`
- Caddy built with xcaddy to include `github.com/caddy-dns/cloudflare`

## Firewall (Helm/OPNsense)
- 10.6.66.40 allowed egress on UDP/TCP 53 (external DNS), TCP 80/443 (Let's Encrypt ACME)
- Required because default LAN policy routes DNS through Helm, which doesn't work for DNS-01 propagation checks

## Known gotchas
- If cert renewal ever fails with "timed out waiting for record to fully propagate,"
  check for stale _acme-challenge TXT records and delete them via Cloudflare API
