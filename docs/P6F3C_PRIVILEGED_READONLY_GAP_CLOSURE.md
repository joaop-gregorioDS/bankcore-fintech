# P6-F3C — Privileged Read-only Gap Closure

**Status:** local implementation; no mutation authorized  
**Purpose:** close the P6-F3B observation gaps with a minimal privileged
read-only allowlist.

## Scope

The probe is limited to evidence that the unprivileged `deploy` session could
not collect:

- owner/process information for listeners, especially TCP/9090;
- UFW, nftables, iptables and ip6tables rules;
- effective Nginx configuration, sanitized before reporting;
- public certificate metadata (subject, issuer, SANs and validity dates);
- backup/config/secrets file metadata only;
- root cron metadata and systemd services/timers;
- Docker root directory, version, security options, bindings, mounts and
  restart policies.

## Safety contract

`scripts/p6f3c-privileged-readonly.py` enforces:

- every privileged command is exactly `sudo -n <allowlisted-read-command>`;
- no interactive password prompt, shell, command substitution or redirection;
- no package manager, user/group, permission, filesystem, firewall, systemd,
  Nginx/TLS or Docker lifecycle operation;
- `find` is restricted to approved metadata roots and a metadata-only format;
- `openssl` may inspect only `fullchain.pem`/`cert.pem` under the Let's Encrypt
  live directory and only emits public certificate metadata;
- Docker inspection excludes environment fields and reads only image,
  restart-policy, mounts and port-binding metadata;
- private keys, `.env` values, secrets and database dumps are never queried or
  opened;
- `shell=False`, bounded timeouts and sanitized output are used for every
  probe.

If passwordless `sudo` is unavailable, the probe records the gap as
unverified and stops; it does not ask for a password or fall back to a broader
command.

## Report contract

The generated report keeps the same review structure:

`Observed → Expected → Drift → Proposed change → Risk → Rollback`

Unavailable probes remain explicitly unverified. No proposed item is an
authorization to change the host.

## Local validation

```text
python3 scripts/p6f3c-privileged-readonly.py --self-test
python3 -m py_compile scripts/p6f3c-privileged-readonly.py tests/test_p6f3c_privileged_readonly.py
```

Remote execution, when separately authorized, must stream this exact program
to the approved host and capture only its sanitized report. It must not copy
files to the host or execute any command outside the program's allowlist.
