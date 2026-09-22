# P6-F3C — Privileged Read-only Gap Closure

**Status:** privileged read-only inventory complete; no mutation authorized
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

The collector requires the explicit `--privileged-readonly` mode. Before any
collection probe it executes only `sudo -n true`, accepting an already-valid
operator ticket. If that preflight fails, it emits a fail-closed report and
starts no privileged collection. It never asks for, receives, stores or
transmits a password, and never falls back to a broader command.

The intended operator sequence is outside this program: authorize a temporary
ticket interactively with `sudo -v`, run the collector immediately, and then
invalidate the ticket with `sudo -k`. The collector itself always uses
non-interactive `sudo -n`.

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
to the approved host and invoke it with
`--privileged-readonly --json`, after the operator has authorized the temporary
ticket in the same session. It must capture only its sanitized report, must not
copy files to the host, and must not execute any command outside the program's
allowlist.

## VPS findings — operator-provided session evidence

The following observations were supplied from the authorized read-only session
and its terminal capture. This document records the findings without storing
public IP addresses, secret values, private-key material, environment values,
or database contents. They are evidence for planning only and do not authorize
any change.

| Area | Observed | Expected / drift | Proposed change for later review | Risk / rollback |
| --- | --- | --- | --- | --- |
| TCP/9090 | Cockpit; `cockpit.socket` enabled; UFW permits IPv4 and IPv6 exposure | Host administration interface is reachable beyond the SSH channel; exposure is outside the minimal BankCore gateway contract | Confirm legitimate operator use and access controls; consider restricting/removing public exposure only in a separately approved change | Locking out host administration is possible; retain an alternate console/SSH recovery path and restore the prior rule if validation fails |
| TCP/80, 443 | Host Nginx listens on the public web ports | Matches the expected public gateway boundary | Preserve as the intended public entry point; validate proxy and TLS behavior during a planned cutover | Public access interruption; revert the Nginx config/proxy pointer using a reviewed backup |
| TCP/8080 | `bankcore-nginx` is Docker-published on all IPv4/IPv6 interfaces; host Nginx proxies to `127.0.0.1:8080` | Docker publication is broader than the loopback-only upstream path expected by the gateway model | In a separate approved change, bind the container port to loopback or remove the host publication if the proxy topology permits | Could break inbound traffic or health checks; restore the previous binding/proxy mapping and verify externally |
| TLS | A currently valid certificate covers `bankcore.vortexsoftware.tech` | TLS is present; exact issuer/expiry metadata are intentionally not repeated here | Preserve the certificate lifecycle and confirm renewal ownership before any proxy change | TLS outage/renewal failure; retain the existing certificate/config and a tested proxy rollback |
| Docker topology | Current stack is rootful; PostgreSQL and Redis are not published to host ports; containers use `restart=unless-stopped` | Rootful operation differs from the P6-F1/F2 target; data services remain internal as expected | Do not convert the live stack in place; prepare and validate a parallel rootless environment before any cutover | Data/service outage or ownership mismatch; keep the existing stack and volumes intact until rollback is proven |
| Application containers | Auth and Transactions use mutable `latest` image references and writable (`rw`) source-code bind mounts | Conflicts with immutable digest releases and immutable application artifacts | Replace only through a verified P6-D release and a separately reviewed blue/green cutover | Release mismatch or failed startup; switch proxy/current pointer back to the retained old stack |
| Configuration metadata | `.env` exists with mode `0600`, owner `deploy`; legacy configuration contract includes the variable name `JWT_SECRET_KEY` | File permissions are restrictive, but owner/contract differ from the planned secret boundary; no secret values were read | Design a new secret injection/ownership contract; rotate only as a separately approved operation | Authentication outage or accidental credential invalidation; preserve a secured recovery copy and validate new credentials before cutover |
| Backups | No automated BankCore backup was confirmed in the inspected timers, cron entries, and audited paths | Backup capability remains unproven; this is not proof that no backups exist elsewhere | Locate the authoritative backup destination/schedule and perform a restore test before production cutover | Irrecoverable financial data loss; no cutover until a verified backup and restore path exist |
| Sudo ticket | Operator reports that `sudo -k` invalidated the ticket; the subsequent non-interactive sudo check failed with “interactive authentication is required” | Temporary authorization was discarded as intended | None | No host change; privileged evidence collection ends with the ticket invalidated |

### Consolidated review

**Observed:** the live host is a pre-P6 deployment consisting of Auth,
Transactions, PostgreSQL, Redis and Nginx; Cockpit is exposed on TCP/9090;
Nginx handles public 80/443 and proxies to loopback TCP/8080 while Docker also
publishes that container port on all interfaces. PostgreSQL/Redis ports are not
published. Application containers use `latest`, writable code mounts and
`unless-stopped` restart policy. The `.env` file metadata is restrictive, but
the configuration contract is legacy.

**Expected:** immutable image digests, a least-exposure gateway, private data
services, explicit secret ownership, tested backups, and a separately
provisioned rootless deployment path.

**Drift:** public administration exposure on 9090; the extra all-interface
8080 binding; mutable images and writable source mounts; rootful Docker; legacy
secret/config ownership; and backup/restore not verified.

**Proposed change:** prepare a parallel BankCore environment, establish and
test backups first, validate release digests and new secret injection, then
plan a controlled proxy cutover. Any restriction of Cockpit/9090 or Docker
8080 publication requires its own explicit reviewed change and recovery path.

**Risk:** changing firewall, proxy bindings, credentials or Docker mode in
place could interrupt access or financial service. Backup absence remains
unverified beyond the inspected sources.

**Rollback:** keep the current stack, volumes, Nginx config and access path
unchanged until parallel validation is complete; retain an alternate host
console/SSH path; reverse only individually approved proxy/network changes.
No rollback or mutation was performed during this inventory.
