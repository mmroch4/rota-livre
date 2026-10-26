#!/usr/bin/env bash
# Explicit stages; never downloads or rebuilds data as a side effect of startup.
set -euo pipefail
runtime_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$runtime_dir/../.." && pwd)"
image=passolivre-valhalla:9f6f67e
data_dir="$runtime_dir/data"
# Git Bash on Windows rewrites arguments that look like paths (/data/valhalla/... becomes C:/.../Git/data/...),
# which breaks the container paths; turn that off and hand host paths to Windows Python in its own form.
export MSYS_NO_PATHCONV=1
host_path() { if command -v cygpath >/dev/null; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
mkdir -p "$data_dir"

case "${1:-}" in
  image)
    docker build -f "$runtime_dir/Dockerfile" --build-arg CONCURRENCY=2 \
      --build-arg VERSION_MODIFIER=passolivre-9f6f67e \
      -t "$image" "$repo_dir/projects/valhalla"
    ;;
  download)
    # Refuse to replace an existing dataset silently.
    test ! -e "$data_dir/Porto.osm.pbf"
    curl -fL --retry 2 --max-time 180 \
      https://download.bbbike.org/osm/bbbike/Porto/Porto.osm.pbf \
      -o "$data_dir/Porto.osm.pbf.part"
    curl -fL --retry 2 --max-time 30 \
      https://download.bbbike.org/osm/bbbike/Porto/CHECKSUM.txt \
      -o "$data_dir/CHECKSUM.txt"
    python3 - "$(host_path "$data_dir")" <<'PY'
import hashlib
from pathlib import Path
import sys
data = Path(sys.argv[1])
expected = next(line.split()[0] for line in (data / "CHECKSUM.txt").read_text().splitlines()
                if line.split()[-1] == "Porto.osm.pbf")
actual = hashlib.md5((data / "Porto.osm.pbf.part").read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit("Published PBF checksum mismatch; leaving .part for inspection")
(data / "Porto.osm.pbf.part").rename(data / "Porto.osm.pbf")
PY
    python3 "$(host_path "$repo_dir/projects/valhalla/scripts/valhalla_build_elevation")" \
      --from-bbox=-8.82,40.90,-8.2,41.42 --outdir "$(host_path "$data_dir/elevation")" \
      --decompress --parallelism 2 -v
    ;;
  config)
    test ! -e "$data_dir/valhalla.json"
    python3 "$(host_path "$repo_dir/projects/valhalla/scripts/valhalla_build_config")" \
      --mjolnir-tile-dir /data/valhalla/tiles \
      --mjolnir-tile-extract /data/valhalla/tiles.tar \
      --mjolnir-concurrency 2 --mjolnir-max-cache-size 268435456 \
      --additional-data-elevation /data/valhalla/elevation \
      --service-limits-max-exclude-polygons-vertices 1000 \
      --service-limits-max-exclude-polygons-length 50000 \
      --httpd-service-listen 'tcp://*:8002' > "$data_dir/valhalla.json"
    ;;
  tiles)
    test -s "$data_dir/Porto.osm.pbf"
    test -s "$data_dir/valhalla.json"
    test -s "$data_dir/elevation/N40/N40W009.hgt"
    test -s "$data_dir/elevation/N41/N41W009.hgt"
    test ! -e "$data_dir/tiles"
    docker run --rm --cpus=2 --memory=4g --user "$(id -u):$(id -g)" \
      -v "$(host_path "$data_dir"):/data/valhalla" --entrypoint valhalla_build_tiles \
      "$image" -c /data/valhalla/valhalla.json /data/valhalla/Porto.osm.pbf
    docker run --rm --cpus=2 --memory=2g --user "$(id -u):$(id -g)" \
      -v "$(host_path "$data_dir"):/data/valhalla" --entrypoint python3 \
      "$image" /usr/local/bin/valhalla_build_extract -c /data/valhalla/valhalla.json
    # (through python3: an image built from a Windows checkout has CRLF scripts, so the shebang fails)
    ;;
  start)
    test -s "$data_dir/tiles.tar"
    docker compose -f "$(host_path "$runtime_dir/compose.yml")" up -d
    ;;
  smoke)
    python3 "$(host_path "$runtime_dir/smoke.py")"
    ;;
  *)
    printf 'Usage: bash %s {image|download|config|tiles|start|smoke}\n' "$0" >&2
    exit 2
    ;;
esac
