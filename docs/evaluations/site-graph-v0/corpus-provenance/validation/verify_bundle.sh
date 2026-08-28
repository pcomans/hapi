#!/usr/bin/env bash
set -euo pipefail

bundle_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$bundle_root"

for command_name in gzip jq sort comm wc; do
  command -v "$command_name" >/dev/null || {
    echo "Missing required command: $command_name" >&2
    exit 1
  }
done

if command -v sha256sum >/dev/null; then
  sha256sum -c SHA256SUMS
elif command -v shasum >/dev/null; then
  shasum -a 256 -c SHA256SUMS
else
  echo "Missing required checksum command: sha256sum or shasum" >&2
  exit 1
fi

assert_rows() {
  local file="$1"
  local expected="$2"
  local actual
  gzip -t "$file"
  actual="$(gzip -cd "$file" | wc -l | tr -d ' ')"
  if [[ "$actual" != "$expected" ]]; then
    echo "$file: expected $expected rows, found $actual" >&2
    exit 1
  fi
}

assert_rows data/artifacts.ndjson.gz 36245
assert_rows data/raw_met.ndjson.gz 27969
assert_rows data/raw_brooklyn.ndjson.gz 8832
assert_rows data/raw_harvard.ndjson.gz 722

expected_keys="$(jq -c '.properties | keys' schema/artifacts.schema.json)"
gzip -cd data/artifacts.ndjson.gz \
  | jq -e --argjson expected "$expected_keys" \
      'type == "object" and (keys == $expected)' >/dev/null

for raw_file in data/raw_met.ndjson.gz data/raw_brooklyn.ndjson.gz data/raw_harvard.ndjson.gz; do
  gzip -cd "$raw_file" \
    | jq -e '
        type == "object"
        and (keys == ["data", "object_id"])
        and (.object_id | type == "string")
        and (.data | type == "object")
      ' >/dev/null
done

scratch_dir="$(mktemp -d)"
trap 'rm -rf "$scratch_dir"' EXIT

gzip -cd data/artifacts.ndjson.gz \
  | jq -r '[.source_museum, .source_id] | @tsv' \
  | LC_ALL=C sort > "$scratch_dir/canonical.tsv"

if [[ "$(LC_ALL=C sort -u "$scratch_dir/canonical.tsv" | wc -l | tr -d ' ')" != "36245" ]]; then
  echo "Canonical source keys are not unique" >&2
  exit 1
fi

for museum in met brooklyn harvard; do
  gzip -cd "data/raw_${museum}.ndjson.gz" \
    | jq -r --arg museum "$museum" '[$museum, .object_id] | @tsv' \
    | LC_ALL=C sort > "$scratch_dir/raw_${museum}.tsv"
done

cat "$scratch_dir"/raw_*.tsv | LC_ALL=C sort > "$scratch_dir/raw.tsv"
if [[ "$(LC_ALL=C sort -u "$scratch_dir/raw.tsv" | wc -l | tr -d ' ')" != "37523" ]]; then
  echo "Raw source keys are not unique" >&2
  exit 1
fi

if [[ -n "$(comm -23 "$scratch_dir/canonical.tsv" "$scratch_dir/raw.tsv")" ]]; then
  echo "At least one canonical record has no raw source record" >&2
  exit 1
fi

for museum in met harvard; do
  if [[ -n "$(comm -23 "$scratch_dir/raw_${museum}.tsv" "$scratch_dir/canonical.tsv")" ]]; then
    echo "Unexpected raw-only rows for $museum" >&2
    exit 1
  fi
done

brooklyn_raw_only="$(comm -23 "$scratch_dir/raw_brooklyn.tsv" "$scratch_dir/canonical.tsv" | wc -l | tr -d ' ')"
if [[ "$brooklyn_raw_only" != "1278" ]]; then
  echo "Expected 1278 filtered Brooklyn rows, found $brooklyn_raw_only" >&2
  exit 1
fi

echo "PASS: checksums, compression, JSON shape, counts, uniqueness, and canonical/raw linkage"
