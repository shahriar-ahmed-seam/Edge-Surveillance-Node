# Generates the mosquitto password file with hashed credentials.
# Run once before `docker compose up`. Requires Docker.
#
# Creates two users:
#   edge       / edge-secret        (edge agents publish)
#   ingestion  / ingestion-secret   (backend subscribes)

$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot

docker run --rm -v "${dir}:/work" eclipse-mosquitto:2 sh -c `
  "mosquitto_passwd -b -c /work/passwd edge edge-secret && mosquitto_passwd -b /work/passwd ingestion ingestion-secret"

Write-Host "Created $dir/passwd with users: edge, ingestion"
