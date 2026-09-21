# P6-C — Immutable Images and Release Artifacts

P6-C proves the local supply-chain shape without publishing anything to a
registry. The runner is:

```text
python scripts/p6c-release.py
```

It builds the four BankCore images with OCI metadata, captures the actual
local SHA-256 identities, generates CycloneDX SBOMs with Docker Scout, creates
an immutable Compose override, runs the production-like bundle by digest, and
verifies that the image identity used by each container matches the release
manifest.

## Generated package

Artifacts are written below the ignored local path `artifacts/p6c/<release>/`:

```text
manifest.json
docker-compose.production.immutable.yml
reproducibility.json
checksums.sha256
sbom/
  auth.cdx.json
  transactions.cdx.json
  risk.cdx.json
  audit.cdx.json
```

The package includes the custom services and the pinned infrastructure images
used by the production-like bundle, including Nginx, PostgreSQL, Redis, Kafka,
OpenTelemetry Collector, Prometheus, and Grafana. The generated Compose
override replaces every runtime image with `repository@sha256:...`; no
`latest` reference is accepted in the release artifact.

## OCI metadata

The custom Dockerfiles receive only non-secret build arguments:

```text
org.opencontainers.image.source
org.opencontainers.image.revision
org.opencontainers.image.version
```

The runner checks those labels against the current Git commit and release
identifier. No runtime secret is passed as a build argument or written to an
image label.

## Rebuild interpretation

The runner rebuilds the Auth image with `--no-cache` and records the result in
`reproducibility.json`. A byte-identical result is reported when the content
identity matches. If it differs, the package records the two digests and the
reason P6-C does not claim byte-for-byte reproducibility: the current
Dockerfiles still consume external base-image and package-index inputs.

This is an explicit measurement, not an unverified reproducibility claim.
Formal pinning of every build input, provenance, signing, registry promotion,
and remote verification are deferred to P6-D.

## Safety checks

The runner rejects or scans for:

- `latest` image references in the release path;
- missing SHA-256 identities;
- missing or inconsistent OCI metadata;
- malformed CycloneDX SBOMs;
- secrets/private-key markers in image metadata, history, manifest, SBOMs, or
  checksums;
- a runtime container whose image ID differs from the manifest digest.

The release package is intentionally ignored by Git because local image
digests are host-specific until P6-D establishes registry publication and
signing.
