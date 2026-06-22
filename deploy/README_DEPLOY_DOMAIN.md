# Mosquito dashboard domain deploy (auto)

## Target
- Domain: `mosquito.vietsunbirdnest.com.au`
- Upstream app: `http://127.0.0.1:8787/dashboard_v9.html`

## 1) DNS (required first)
Create DNS record:
- `A mosquito.vietsunbirdnest.com.au -> 110.174.14.200`

Wait until DNS resolves.

## 2) Run one command on root-enabled host
```bash
cd /home/dung/.openclaw/workspace-VP2_codex/projects/mosquito_trap_dashboard/deploy
sudo bash deploy_mosquito_domain.sh mosquito.vietsunbirdnest.com.au 8787
```

## 3) Verify
```bash
bash verify_mosquito_domain.sh mosquito.vietsunbirdnest.com.au 8787
```

## Notes
- This session currently cannot use elevated permissions, so deployment must run on a root-enabled shell.
- Script provisions Nginx reverse-proxy + Let's Encrypt SSL + HTTPS redirect.
- If DNS still NXDOMAIN, SSL provisioning will fail until DNS propagates.
