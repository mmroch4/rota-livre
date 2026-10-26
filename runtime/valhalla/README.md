# Rota Livre's slope-aware Valhalla

Upstream [Valhalla](https://github.com/valhalla/valhalla) at commit `618cad5` (master, 19/10/2026) with one
costing fix, [`slope-cap.patch`](slope-cap.patch), in `src/sif/pedestriancost.cc`: `max_grade`
(percent) is compared with each edge's uphill and downhill slope in the direction
of travel, and under a cap (below the foot default of 90) edges in tiles built
without elevation are rejected. Edge slopes are labelled degrees in Valhalla's
headers but are stored as percent (rise over a 60 m posting, rounded up). Before the fix,
comparing the negative `int` downhill slope with the unsigned cap rejected every
edge with any downhill, so pedestrian routes failed with error 442. The image tag
names the upstream commit; rebuild with `setup.sh image` after changing the patch
(a full C++ build: ~40 min with two workers).

The service publishes **http://127.0.0.1:8003**. Its container listens on 8002;
Compose maps host 8003 to that port. It is deliberately local to this machine;
the hosted HTTPS app reaches it through the opt-in tunnel in `compose.tunnel.yml`.

## Repeat setup

Run from the repository root:

```bash
bash runtime/valhalla/setup.sh source
bash runtime/valhalla/setup.sh image
bash runtime/valhalla/setup.sh download
bash runtime/valhalla/setup.sh config
bash runtime/valhalla/setup.sh tiles
bash runtime/valhalla/setup.sh start
bash runtime/valhalla/setup.sh smoke
```

`source` fetches upstream Valhalla at the pinned commit with its submodules (depth 1, ~360 MB) into the ignored
`src/` and applies the patch; it refuses to run if `src/` exists. `image` compiles that tree and its HTTP
dependency with two
workers. It requires Docker, network access, several GB of free disk space and
time for a C++ build. The recipe is adapted from upstream's `docker/Dockerfile`; it
sets concurrency before the dependency installer and retries package-index
fetches with caching disabled. Package signature/hash checks remain enabled.
The base image/package repositories are not digest-pinned, so future rebuilds
can differ; the image built on 26/10/2026 with this recipe (ID `c306f82e8ad4`, version
`3.9.1-rota-livre-618cad5`) passes `setup.sh smoke`.

`download` gets the approximately 43 MB
[BBBike Porto OSM extract](https://download.bbbike.org/osm/bbbike/Porto/) and two
Tilezen/Mapzen Skadi elevation cells via Valhalla's checked-in downloader.
The region is west/south/east/north `-8.82,40.90,-8.2,41.42`. This is regional
coverage, not all of Portugal. Map data is © OpenStreetMap contributors, ODbL;
BBBike provides the extract. Elevation source/licensing information is maintained
by [Tilezen's terrain tiles project](https://github.com/tilezen/joerd).

Downloaded and generated files live in ignored `data/`. `data-manifest.json`
records the original download hashes; live upstream downloads can change.
The PBF is checked against the provider's published MD5 over HTTPS. The recorded
SHA-256 hashes identify the actual input bytes used in this session.

`config` generates the JSON with the script from `src/` and explicit mounted paths.
`tiles` runs the complete tile pipeline with the elevation files already present,
then creates the tile archive. It caps the builder at two CPUs and 4 GiB RAM.
The setup does not download the global timezone dataset or prepare an admin
database; time-dependent/administrative routing is outside this smoke baseline.
Graph-build warnings about those missing optional datasets must not be confused
with confirmation of those features.

The download, config and tile stages refuse to overwrite existing primary
artifacts. If a stage fails, inspect its output and preserve useful inputs before
retrying deliberately. `start` only starts the service; it never downloads data
or builds a graph. The service mounts data read-only and uses two CPUs / 2 GiB RAM.

## Existing runtime

```bash
docker compose -f runtime/valhalla/compose.yml ps
curl --fail --max-time 5 http://127.0.0.1:8003/status
bash runtime/valhalla/setup.sh smoke
docker compose -f runtime/valhalla/compose.yml logs --tail 50 valhalla
```

The smoke check tests a Porto pedestrian route and `/trace_attributes` on its
geometry, then the slope cap on known cases: a gentle route unchanged at its own
steepest grade, one ~13 % footway used above the cap and detoured below it both
uphill and downhill (default, forward-only and reverse-only searches), and the
São Bento → Batalha demo detour growing as the cap tightens. It asserts the cap on
interior edges only, because the origin and destination partial edges are not
capped. It does not validate wheelchair safety, barrier avoidance, the frontend,
or broker integration. Costing changes need only `image` and a
container restart; tiles are rebuilt only when the data or elevation changes.

To stop just this routing service without deleting data:

```bash
docker compose -f runtime/valhalla/compose.yml stop
```

The Coreflux broker is a separate stack (`broker/`); this runtime neither changes broker entities nor
provisions users.
