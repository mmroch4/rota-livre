// Accessible route planner: the person says where they want to go, sees the route (blue line + the streets it
// passes) and is guided along it with their live position. Routes come from Valhalla; barrier reports are shared
// through the Coreflux broker (MQTT over WebSocket).
"use strict";

const config = window.APP_CONFIG;
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const DEMO = params.has("demo"); // ?demo: fake position that walks along the route (for the pitch)

// ---------------------------------------------------------------------------------------------------------------
// Needs. Valhalla's pedestrian costing has two types: "wheelchair" (only hard surfaces) and "foot". Kerb height
// is not something Valhalla can filter on, so there is no option for it.

const PROFILES = {
    wheelchair: { maxGrade: 6, avoidSteps: true, avoidRoughSurface: true },
    walker: { maxGrade: 8, avoidSteps: true, avoidRoughSurface: true },
    stroller: { maxGrade: 10, avoidSteps: true, avoidRoughSurface: false },
    foot: { maxGrade: 8, avoidSteps: true, avoidRoughSurface: false },
};
const STORAGE_KEY = "access.needs";

const MAX_STEP_PENALTY = 43200; // seconds: Valhalla's upper bound (12 h), so steps are used only as a last resort
const GRADE_LIMIT = 15;         // highest slope the slider offers, in %
const BARRIER_RADIUS_M = 15;    // half the side of the square excluded around each barrier
const NO_ELEVATION = 32768;     // Valhalla's marker for "no elevation data" on an edge
const OFF_ROUTE_M = 35;         // further than this from the line counts as off the route
const ARRIVED_M = 20;
const REROUTE_EVERY_MS = 15000;

const BARRIER_KINDS = {
    works: "Obras ou andaime",
    blocked_sidewalk: "Passeio bloqueado",
    parked_car: "Carro em cima do passeio",
    broken_lift: "Elevador ou rampa avariados",
    damaged_pavement: "Piso danificado ou buraco",
    other: "Outro obstáculo",
};

// ---------------------------------------------------------------------------------------------------------------
// State

const state = {
    needs: null,
    from: null,        // {lat, lon, label}; null = the person's own position
    to: null,
    position: null,    // last fix {lat, lon, accuracy}
    route: null,       // see routeService.route
    guiding: false,
    following: true,
    offRouteCount: 0,
    lastRerouteAt: 0,
    arrived: false,
    mapPick: "to",     // what a tap on the map sets: "to" | "from" | "report" | null
    pendingReport: null,
    barriers: new Map(),
};

// ---------------------------------------------------------------------------------------------------------------
// Map and its layers

const map = L.map("map", { zoomControl: true }).setView(config.center, config.zoom);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const routeLayer = L.layerGroup().addTo(map);
const barrierLayer = L.layerGroup().addTo(map);
let passedLine = null;
let personMarker = null;
let accuracyCircle = null;
let fromMarker = null;
let toMarker = null;

const PERSON_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="3"/>'
    + '<path d="M12 9c-2 0-3.5 1.2-3.5 3v4h2v6h3v-6h2v-4c0-1.8-1.5-3-3.5-3z"/></svg>';

function pinIcon(text, cls) {
    return L.divIcon({ className: `pin ${cls}`, html: text, iconSize: [30, 30], iconAnchor: [15, 15] });
}

map.on("click", (e) => {
    const point = { lat: e.latlng.lat, lon: e.latlng.lng };
    if (state.mapPick === "report") openReportDialog(point);
    else if (state.mapPick === "from") pickFromMap("from", point);
    else if (state.mapPick === "to") pickFromMap("to", point);
});

map.on("dragstart", () => {
    if (!state.guiding) return;
    state.following = false;
    $("recenter-btn").hidden = false;
});

$("recenter-btn").addEventListener("click", () => {
    state.following = true;
    $("recenter-btn").hidden = true;
    if (state.position) map.setView([state.position.lat, state.position.lon], Math.max(map.getZoom(), 17));
});

// ---------------------------------------------------------------------------------------------------------------
// Screens

function showScreen(name) {
    for (const s of ["welcome", "plan", "route", "guide"]) $(`screen-${s}`).hidden = s !== name;
    $("report-section").hidden = name === "welcome";
    $("layout").classList.toggle("guiding", name === "guide");
    $("guide-banner").hidden = name !== "guide";
    if (name !== "guide") $("recenter-btn").hidden = true;
    state.mapPick = name === "plan" ? "to" : null;
    setSheetExpanded(false);
}

// ---------------------------------------------------------------------------------------------------------------
// Phones: the panel is a bottom sheet over a full-screen map. Closed, it shows the top of the current screen
// (down to the last [data-peek] element: the main button); open, it shows everything. The map's visible area
// always ends where the closed sheet starts, so the route and the person are never hidden under it.

const phone = window.matchMedia("(max-width: 760px) and (orientation: portrait)");
let sheetExpanded = false;
const SHEET_GAP = 16;

function currentScreen() {
    return document.querySelector(".screen:not([hidden])");
}

function setSheetExpanded(open) {
    sheetExpanded = open;
    if (!open) $("panel").scrollTop = 0;
    updateSheet();
}

function updateSheet() {
    const panel = $("panel");
    const layout = $("layout");
    if (!phone.matches) {
        layout.style.removeProperty("--sheet-h");
        panel.classList.remove("expanded");
        map.invalidateSize();
        return;
    }
    const screen = currentScreen();
    const peekEls = screen ? [...screen.querySelectorAll("[data-peek]")].filter((el) => el.offsetParent) : [];
    let peek = peekEls.length
        ? Math.max(...peekEls.map((el) => el.offsetTop + el.offsetHeight)) + SHEET_GAP
        : panel.scrollHeight;
    // Leave some map visible; a screen without a main button (welcome) may use the whole sheet.
    peek = Math.min(peek, Math.round(window.innerHeight * (peekEls.length ? 0.7 : 0.88)));
    const hasMore = panel.scrollHeight > peek + 4;
    $("sheet-handle").hidden = !hasMore;
    $("sheet-handle").setAttribute("aria-expanded", String(sheetExpanded));
    $("sheet-handle-text").textContent = sheetExpanded ? "Ver menos" : (screen && screen.dataset.more) || "Ver mais";
    panel.classList.toggle("expanded", sheetExpanded && hasMore);
    layout.style.setProperty("--sheet-h", `${peek}px`);
    map.invalidateSize();
}

// Tap the handle to open/close; or swipe it up/down.
let handleDragY = null;
let handleSwiped = false;
$("sheet-handle").addEventListener("pointerdown", (e) => { handleDragY = e.clientY; handleSwiped = false; });
$("sheet-handle").addEventListener("pointerup", (e) => {
    if (handleDragY === null) return;
    const dy = e.clientY - handleDragY;
    handleDragY = null;
    if (Math.abs(dy) > 30) {
        handleSwiped = true;
        setSheetExpanded(dy < 0);
    }
});
$("sheet-handle").addEventListener("click", () => {
    if (handleSwiped) {
        handleSwiped = false;
        return;
    }
    setSheetExpanded(!sheetExpanded);
});

// Content changes (search results, messages, the street list) change how much the closed sheet shows.
const sheetObserver = new ResizeObserver(() => { if (!sheetExpanded) updateSheet(); });
for (const s of document.querySelectorAll(".screen")) sheetObserver.observe(s);
phone.addEventListener("change", () => setSheetExpanded(false));
window.addEventListener("resize", () => updateSheet());

// ---------------------------------------------------------------------------------------------------------------
// Welcome: ask once how the person gets around, then remember it on this device.

for (const b of document.querySelectorAll("[data-profile]")) {
    b.addEventListener("click", () => {
        applyNeeds({ profile: b.dataset.profile, ...PROFILES[b.dataset.profile], avoidBarriers: true });
        saveNeeds();
        showScreen("plan");
        $("to-input").focus();
    });
}

function loadNeeds() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (saved && typeof saved.maxGrade === "number") return saved;
    } catch { /* private mode or blocked storage: ask again */ }
    return null;
}

function saveNeeds() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.needs)); } catch { /* not remembered, still works */ }
}

function applyNeeds(needs) {
    state.needs = needs;
    $("profile-select").value = needs.profile;
    $("profile-select").querySelector('option[value="custom"]').hidden = needs.profile !== "custom";
    $("grade-input").value = needs.maxGrade;
    $("grade-output").value = needs.maxGrade;
    $("steps-check").checked = needs.avoidSteps;
    $("surface-check").checked = needs.avoidRoughSurface;
    $("barriers-check").checked = needs.avoidBarriers;
}

// ---------------------------------------------------------------------------------------------------------------
// Advanced options

$("profile-select").addEventListener("change", (e) => {
    const p = PROFILES[e.target.value];
    if (!p) return;
    applyNeeds({ ...state.needs, profile: e.target.value, ...p });
    saveNeeds();
});

$("grade-input").addEventListener("input", (e) => { $("grade-output").value = e.target.value; });

for (const id of ["grade-input", "steps-check", "surface-check", "barriers-check"]) {
    $(id).addEventListener("change", () => {
        const needs = {
            maxGrade: Number($("grade-input").value),
            avoidSteps: $("steps-check").checked,
            avoidRoughSurface: $("surface-check").checked,
            avoidBarriers: $("barriers-check").checked,
        };
        needs.profile = Object.keys(PROFILES).find((name) => {
            const p = PROFILES[name];
            return p.maxGrade === needs.maxGrade && p.avoidSteps === needs.avoidSteps
                && p.avoidRoughSurface === needs.avoidRoughSurface;
        }) || "custom";
        applyNeeds(needs);
        saveNeeds();
    });
}

function describeNeeds(needs) {
    const parts = [`subidas até ${needs.maxGrade}%`];
    if (needs.avoidSteps) parts.push("sem escadas");
    if (needs.avoidRoughSurface) parts.push("piso regular");
    return parts.slice(0, -1).join(", ") + (parts.length > 1 ? " e " : "") + parts[parts.length - 1];
}

// ---------------------------------------------------------------------------------------------------------------
// Choosing the destination and the start

$("to-form").addEventListener("submit", (e) => {
    e.preventDefault();
    search($("to-input").value.trim(), $("to-results"), (place) => setPlace("to", place));
});

$("from-form").addEventListener("submit", (e) => {
    e.preventDefault();
    search($("from-input").value.trim(), $("from-results"), (place) => setPlace("from", place));
});

$("from-change-btn").addEventListener("click", () => {
    const editor = $("from-editor");
    editor.hidden = !editor.hidden;
    if (!editor.hidden) $("from-input").focus();
});

$("from-gps-btn").addEventListener("click", () => {
    setPlace("from", null);
    startWatchingPosition();
});

$("from-map-btn").addEventListener("click", () => {
    state.mapPick = "from";
    setPlanMessage("Toque no mapa no ponto de partida.");
});

async function pickFromMap(which, point) {
    setPlace(which, { ...point, label: "Ponto escolhido no mapa" });
    if (which === "from") state.mapPick = "to";
    const label = await reverseGeocode(point);
    if (label && state[which] && state[which].lat === point.lat) setPlace(which, { ...point, label });
}

function setPlace(which, place) {
    state[which] = place;
    const isFrom = which === "from";
    if (isFrom) {
        $("from-label").textContent = place ? place.label : "a sua localização";
        $("from-results").hidden = true;
        if (fromMarker) map.removeLayer(fromMarker);
        fromMarker = place ? L.marker([place.lat, place.lon], { icon: pinIcon("A", "pin-from"), title: "Partida" }).addTo(map) : null;
        $("from-editor").hidden = true;
    } else {
        $("to-results").hidden = true;
        $("to-chosen").hidden = !place;
        $("to-chosen").textContent = place ? `Destino: ${place.label}` : "";
        if (toMarker) map.removeLayer(toMarker);
        toMarker = place ? L.marker([place.lat, place.lon], { icon: pinIcon("●", "pin-to"), title: "Destino" }).addTo(map) : null;
    }
    hidePlanMessage();
}

// Nominatim, limited to the Porto area, only when the person asks (its usage policy allows light use).
const PORTO_VIEWBOX = "-8.70,41.19,-8.54,41.13"; // left,top,right,bottom

async function search(query, list, onPick) {
    list.replaceChildren();
    list.hidden = true;
    if (!query) return;
    const url = "https://nominatim.openstreetmap.org/search?" + new URLSearchParams({
        q: query, format: "jsonv2", limit: "5", countrycodes: "pt",
        viewbox: PORTO_VIEWBOX, bounded: "1", "accept-language": "pt-PT",
    });
    try {
        const results = await (await fetch(url)).json();
        if (results.length === 0) list.append(resultItem("Não encontrámos esse sítio no Porto. Tente outro nome.", null));
        for (const r of results) {
            const [name, ...rest] = r.display_name.split(", ");
            list.append(resultItem(name, rest.slice(0, 2).join(", "), () => {
                const place = { lat: Number(r.lat), lon: Number(r.lon), label: name };
                onPick(place);
                map.setView([place.lat, place.lon], 17);
            }));
        }
    } catch {
        list.append(resultItem("A pesquisa falhou. Tente de novo ou toque no mapa.", null));
    }
    list.hidden = false;
}

function resultItem(title, detail, onPick) {
    const li = document.createElement("li");
    if (!onPick) {
        li.textContent = title;
        return li;
    }
    const b = document.createElement("button");
    b.type = "button";
    const strong = document.createElement("strong");
    strong.textContent = title;
    b.append(strong);
    if (detail) {
        const small = document.createElement("span");
        small.textContent = detail;
        b.append(small);
    }
    b.addEventListener("click", onPick);
    li.append(b);
    return li;
}

async function reverseGeocode(p) {
    const url = "https://nominatim.openstreetmap.org/reverse?" + new URLSearchParams({
        lat: p.lat, lon: p.lon, format: "jsonv2", zoom: "18", "accept-language": "pt-PT",
    });
    try {
        const r = await (await fetch(url)).json();
        const a = r.address || {};
        if (r.name) return r.name;
        if (a.road) return a.house_number ? `${a.road}, ${a.house_number}` : a.road;
    } catch { /* keep the generic label */ }
    return null;
}

function setPlanMessage(text, action) {
    const el = $("plan-message");
    el.replaceChildren(document.createTextNode(text));
    if (action) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = action.label;
        b.addEventListener("click", action.onClick);
        el.append(" ", b);
    }
    el.hidden = false;
}

function hidePlanMessage() {
    $("plan-message").hidden = true;
}

// ---------------------------------------------------------------------------------------------------------------
// The person's position (GPS, or a simulated walk with ?demo)

let watchId = null;
const positionWaiters = [];

function startWatchingPosition() {
    if (DEMO) {
        if (!state.position) onPosition({ lat: config.center[0], lon: config.center[1], accuracy: 5 });
        return;
    }
    if (watchId !== null || !navigator.geolocation) return;
    watchId = navigator.geolocation.watchPosition(
        (pos) => onPosition({ lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy }),
        () => {
            watchId = null;
            while (positionWaiters.length) positionWaiters.shift()(null);
        },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
    );
}

// Resolves with the current position, or null if it is not available within a few seconds.
function currentPosition() {
    if (state.position) return Promise.resolve(state.position);
    startWatchingPosition();
    return new Promise((resolve) => {
        positionWaiters.push(resolve);
        setTimeout(() => {
            const i = positionWaiters.indexOf(resolve);
            if (i >= 0) positionWaiters.splice(i, 1);
            resolve(state.position);
        }, 10000);
    });
}

function onPosition(p) {
    state.position = p;
    while (positionWaiters.length) positionWaiters.shift()(p);
    const ll = [p.lat, p.lon];
    if (!personMarker) {
        accuracyCircle = L.circle(ll, { radius: p.accuracy || 10, className: "accuracy", interactive: false }).addTo(map);
        personMarker = L.marker(ll, {
            icon: L.divIcon({ className: "person", html: PERSON_SVG, iconSize: [36, 36], iconAnchor: [18, 18] }),
            title: "Está aqui",
            zIndexOffset: 1000,
            keyboard: false,
        }).addTo(map);
    } else {
        personMarker.setLatLng(ll);
        accuracyCircle.setLatLng(ll).setRadius(p.accuracy || 10);
    }
    if (state.guiding) updateGuidance();
}

// If the browser already allowed location, show the person straight away; otherwise wait until it is needed.
if (DEMO) {
    startWatchingPosition();
} else if (navigator.permissions) {
    navigator.permissions.query({ name: "geolocation" })
        .then((s) => { if (s.state === "granted") startWatchingPosition(); })
        .catch(() => {});
}

// ---------------------------------------------------------------------------------------------------------------
// Routing. Everything that talks to the routing backend is in routeService, so the backend can change
// without touching the screens.

const routeService = {
    // Returns {ok: true, route} or {ok: false, reason: "no_route" | "far_from_path" | "unavailable"}.
    async route(from, to, needs) {
        if (!config.valhallaUrl) {
            console.warn("valhallaUrl is not set in config.js");
            return { ok: false, reason: "unavailable" };
        }
        let res, data;
        try {
            res = await fetch(`${config.valhallaUrl}/route`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    locations: [{ lat: from.lat, lon: from.lon }, { lat: to.lat, lon: to.lon }],
                    ...valhallaCosting(needs),
                    exclude_polygons: excludedAreas(needs),
                    units: "kilometers",
                    language: "pt-PT",
                }),
            });
            data = await res.json();
        } catch {
            return { ok: false, reason: "unavailable" };
        }
        if (!res.ok || !data.trip) {
            const code = data && data.error_code;
            if (code === 442 || code === 443) return { ok: false, reason: "no_route" };
            if (code === 170 || code === 171) return { ok: false, reason: "far_from_path" };
            console.warn("Valhalla error", data);
            return { ok: false, reason: "unavailable" };
        }
        const leg = data.trip.legs[0];
        return {
            ok: true,
            route: {
                encoded: leg.shape,
                shape: decodePolyline6(leg.shape),
                distanceKm: data.trip.summary.length,
                timeS: data.trip.summary.time,
                maneuvers: leg.maneuvers.map((m) => ({
                    instruction: fixPortuguese(m.instruction),
                    streets: m.street_names || [],
                    lengthKm: m.length,
                    begin: m.begin_shape_index,
                    end: m.end_shape_index,
                    arrive: m.type === 4 || m.type === 5 || m.type === 6,
                })),
            },
        };
    },

    // Slope and surface per edge, for the details and the warnings. Returns null when not available.
    async slopes(route, needs) {
        try {
            const res = await fetch(`${config.valhallaUrl}/trace_attributes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    encoded_polyline: route.encoded,
                    shape_match: "edge_walk",
                    ...valhallaCosting(needs),
                    filters: {
                        attributes: ["edge.length", "edge.use", "edge.max_upward_grade", "edge.max_downward_grade",
                            "edge.begin_shape_index", "edge.end_shape_index"],
                        action: "include",
                    },
                }),
            });
            const data = await res.json();
            return res.ok && data.edges ? data.edges : null;
        } catch {
            return null;
        }
    },
};

function valhallaCosting(needs) {
    const pedestrian = {
        type: needs.avoidRoughSurface ? "wheelchair" : "foot", // wheelchair = only hard surfaces
        max_grade: needs.maxGrade,
    };
    if (needs.avoidSteps) pedestrian.step_penalty = MAX_STEP_PENALTY;
    return { costing: "pedestrian", costing_options: { pedestrian } };
}

function excludedAreas(needs) {
    if (!needs.avoidBarriers) return [];
    return activeBarriers().map((b) => squareAround(b.lat, b.lon, BARRIER_RADIUS_M));
}

// A closed ring of [lon, lat] pairs, as Valhalla's exclude_polygons expects.
function squareAround(lat, lon, meters) {
    const dLat = meters / 111320;
    const dLon = meters / (111320 * Math.cos((lat * Math.PI) / 180));
    return [[lon - dLon, lat - dLat], [lon + dLon, lat - dLat], [lon + dLon, lat + dLat],
        [lon - dLon, lat + dLat], [lon - dLon, lat - dLat]];
}

// ---------------------------------------------------------------------------------------------------------------
// Plan → route screen

$("route-btn").addEventListener("click", planRoute);
$("back-btn").addEventListener("click", () => {
    clearRoute();
    showScreen("plan");
});

let routeRequestId = 0;

async function planRoute() {
    if (!state.to) {
        setPlanMessage("Primeiro diga para onde quer ir: escreva o nome do sítio ou toque no mapa.");
        $("to-input").focus();
        return;
    }
    $("route-btn").disabled = true;
    setPlanMessage(state.from ? "A procurar o melhor caminho…" : "A procurar onde está e o melhor caminho…");
    const from = state.from || await currentPosition();
    if (!from) {
        $("route-btn").disabled = false;
        setPlanMessage("Não conseguimos saber onde está. Escolha o ponto de partida.");
        $("from-editor").hidden = false;
        return;
    }
    const myRequest = ++routeRequestId;
    const result = await routeService.route(from, state.to, state.needs);
    $("route-btn").disabled = false;
    if (myRequest !== routeRequestId) return;
    if (!result.ok) {
        showRouteProblem(result.reason, (text, action) => setPlanMessage(text, action));
        return;
    }
    hidePlanMessage();
    showRoute(result.route);
    showScreen("route");
    map.fitBounds(L.latLngBounds(result.route.shape), { padding: [40, 40] });
    $("start-btn").focus();
}

// Never relax the person's limits on our own: explain and let them decide.
function showRouteProblem(reason, show) {
    const needs = state.needs;
    if (reason === "no_route") {
        const higher = needs.maxGrade + 2;
        const text = `Não encontrámos um caminho com ${describeNeeds(needs)}.`;
        if (higher <= GRADE_LIMIT) {
            show(text + " Se conseguir, pode aceitar subidas um pouco maiores.", {
                label: `Tentar com subidas até ${higher}%`,
                onClick: () => {
                    applyNeeds({ ...needs, maxGrade: higher, profile: "custom" });
                    planRoute();
                },
            });
        } else {
            show(text + " Experimente outro destino ou mude as opções avançadas.");
        }
    } else if (reason === "far_from_path") {
        show("O ponto de partida ou o destino estão longe de um passeio acessível. Escolha um ponto mais perto da rua.");
    } else {
        show("Não foi possível calcular o caminho agora. Tente de novo dentro de momentos.");
    }
}

function showRoute(route) {
    state.route = route;
    route.cumulative = cumulativeDistances(route.shape);
    drawRoute(route);
    $("route-title").textContent = state.to ? `Até ${state.to.label}` : "O seu caminho";
    $("sum-time").textContent = formatDuration(route.timeS);
    $("sum-distance").textContent = formatDistance(route.distanceKm);
    const verdict = $("sum-verdict");
    verdict.textContent = `Caminho com ${describeNeeds(state.needs)}.`;
    verdict.className = "verdict verdict-ok";
    $("slope-details").hidden = true;
    route.streets = streetList(route.maneuvers);
    renderStreets($("streets"), route.streets, -1);
    renderStreets($("guide-streets"), route.streets, 0);
    loadSlopes(route);
}

function drawRoute(route) {
    routeLayer.clearLayers();
    L.polyline(route.shape, { className: "route-casing", weight: 11, interactive: false }).addTo(routeLayer);
    L.polyline(route.shape, { className: "route-line", weight: 7, interactive: false }).addTo(routeLayer);
    passedLine = L.polyline([], { className: "route-passed", weight: 7, interactive: false }).addTo(routeLayer);
}

function clearRoute() {
    routeLayer.clearLayers();
    passedLine = null;
    state.route = null;
}

// Groups the maneuvers into the streets the person walks along, in order.
function streetList(maneuvers) {
    const streets = [];
    maneuvers.forEach((m, i) => {
        if (m.arrive) return;
        const name = m.streets[0] || "Caminho pedonal";
        const last = streets[streets.length - 1];
        if (last && last.name === name) {
            last.lengthKm += m.lengthKm;
            last.lastManeuver = i;
        } else {
            streets.push({ name, lengthKm: m.lengthKm, firstManeuver: i, lastManeuver: i });
        }
    });
    return streets;
}

function renderStreets(list, streets, currentIndex) {
    list.replaceChildren();
    streets.forEach((s, i) => {
        const li = document.createElement("li");
        if (i < currentIndex) li.className = "done";
        if (i === currentIndex) {
            li.className = "current";
            li.setAttribute("aria-current", "step");
        }
        const name = document.createElement("span");
        name.textContent = s.name;
        const len = document.createElement("span");
        len.className = "len";
        len.textContent = formatDistance(s.lengthKm);
        li.append(name, len);
        list.append(li);
    });
}

async function loadSlopes(route) {
    const edges = await routeService.slopes(route, state.needs);
    if (!edges || state.route !== route) return;
    const needs = state.needs;
    let steepestUp = 0, steepestDown = 0, overLimit = 0, hasSteps = false;
    for (const e of edges) {
        if (e.use === "steps") hasSteps = true;
        if (Math.abs(e.max_upward_grade) >= NO_ELEVATION || Math.abs(e.max_downward_grade) >= NO_ELEVATION) continue;
        const up = degreesToPercent(e.max_upward_grade);
        const down = degreesToPercent(Math.abs(e.max_downward_grade));
        steepestUp = Math.max(steepestUp, up);
        steepestDown = Math.max(steepestDown, down);
        const over = Math.round(Math.max(up, down)) > needs.maxGrade;
        if (over) overLimit += 1;
        if ((over || (e.use === "steps" && needs.avoidSteps)) && e.end_shape_index > e.begin_shape_index) {
            const part = route.shape.slice(e.begin_shape_index, e.end_shape_index + 1);
            L.polyline(part, { className: "route-warning", weight: 7, interactive: false }).addTo(routeLayer);
        }
    }
    const problems = [];
    if (overLimit > 0) problems.push(overLimit === 1 ? "uma parte mais inclinada do que pediu" : `${overLimit} partes mais inclinadas do que pediu`);
    if (hasSteps && needs.avoidSteps) problems.push("escadas que não foi possível evitar");
    if (problems.length) {
        $("sum-verdict").textContent = `Atenção: este caminho tem ${problems.join(" e ")} (a laranja no mapa).`;
        $("sum-verdict").className = "verdict verdict-warn";
    }
    $("sum-slopes").textContent = `Subida mais inclinada: ${Math.round(steepestUp)}%. Descida mais inclinada: ${Math.round(steepestDown)}%.`;
    $("slope-details").hidden = false;
}

// ---------------------------------------------------------------------------------------------------------------
// Guided mode

$("start-btn").addEventListener("click", startGuidance);
$("stop-btn").addEventListener("click", stopGuidance);

async function startGuidance() {
    state.guiding = true;
    state.following = true;
    state.arrived = false;
    state.offRouteCount = 0;
    showScreen("guide");
    $("guide-message").hidden = true;
    if (DEMO) {
        startDemoWalk();
    } else {
        startWatchingPosition();
        if (!await currentPosition() && state.guiding) {
            setBanner("Não conseguimos saber onde está.", "Siga a linha azul no mapa e a lista de ruas.");
            return;
        }
    }
    updateGuidance();
}

function stopGuidance() {
    state.guiding = false;
    stopDemoWalk();
    showScreen("route");
    if (state.route) map.fitBounds(L.latLngBounds(state.route.shape), { padding: [40, 40] });
}

function updateGuidance() {
    const route = state.route;
    const p = state.position;
    if (!route || !p || state.arrived) return;

    if (state.following) map.setView([p.lat, p.lon], Math.max(map.getZoom(), 17), { animate: true });

    const near = nearestOnRoute(route, p);
    const toEnd = route.cumulative[route.cumulative.length - 1] - near.along;
    const toDestination = state.to ? metersBetween(p, state.to) : toEnd;

    if (toEnd < ARRIVED_M || toDestination < ARRIVED_M) {
        state.arrived = true;
        stopDemoWalk();
        setBanner("Chegou ao destino!", state.to ? state.to.label : "");
        $("guide-remaining").textContent = "0 m";
        renderStreets($("guide-streets"), route.streets, route.streets.length);
        return;
    }

    // Off the route: recalculate from here, but not on every jittery GPS fix.
    if (near.distance > Math.max(OFF_ROUTE_M, p.accuracy || 0)) {
        state.offRouteCount += 1;
        if (state.offRouteCount >= 2) rerouteFromHere("Saiu do caminho. A procurar um novo caminho…");
        return;
    }
    state.offRouteCount = 0;

    passedLine.setLatLngs(route.shape.slice(0, near.index + 1).concat([[near.lat, near.lon]]));

    const i = route.maneuvers.findIndex((m) => near.index >= m.begin && near.index < Math.max(m.end, m.begin + 1));
    const current = i >= 0 ? i : 0;
    const next = route.maneuvers[current + 1];
    const toTurn = route.cumulative[route.maneuvers[current].end] - near.along;
    if (next) {
        const nextText = next.arrive ? "chega ao destino." : lowerFirst(next.instruction);
        setBanner(`Daqui a ${formatMeters(toTurn)}: ${nextText}`, streetNow(route, current));
    } else {
        setBanner(route.maneuvers[current].instruction, "");
    }
    $("guide-remaining").textContent = `${formatMeters(toEnd)} · cerca de ${formatDuration(route.timeS * (toEnd / Math.max(1, route.cumulative[route.cumulative.length - 1])))}`;
    const streetIndex = route.streets.findIndex((s) => current >= s.firstManeuver && current <= s.lastManeuver);
    renderStreets($("guide-streets"), route.streets, streetIndex);
}

function streetNow(route, maneuverIndex) {
    const s = route.streets.find((x) => maneuverIndex >= x.firstManeuver && maneuverIndex <= x.lastManeuver);
    return s ? `Está em: ${s.name}` : "";
}

async function rerouteFromHere(message) {
    if (Date.now() - state.lastRerouteAt < REROUTE_EVERY_MS || !state.position || !state.to) return;
    state.lastRerouteAt = Date.now();
    setBanner(message, "");
    const result = await routeService.route(state.position, state.to, state.needs);
    if (!state.guiding) return;
    if (!result.ok) {
        showRouteProblem(result.reason, (text) => showGuideMessage(text));
        return;
    }
    state.offRouteCount = 0;
    showRoute(result.route);
    if (DEMO) restartDemoWalk();
    updateGuidance();
}

function setBanner(next, then) {
    $("guide-next").textContent = next;
    $("guide-then").textContent = then;
}

function showGuideMessage(text) {
    $("guide-message").textContent = text;
    $("guide-message").hidden = false;
}

// ?demo: walks along the route at a brisk pace so the guidance can be shown without leaving the room.
let demoTimer = null;
let demoAlong = 0;
const DEMO_STEP_M = 8;

function startDemoWalk() {
    stopDemoWalk();
    demoAlong = 0;
    demoTimer = setInterval(demoTick, 1000);
    demoTick();
}

function restartDemoWalk() {
    startDemoWalk();
}

function stopDemoWalk() {
    if (demoTimer) clearInterval(demoTimer);
    demoTimer = null;
}

function demoTick() {
    const route = state.route;
    if (!route) return;
    const p = pointAlong(route, demoAlong);
    demoAlong += DEMO_STEP_M;
    onPosition({ lat: p[0], lon: p[1], accuracy: 5 });
}

// ---------------------------------------------------------------------------------------------------------------
// Geometry (small distances in a city: an equirectangular projection is accurate enough)

function metersBetween(a, b) {
    const k = Math.cos(((a.lat + b.lat) / 2) * Math.PI / 180);
    const dx = (b.lon - a.lon) * 111320 * k;
    const dy = (b.lat - a.lat) * 111320;
    return Math.hypot(dx, dy);
}

function cumulativeDistances(shape) {
    const out = [0];
    for (let i = 1; i < shape.length; i++) {
        const a = { lat: shape[i - 1][0], lon: shape[i - 1][1] };
        const b = { lat: shape[i][0], lon: shape[i][1] };
        out.push(out[i - 1] + metersBetween(a, b));
    }
    return out;
}

// The closest point of the route to p: segment index, distance from p, and how far along the route it is.
function nearestOnRoute(route, p) {
    const k = Math.cos(p.lat * Math.PI / 180) * 111320;
    let best = { distance: Infinity, index: 0, along: 0, lat: route.shape[0][0], lon: route.shape[0][1] };
    for (let i = 0; i < route.shape.length - 1; i++) {
        const [aLat, aLon] = route.shape[i];
        const [bLat, bLon] = route.shape[i + 1];
        const ax = (aLon - p.lon) * k, ay = (aLat - p.lat) * 111320;
        const bx = (bLon - p.lon) * k, by = (bLat - p.lat) * 111320;
        const dx = bx - ax, dy = by - ay;
        const len2 = dx * dx + dy * dy;
        const t = len2 > 0 ? Math.min(1, Math.max(0, -(ax * dx + ay * dy) / len2)) : 0;
        const d = Math.hypot(ax + t * dx, ay + t * dy);
        if (d < best.distance) {
            const segLen = route.cumulative[i + 1] - route.cumulative[i];
            best = {
                distance: d, index: i, along: route.cumulative[i] + t * segLen,
                lat: aLat + t * (bLat - aLat), lon: aLon + t * (bLon - aLon),
            };
        }
    }
    return best;
}

function pointAlong(route, meters) {
    const c = route.cumulative;
    if (meters >= c[c.length - 1]) return route.shape[route.shape.length - 1];
    let i = 0;
    while (c[i + 1] < meters) i++;
    const t = (meters - c[i]) / Math.max(1e-9, c[i + 1] - c[i]);
    const [aLat, aLon] = route.shape[i];
    const [bLat, bLon] = route.shape[i + 1];
    return [aLat + t * (bLat - aLat), aLon + t * (bLon - aLon)];
}

// Valhalla encodes shapes as Google polylines with 6 decimal places.
function decodePolyline6(str) {
    const points = [];
    let index = 0, lat = 0, lon = 0;
    while (index < str.length) {
        for (const axis of [0, 1]) {
            let result = 0, shift = 0, byte;
            do {
                byte = str.charCodeAt(index++) - 63;
                result |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);
            const delta = result & 1 ? ~(result >> 1) : result >> 1;
            if (axis === 0) lat += delta;
            else lon += delta;
        }
        points.push([lat / 1e6, lon / 1e6]);
    }
    return points;
}

function degreesToPercent(deg) {
    return Math.tan((deg * Math.PI) / 180) * 100; // Valhalla stores edge slopes in degrees
}

function formatDistance(km) {
    return formatMeters(km * 1000);
}

function formatMeters(m) {
    if (m < 1000) return `${Math.max(5, Math.round(m / 5) * 5)} m`;
    return `${(m / 1000).toFixed(1).replace(".", ",")} km`;
}

function formatDuration(seconds) {
    const min = Math.max(1, Math.round(seconds / 60));
    return min < 60 ? `${min} min` : `${Math.floor(min / 60)} h ${min % 60} min`;
}

// Valhalla's pt-PT templates contract "a" + article badly ("à o passeio"); fix the common cases.
function fixPortuguese(s) {
    const contracted = { o: "ao", os: "aos", a: "à", as: "às" };
    return (s || "").replace(/à (os|as|o|a)(?=[\s.,;]|$)/g, (_, article) => contracted[article]);
}

function lowerFirst(s) {
    return s ? s[0].toLowerCase() + s.slice(1) : s;
}

// ---------------------------------------------------------------------------------------------------------------
// Barriers (MQTT). Each report is one retained message on <prefix>/barriers/<id>; an empty retained message
// removes it. Reports past their expires_at are ignored.

let mqttClient = null;
const barrierTopic = (id) => `${config.topicPrefix}/barriers/${id}`;

function connectBroker() {
    if (!config.brokerUrl) {
        console.warn("brokerUrl is not set in config.js");
        setBrokerStatus("off", "Os reportes não estão disponíveis de momento.");
        return;
    }
    mqttClient = mqtt.connect(config.brokerUrl, {
        username: config.brokerUsername || undefined,
        password: config.brokerPassword || undefined,
        clientId: `access-web-${Math.random().toString(16).slice(2, 10)}`,
        reconnectPeriod: 5000,
    });
    mqttClient.on("connect", () => {
        setBrokerStatus("on", "Obstáculos atualizados em tempo real.");
        mqttClient.subscribe(barrierTopic("+"));
    });
    mqttClient.on("reconnect", () => setBrokerStatus("wait", "A ligar…"));
    mqttClient.on("offline", () => setBrokerStatus("off", "Sem ligação. A tentar de novo…"));
    mqttClient.on("error", (err) => {
        console.warn("MQTT error", err);
        setBrokerStatus("off", "Os reportes não estão disponíveis de momento.");
    });
    mqttClient.on("message", onBarrierMessage);
}

function onBarrierMessage(topic, payload) {
    const id = topic.split("/").pop();
    const text = payload.toString();
    let added = null;
    if (!text) {
        state.barriers.delete(id);
    } else {
        try {
            const b = JSON.parse(text);
            if (typeof b.lat !== "number" || typeof b.lon !== "number") return;
            added = { ...b, id };
            state.barriers.set(id, added);
        } catch {
            return; // not one of ours
        }
    }
    renderBarriers();
    // A new barrier on the way ahead: find another route while walking.
    if (added && state.guiding && state.needs.avoidBarriers && barrierAhead(added)) {
        state.lastRerouteAt = 0;
        rerouteFromHere("Há um obstáculo novo no seu caminho. A procurar outro caminho…");
    }
}

function barrierAhead(b) {
    const route = state.route;
    if (!route || !state.position) return false;
    const here = nearestOnRoute(route, state.position).along;
    const there = nearestOnRoute(route, b);
    return there.distance < BARRIER_RADIUS_M * 2 && there.along > here;
}

function activeBarriers() {
    const now = Date.now();
    return [...state.barriers.values()].filter((b) => !b.expires_at || Date.parse(b.expires_at) > now);
}

function renderBarriers() {
    barrierLayer.clearLayers();
    const active = activeBarriers();
    for (const b of active) {
        const marker = L.marker([b.lat, b.lon], {
            icon: L.divIcon({ className: "barrier", html: "!", iconSize: [28, 28], iconAnchor: [14, 14] }),
            title: BARRIER_KINDS[b.kind] || BARRIER_KINDS.other,
        });
        marker.bindPopup(() => barrierPopup(b));
        barrierLayer.addLayer(marker);
    }
    $("barrier-count").textContent = active.length === 0 ? ""
        : active.length === 1 ? "· 1 obstáculo no mapa" : `· ${active.length} obstáculos no mapa`;
}

function barrierPopup(b) {
    const div = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = BARRIER_KINDS[b.kind] || BARRIER_KINDS.other;
    div.append(title);
    if (b.description) {
        const p = document.createElement("p");
        p.textContent = b.description;
        div.append(p);
    }
    const when = document.createElement("p");
    when.textContent = `Reportado ${new Date(b.reported_at).toLocaleString("pt-PT")}`;
    div.append(when);
    const gone = document.createElement("button");
    gone.type = "button";
    gone.textContent = "Já não está lá";
    gone.addEventListener("click", () => {
        publish(barrierTopic(b.id), "");
        map.closePopup();
    });
    div.append(gone);
    return div;
}

function setBrokerStatus(kind, text) {
    $("broker-dot").className = `dot dot-${kind}`;
    $("broker-status").textContent = text;
    $("report-here-btn").disabled = kind !== "on";
    $("report-map-btn").disabled = kind !== "on";
}

function publish(topic, message) {
    if (!mqttClient || !mqttClient.connected) return false;
    mqttClient.publish(topic, message, { qos: 1, retain: true });
    return true;
}

$("report-here-btn").addEventListener("click", async () => {
    const p = await currentPosition();
    if (p) openReportDialog({ lat: p.lat, lon: p.lon });
    else setReportPicking(true);
});
$("report-map-btn").addEventListener("click", () => setReportPicking(true));
$("report-cancel").addEventListener("click", () => setReportPicking(false));

let mapPickBeforeReport = null;

function setReportPicking(on) {
    if (on && state.mapPick !== "report") mapPickBeforeReport = state.mapPick;
    state.mapPick = on ? "report" : mapPickBeforeReport;
    $("report-hint").hidden = !on;
    $("map").classList.toggle("picking", on);
}

function openReportDialog(point) {
    state.pendingReport = point;
    $("report-form").reset();
    $("report-dialog").showModal();
}

$("report-dialog").addEventListener("close", () => {
    const point = state.pendingReport;
    state.pendingReport = null;
    if (state.mapPick === "report") setReportPicking(false);
    if ($("report-dialog").returnValue !== "send" || !point) return;
    const hours = Number($("duration-select").value);
    const now = new Date();
    const id = `b${now.getTime().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    const barrier = {
        id,
        kind: document.querySelector('input[name="kind"]:checked').value,
        description: $("description-input").value.trim(),
        lat: Number(point.lat.toFixed(6)),
        lon: Number(point.lon.toFixed(6)),
        reported_at: now.toISOString(),
        expires_at: new Date(now.getTime() + hours * 3600 * 1000).toISOString(),
    };
    if (!publish(barrierTopic(id), JSON.stringify(barrier))) {
        alert("Não foi possível enviar o reporte. Tente de novo dentro de momentos.");
    }
});

// Expired barriers disappear without waiting for a new message.
setInterval(renderBarriers, 60 * 1000);

// ---------------------------------------------------------------------------------------------------------------
// Start

const saved = loadNeeds();
if (saved) {
    applyNeeds(saved);
    showScreen("plan");
} else {
    applyNeeds({ profile: "wheelchair", ...PROFILES.wheelchair, avoidBarriers: true });
    showScreen("welcome");
}
renderBarriers();
connectBroker();
