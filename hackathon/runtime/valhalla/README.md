# Local Passo Livre routing runtime

Custom Valhalla built from `projects/valhalla` at repository revision `9f6f67e`.
The image includes one costing fix in `src/sif/pedestriancost.cc`: `max_grade`
(percent) is converted to degrees, the unit of edge slopes, and both uphill and
downhill magnitudes are compared against it. Before the fix, comparing the
negative `int` downhill slope with the unsigned cap rejected every edge with any
downhill, so pedestrian routes failed with error 442. The image tag still names
the base revision; rebuild with `setup.sh image` after pulling the fix.

The service publishes **http://127.0.0.1:8003**. Its container listens on 8002;
Compose maps host 8003 to that port. It is deliberately local to this machine.
Ben can use this base URL for a locally served app; no files in `hackathon/app/`
are modified by these scripts. A hosted HTTPS app needs separate HTTPS reachability.

## Repeat setup

Run from the repository root:

```bash
bash hackathon/runtime/valhalla/setup.sh image
bash hackathon/runtime/valhalla/setup.sh download
bash hackathon/runtime/valhalla/setup.sh config
bash hackathon/runtime/valhalla/setup.sh tiles
bash hackathon/runtime/valhalla/setup.sh start
bash hackathon/runtime/valhalla/setup.sh smoke
```

`image` compiles the checked-in custom source and its HTTP dependency with two
workers. It requires Docker, network access, several GB of free disk space and
time for a C++ build. The recipe is adapted from the vendored Dockerfile; it
sets concurrency before the dependency installer and retries package-index
fetches with caching disabled. Package signature/hash checks remain enabled.
The base image/package repositories are not digest-pinned, so future rebuilds
can differ; the tested image ID is recorded in `hackathon/docs/runtime-baseline.md`.

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

`config` generates the JSON from this source tree with explicit mounted paths.
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
docker compose -f hackathon/runtime/valhalla/compose.yml ps
curl --fail --max-time 5 http://127.0.0.1:8003/status
bash hackathon/runtime/valhalla/setup.sh smoke
docker compose -f hackathon/runtime/valhalla/compose.yml logs --tail 50 valhalla
```

The smoke check tests a Porto pedestrian route, `/trace_attributes` using its
returned geometry, and one known slope-cap case (Aliados: `max_grade` 8 allowed,
6 blocked). It does not validate wheelchair safety, barrier avoidance, the
frontend, or broker integration. Costing changes need only `image` and a
container restart; tiles are rebuilt only when the data or elevation changes.

To stop just this routing service without deleting data:

```bash
docker compose -f hackathon/runtime/valhalla/compose.yml stop
```

Coreflux remains the separate existing broker stack. Its browser WebSocket
transport and `access/barriers/<id>` exchange still need a separate integration
task. This runtime neither changes broker entities nor provisions users.
