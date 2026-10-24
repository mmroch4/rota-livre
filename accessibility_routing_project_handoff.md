# Accessibility-First Pedestrian Routing --- Project Handoff

**Last updated:** 24 October 2026

> **Status warning:** This is a handoff based on the terminal output and
> conversation, not proof that routing works end to end. The last
> `git commit` failed because Git author identity was missing. The
> subsequent push created the remote branch but reported `Total 0`; the
> project files may not yet be committed or uploaded.

## 1. Objective

Implement accessibility-first pedestrian routing using Valhalla and the
OpenStreetMap website.

Desired behavior: - A user selects a maximum allowed slope. - Edges
above that cap must not be used. - Among eligible routes, Valhalla
chooses according to its pedestrian costing model. - The cap must never
be relaxed automatically. - If no route exists under the cap, explain
that no route was found and let the user decide whether to raise the cap
manually.

The website currently has a temporary hardcoded `max_grade: 6` for
pedestrian requests. A user-facing setting and helpful no-route message
are not finished.

## 2. Relevant information

### 2.1 Repositories and important files

  -------------------------------------------------------------------------------------------------------------------
  Item                                Location
  ----------------------------------- -------------------------------------------------------------------------------
  Valhalla source checkout            `~/valhalla/valhalla-source`

  Modified Valhalla source            `src/sif/pedestriancost.cc`

  OpenStreetMap website checkout      `~/openstreetmap-website`

  Modified website file               `app/assets/javascripts/index_modules/directions/engines/fossgis_valhalla.js`

  Target GitHub repository            `https://github.com/mmroch4/scitech-2026`

  Local target clone                  `~/scitech-2026-upload`

  Branch created                      `add-accessibility-routing`

  Valhalla upstream remote            `https://github.com/valhalla/valhalla.git`

  Website upstream remote             `https://github.com/openstreetmap/openstreetmap-website.git`
  -------------------------------------------------------------------------------------------------------------------

Do not push project work to the two upstream repositories. The intended
destination is `mmroch4/scitech-2026`.

### 2.2 Valhalla code change

File: `src/sif/pedestriancost.cc`

The slope checks in `PedestrianCost::Allowed` and
`PedestrianCost::AllowedReverse` were uncommented. The diff also adds
this helper:

``` cpp
float grade_percent_to_degrees(uint32_t grade_percent) {
  return std::atan(static_cast<float>(grade_percent) / 100.0f) *
         180.0f / static_cast<float>(M_PI);
}
```

The helper is currently unused. **Do not assume the slope filtering is
correct yet.** There is an unresolved units/sign issue: - `max_grade_`
is configured as a percentage. - Slope accessors/setters/comments in
`DirectedEdge` appear to describe degrees, while `weighted_grade()` in
`src/skadi/util.cc` appears to calculate percentage grade
(`height difference * 100 / horizontal distance`). - `max_down_slope()`
is negative. Comparing it directly with a positive maximum grade using
`max_down_slope() > max_grade_` will not reject steep downhill values as
intended. - The 5-bit slope fields encode/quantize values, so verify the
actual units and ranges in this Valhalla version and its tests before
choosing a conversion. - Invalid elevation samples may result in parts
of a segment being treated as zero slope. Investigate how missing
elevation is represented and decide explicitly how unknown slopes should
be handled.

Observed defaults in the source: - `kDefaultMaxGradeFoot = 90` -
`kDefaultMaxGradeWheelchair = 12`

### 2.3 Website code change

File:
`app/assets/javascripts/index_modules/directions/engines/fossgis_valhalla.js`

The request payload adds `costing_options.pedestrian.max_grade = 6` only
when `costing === "pedestrian"`. This is hardcoded for testing.

The response handler currently throws a generic `Error` when
`trip.status !== 0`. It does not yet provide a specific no-route message
or a manual cap-adjustment flow.

### 2.4 Original development machine: paths and containers

These are machine-specific paths; they will not automatically exist on a
new PC.

  --------------------------------------------------------------------------------------------------------------
  Item                                Original value
  ----------------------------------- --------------------------------------------------------------------------
  Valhalla custom data                `/home/peteryellow/valhalla/custom_files`

  Original Valhalla config            `/home/peteryellow/valhalla/custom_files/valhalla.json`

  Andorra OSM PBF                     `/home/peteryellow/valhalla/custom_files/andorra-latest.osm.pbf`

  Elevation file                      `/home/peteryellow/valhalla/custom_files/elevation_data/N42/N42E001.hgt`

  Original graph backup               `/home/peteryellow/valhalla/custom_files/backup-before-elevation`

  Temporary graph workspace           `/home/peteryellow/valhalla/custom_files/slope-build/`

  Temporary graph config              `/home/peteryellow/valhalla/custom_files/slope-build/valhalla.json`

  Local Valhalla image                `valhalla-slope:local`

  Test Valhalla container             `valhalla-slope-test`, port `8003`

  Original Valhalla container         `valhalla` (reported stopped/exited 137; original graph preserved)

  Website container                   `openstreetmap-website-web-1`, port `3000`

  Website database container          `openstreetmap-website-db-1`, port `54321`
  --------------------------------------------------------------------------------------------------------------

**Do not stop/remove the existing website containers or delete the
original graph/data.** The temporary service uses the graph in
`slope-build`, separate from the original graph.

### 2.5 Temporary graph build

The elevation-enhanced graph was built successfully in the temporary
workspace using these commands inside the Valhalla build environment:

``` bash
valhalla_build_tiles -c /custom_files/slope-build/valhalla.json -e build /custom_files/andorra-latest.osm.pbf
valhalla_build_elevation --from-tiles --decompress -c /custom_files/slope-build/valhalla.json -v
valhalla_build_tiles -c /custom_files/slope-build/valhalla.json -s enhance /custom_files/andorra-latest.osm.pbf
valhalla_build_extract -c /custom_files/slope-build/valhalla.json -v
```

The temporary service reported Valhalla 3.9.1 with seven tiles loaded.
That confirms the service/graph started, **not** that slope filtering is
correct. The graph covers the Andorra region, not the whole world.

## 3. Known problems / unfinished work

1.  **Slope units and downhill sign:** Verify units from code/tests,
    then fix comparisons in both forward and reverse pedestrian edge
    checks. Treat uphill and downhill correctly.
2.  **Unused helper:** `grade_percent_to_degrees()` is not called.
    Decide whether conversion is actually needed after confirming the
    stored units.
3.  **Missing elevation:** Establish how unknown elevation affects the
    grade values. Do not silently assume unknown terrain is flat without
    a deliberate decision.
4.  **Hardcoded cap:** Website uses `max_grade: 6`; no finished user
    setting yet.
5.  **Poor no-route handling:** A nonzero `trip.status` currently
    produces a generic error. Add a clear message and manual cap
    adjustment; never auto-relax the cap.
6.  **End-to-end tests not confirmed:** Test gentle routes, steep
    uphill, steep downhill, and missing-elevation areas. Confirm no edge
    above the cap is used and no automatic fallback raises the cap.
7.  **URL/configuration:** Verify the website's
    `OSM.FOSSGIS_VALHALLA_URL` points to the intended service. The test
    service is on port `8003`; the website is on port `3000`.
8.  **Machine-specific build:** The Docker image, graph tiles, elevation
    data, and config are local artifacts, not guaranteed to be in
    GitHub.
9.  **GitHub upload may be incomplete:** Commit failed due to missing
    author identity. A later push created the branch but showed
    `Total 0`, so the staged files likely were not pushed as a commit.
10. **Large/generated files:** The source trees were copied into
    `projects/valhalla/` and `projects/openstreetmap-website/`. `.git`,
    `node_modules`, `vendor`, `log`, `tmp`, `storage`, `.bundle`, and
    the nested duplicate `openstreetmap-website/` folder were excluded
    during the copy. Check staged files and large assets before
    committing.

## 4. Running on the original development PC

### 4.1 Check Docker and containers

``` bash
docker ps -a
docker images | grep valhalla
```

Do not stop or remove the website containers.

### 4.2 Start the temporary Valhalla service

Check it:

``` bash
docker ps -a --filter name=valhalla-slope-test
```

If the container exists but is stopped:

``` bash
docker start valhalla-slope-test
```

If it does not exist, and the image and graph files still exist,
recreate it:

``` bash
docker run -d \
  --name valhalla-slope-test \
  -p 8003:8003 \
  -v /home/peteryellow/valhalla/custom_files:/custom_files \
  --entrypoint valhalla_service \
  valhalla-slope:local \
  /custom_files/slope-build/valhalla.json 1
```

If the name is already in use, inspect the existing container instead of
deleting it.

Check service status:

``` bash
curl http://localhost:8003/status
```

### 4.3 Check the website

``` bash
docker ps --filter name=openstreetmap-website
```

Open `http://localhost:3000` in a browser. The website must be
configured to reach the test Valhalla service. Do not assume
`localhost:8003` works from inside a separate container: inside a
container, `localhost` means that container itself. Use the correct
shared Docker network/service name or host address.

The exact config setting for `OSM.FOSSGIS_VALHALLA_URL` was not captured
here; inspect the website configuration and verify connectivity before
testing.

### 4.4 Logs and direct route request

``` bash
docker logs --tail=200 valhalla-slope-test
docker logs --tail=200 openstreetmap-website-web-1
```

Example request shape (coordinates are illustrative and must be replaced
with two valid points in the loaded Andorra graph):

``` bash
curl -sS http://localhost:8003/route \
  -H 'Content-Type: application/json' \
  -d '{
    "locations": [
      {"lat": 42.50, "lon": 1.52},
      {"lat": 42.51, "lon": 1.53}
    ],
    "costing": "pedestrian",
    "costing_options": {
      "pedestrian": {
        "max_grade": 6
      }
    },
    "units": "kilometers"
  }'
```

A successful route response alone does not prove that the cap works.
Test known uphill and downhill cases.

## 4.5. Running on a different PC without Docker installed

The source code alone is not enough to reproduce the original runtime. A
new machine needs Docker, a built Valhalla image, OSM and elevation
inputs, a generated graph, config files, and a configured
website/database.

### A. Install prerequisites

On a fresh Linux PC: 1. Install Git. 2. Install Docker Engine and the
Docker Compose plugin using the official instructions for that Linux
distribution. 3. Start the Docker service and ensure your user can run
Docker. 4. Ensure enough disk space for the source trees, build
dependencies, PBF/elevation inputs, and graph tiles.

Verify:

``` bash
git --version
docker --version
docker compose version
docker run --rm hello-world
```

Installation instructions vary by operating system; do not assume one
universal installation command.

### B. Download the project branch

Only after the commit has actually been pushed:

``` bash
git clone --branch add-accessibility-routing \
  https://github.com/mmroch4/scitech-2026.git scitech-2026
cd scitech-2026
```

The source copies should be under:

``` text
projects/valhalla/
projects/openstreetmap-website/
```

If the branch has no commit containing these files yet, finish section 5
on the original PC first.

### C. Build Valhalla

The local image was called `valhalla-slope:local`, but the exact Docker
build command/build context was not recorded. On the original PC,
inspect how it was built:

``` bash
cd ~/valhalla
find . -maxdepth 3 \( -iname 'Dockerfile*' -o -iname '*docker*' \) -type f
docker image inspect valhalla-slope:local
```

Use the actual Dockerfile/build instructions to recreate the image on
the new machine. Do not assume that a generic `docker build` from the
copied source root will work.

### D. Obtain data and build a graph

The original inputs were: -
`/home/peteryellow/valhalla/custom_files/andorra-latest.osm.pbf` -
`/home/peteryellow/valhalla/custom_files/elevation_data/N42/N42E001.hgt` -
`/home/peteryellow/valhalla/custom_files/slope-build/valhalla.json`

These are not guaranteed to be in the GitHub repo. Obtain suitable OSM
PBF and elevation data, create a Valhalla config with valid paths, then
follow the graph-building sequence in section 2.5. Container paths must
match the Docker volume mounts. Do not copy the old absolute
`/home/peteryellow/...` paths unchanged unless they are valid on the new
machine.

### E. Start the website and database

Inspect `projects/openstreetmap-website/docker-compose.yml`,
`Dockerfile`, README, and environment configuration before starting it.
Follow the website's documented setup, including database initialization
and required environment variables. `docker compose up` by itself may
not complete first-time setup.

Do not commit secrets, `.env` files, local databases, logs, or generated
dependencies.

### F. Connect website to Valhalla

Configure the website's Valhalla URL to reach the test service.
Containers may need a shared Docker network and service/container
hostname. Verify the URL and connectivity from the website container.
The exact setting was not recorded in this handoff, so search the
website configuration for `OSM.FOSSGIS_VALHALLA_URL`.

### G. Validation checklist

-   Gentle-slope route succeeds.
-   Route requiring an edge above the cap is rejected or rerouted.
-   Uphill and downhill caps both work.
-   Missing elevation is handled deliberately.
-   No-route response is clear.
-   The cap is never automatically raised.
-   Manually changing the cap submits that exact new value.

## 5. Finish the GitHub upload

The commit failed with `Author identity unknown`. The following push
created the remote branch but reported `Total 0`, so the project files
may still be only staged locally.

On the original PC:

``` bash
cd ~/scitech-2026-upload
git config user.name "YOUR NAME"
git config user.email "YOUR_GITHUB_EMAIL"
git status
```

Replace placeholders with the name and email you want recorded in
commits. These settings apply only to this repository.

Then:

``` bash
git commit -m "Add Valhalla and OpenStreetMap accessibility routing work"
git push -u origin add-accessibility-routing
```

If Git says there is nothing to commit, inspect:

``` bash
git status --short
git log -1 --oneline
git ls-files projects | head
```

Then review the branch here:

https://github.com/mmroch4/scitech-2026/pull/new/add-accessibility-routing

## 6. Recommended next steps

1.  Complete the commit and push.
2.  Verify slope units and downhill comparisons.
3.  Test known routes, including missing-elevation cases.
4.  Replace the hardcoded cap with a user setting.
5.  Add a clear no-route message and manual cap adjustment without
    automatic relaxation.
6.  Record the exact image-build and fresh-machine setup commands after
    verifying them.

## 7. Confirmation status

**Observed/confirmed in the conversation** - Both local source files
were modified. - The temporary graph build sequence completed on the
original machine. - The temporary Valhalla service reported version
3.9.1 and seven loaded tiles. - Website containers were reported running
on ports 3000 and 54321. - The GitHub branch was created remotely.

**Not confirmed** - That a commit containing the project files
succeeded. - That both source trees are actually present on GitHub. -
That slope filtering correctly enforces the cap. - That unknown
elevation is handled safely. - That the website reaches the intended
Valhalla test service. - That end-to-end tests pass. - That a fresh PC
can run the system without extra configuration or data.

This handoff deliberately distinguishes observed facts from work that
remains to be verified.
