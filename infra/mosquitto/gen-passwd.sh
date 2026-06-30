#!/usr/bin/env bash
# Generates the mosquitto password file with hashed credentials.
# Run once before `docker compose up`. Requires Docker.
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"

docker run --rm -v "${dir}:/work" eclipse-mosquitto:2 sh -c \
  "mosquitto_passwd -b -c /work/passwd edge edge-secret && \
   mosquitto_passwd -b /work/passwd ingestion ingestion-secret"

echo "Created ${dir}/passwd with users: edge, ingestion"
