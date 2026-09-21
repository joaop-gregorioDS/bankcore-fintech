import argparse
import json
import re
from pathlib import Path


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_IMAGES = {"auth", "transactions", "risk", "audit"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a P6-D manifest from CI image fragments.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", required=True)
    args = parser.parse_args()

    fragments = sorted((args.input_dir / "fragments").glob("*.json"))
    if {path.stem for path in fragments} != EXPECTED_IMAGES:
        raise SystemExit("Release manifest must contain exactly auth, transactions, risk and audit fragments.")

    images = []
    for fragment_path in fragments:
        fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
        required = {"name", "image", "tag", "digest", "sbom"}
        if set(fragment) < required:
            raise SystemExit(f"Incomplete release fragment: {fragment_path}")
        digest = fragment["digest"]
        image = fragment["image"]
        if not DIGEST_RE.fullmatch(digest):
            raise SystemExit(f"Invalid digest in {fragment_path}")
        if not image.startswith("ghcr.io/joaop-gregoriods/bankcore-"):
            raise SystemExit(f"Unexpected registry image in {fragment_path}")
        if ":latest" in image or fragment["tag"] == "latest":
            raise SystemExit("latest is forbidden in a P6-D release manifest.")
        images.append(
            {
                "name": fragment["name"],
                "image": image,
                "tag": fragment["tag"],
                "digest": digest,
                "immutable_ref": f"{image}@{digest}",
                "sbom": fragment["sbom"],
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "release": args.release,
                "git_commit": args.commit,
                "repository": args.repository,
                "workflow": args.workflow,
                "images": sorted(images, key=lambda item: item["name"]),
                "verification": {
                    "registry": "ghcr.io",
                    "signature": "cosign-keyless",
                    "provenance": "github-artifact-attestation",
                    "sbom_format": "CycloneDX JSON",
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"P6D manifest written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
