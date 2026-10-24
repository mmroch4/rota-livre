// Rota Livre: the person says where they want to go, sees the route (blue line + the streets it passes) and is
// guided along it with their live position. Routes come from Valhalla; barrier reports are shared through the
// Coreflux broker (MQTT over WebSocket).
"use strict";

const config = window.APP_CONFIG;
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const DEMO = params.has("demo"); // ?demo: fake position that walks along the route (for the pitch)

// ---------------------------------------------------------------------------------------------------------------
// Needs. Valhalla's pedestrian costing has two types: "wheelchair" (only hard surfaces) and "foot". Kerb height
// is not something Valhalla can filter on, so there is no option for it.

const GRADE_LIMIT = 15; // the slider's top value, meaning "no slope limit"

const PROFILES = {
    wheelchair: { label: "Cadeira de rodas", icon: "accessibility", maxGrade: 6, avoidSteps: true, avoidRoughSurface: true },
    walker: { label: "Andarilho ou canadianas", icon: "person-standing", maxGrade: 8, avoidSteps: true, avoidRoughSurface: true },
    stroller: { label: "Carrinho de bebé", icon: "baby", maxGrade: 10, avoidSteps: true, avoidRoughSurface: false },
    foot: { label: "A pé, com dificuldade em subidas", short: "Subidas difíceis", icon: "mountain", maxGrade: 8, avoidSteps: true, avoidRoughSurface: false },
    none: { label: "Sem dificuldades de mobilidade", short: "Sem limitações", icon: "user", maxGrade: GRADE_LIMIT, avoidSteps: false, avoidRoughSurface: false },
};
const CUSTOM = { label: "Personalizado", icon: "sliders-horizontal" };
const STORAGE_KEY = "access.needs";

const MAX_STEP_PENALTY = 43200; // seconds: Valhalla's upper bound (12 h), so steps are used only as a last resort
const BARRIER_RADIUS_M = 15;    // half the side of the square excluded around each barrier
const NO_ELEVATION = 32768;     // Valhalla's marker for "no elevation data" on an edge
const OFF_ROUTE_M = 35;         // further than this from the line counts as off the route
const ARRIVED_M = 20;
const REROUTE_EVERY_MS = 15000;

const BARRIER_KINDS = {
    works: { label: "Obras ou andaime", icon: "construction" },
    blocked_sidewalk: { label: "Passeio bloqueado", icon: "ban" },
    parked_car: { label: "Carro no passeio", icon: "car" },
    broken_lift: { label: "Elevador ou rampa avariados", icon: "arrow-up-down" },
    damaged_pavement: { label: "Piso danificado", icon: "triangle-alert" },
    other: { label: "Outro", icon: "info" },
};

// ---------------------------------------------------------------------------------------------------------------
// State

const state = {
    needs: null,
    from: null,        // {lat, lon, label}; null = the person's own position
    to: null,
    position: null,    // last fix {lat, lon, accuracy}
    route: null,       // see routeService.route
    screen: null,
    guiding: false,
    following: true,
    offRouteCount: 0,
    lastRerouteAt: 0,
    arrived: false,
    mapPick: null,     // what a tap on the map sets: "to" | "from" | null
    searchMode: "to",
    reportPoint: null,
    barriers: new Map(),
};

// ---------------------------------------------------------------------------------------------------------------
// Icons (Lucide). Elements with data-lucide become SVGs; call refreshIcons() after adding new ones.

function refreshIcons() {
    try { window.lucide.createIcons({ attrs: { "aria-hidden": "true" } }); } catch { /* icons are decoration */ }
}

function iconHtml(name) {
    return `<i data-lucide="${name}"></i>`;
}

function setIcon(el, name) {
    el.innerHTML = iconHtml(name);
    refreshIcons();
}

// ---------------------------------------------------------------------------------------------------------------
// Map and its layers

const map = L.map("map", { zoomControl: false }).setView(config.center, config.zoom);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
L.control.zoom({ position: "topright" }).addTo(map);

const routeLayer = L.layerGroup().addTo(map);
const barrierLayer = L.layerGroup().addTo(map);
let passedLine = null;
let personMarker = null;
let accuracyCircle = null;
let fromMarker = null;
let toMarker = null;

const PERSON_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="3"/>'
    + '<path d="M12 9c-2 0-3.5 1.2-3.5 3v4h2v6h3v-6h2v-4c0-1.8-1.5-3-3.5-3z"/></svg>';

map.on("click", (e) => {
    const point = { lat: e.latlng.lat, lon: e.latlng.lng };
    if (state.mapPick === "from" || state.mapPick === "to") {
        const which = state.mapPick;
        setPick(null);
        chooseFromMap(which, point);
    } else if (state.screen === "plan") {
        chooseFromMap("to", point); // like a map app: tap a place to go there
    }
});

map.on("dragstart", () => {
    if (!state.guiding) return;
    state.following = false;
    $("recenter-btn").hidden = false;
});

$("recenter-btn").addEventListener("click", () => {
    if (!state.position) return;
    if (state.guiding) {
        state.following = true;
        $("recenter-btn").hidden = true;
    }
    centerOn([state.position.lat, state.position.lon], Math.max(map.getZoom(), 17));
});

// The parts of the map hidden by floating panels, so routes and the person are shown in the free part.
function mapInsets() {
    const box = $("map").getBoundingClientRect();
    const insets = { top: 0, left: 0, right: 0, bottom: 0 };
    const tops = phone.matches ? ["topbar", "guide-banner", "pick-hint"] : ["guide-banner", "pick-hint"];
    for (const id of tops) {
        const el = $(id);
        if (el.hidden || getComputedStyle(el).display === "none") continue;
        insets.top = Math.max(insets.top, el.getBoundingClientRect().bottom - box.top);
    }
    if (!phone.matches) insets.left = Math.max(0, $("sheet").getBoundingClientRect().right - box.left);
    return insets;
}

function centerOn(ll, zoom) {
    const z = zoom ?? map.getZoom();
    const i = mapInsets();
    const p = map.project(ll, z).add([(i.right - i.left) / 2, (i.bottom - i.top) / 2]);
    map.setView(map.unproject(p, z), z, { animate: true });
}

function fitRoute(shape) {
    const i = mapInsets();
    map.fitBounds(L.latLngBounds(shape), {
        paddingTopLeft: [i.left + 40, i.top + 40],
        paddingBottomRight: [i.right + 40, i.bottom + 40],
    });
}

function pinIcon(cls) {
    return L.divIcon({ className: `pin ${cls}`, html: "<span></span>", iconSize: [34, 42], iconAnchor: [17, 40] });
}

// ---------------------------------------------------------------------------------------------------------------
// Screens

function showScreen(name) {
    state.screen = name;
    for (const s of ["plan", "route", "guide"]) $(`screen-${s}`).hidden = s !== name;
    document.body.dataset.screen = name;
    $("guide-banner").hidden = name !== "guide";
    if (name !== "guide") $("recenter-btn").hidden = !state.position;
    setSheetExpanded(false);
}

function showToast(text, ms = 3500) {
    const t = $("toast");
    t.textContent = text;
    t.hidden = false;
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => { t.hidden = true; }, ms);
}

function showNotice(el, text, action) {
    el.replaceChildren();
    const p = document.createElement("p");
    p.textContent = text;
    el.append(p);
    if (action) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "secondary";
        b.textContent = action.label;
        b.addEventListener("click", action.onClick);
        el.append(b);
    }
    el.hidden = false;
}

function setPick(which, text) {
    state.mapPick = which;
    $("pick-hint").hidden = !which;
    $("pick-hint-text").textContent = text || "";
    $("map").classList.toggle("picking", !!which);
}

$("pick-cancel").addEventListener("click", () => setPick(null));

// ---------------------------------------------------------------------------------------------------------------
// Phones: the panel is a bottom sheet over a full-screen map. Closed, it shows the top of the current screen
// (down to the last [data-peek] element: the main button); open, it shows everything. The visible map ends
// where the closed sheet starts, so the route and the person are never hidden under it.

const phone = window.matchMedia("(max-width: 760px) and (orientation: portrait)");
let sheetExpanded = false;
const SHEET_GAP = 18;

function setSheetExpanded(open) {
    sheetExpanded = open;
    if (!open) $("sheet").scrollTop = 0;
    updateSheet();
}

function updateSheet() {
    const sheet = $("sheet");
    const root = document.documentElement;
    if (!phone.matches) {
        root.style.removeProperty("--sheet-h");
        sheet.classList.remove("expanded");
        $("sheet-handle").hidden = true;
        map.invalidateSize();
        return;
    }
    const screen = document.querySelector(".screen:not([hidden])");
    const peekEls = screen ? [...screen.querySelectorAll("[data-peek]")].filter((el) => el.offsetParent) : [];
    let peek = peekEls.length
        ? Math.max(...peekEls.map((el) => el.offsetTop + el.offsetHeight)) + SHEET_GAP
        : sheet.scrollHeight;
    peek = Math.min(peek, Math.round(window.innerHeight * 0.7));
    const hasMore = sheet.scrollHeight > peek + 4;
    $("sheet-handle").hidden = !hasMore;
    $("sheet-handle").setAttribute("aria-expanded", String(sheetExpanded));
    $("sheet-handle-text").textContent = sheetExpanded ? "Ver menos" : (screen && screen.dataset.more) || "Ver mais";
    sheet.classList.toggle("expanded", sheetExpanded && hasMore);
    root.style.setProperty("--sheet-h", `${peek}px`);
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

// Content changes (messages, the street list) change how much the closed sheet shows.
const sheetObserver = new ResizeObserver(() => { if (!sheetExpanded) updateSheet(); });
for (const s of document.querySelectorAll(".screen")) sheetObserver.observe(s);
phone.addEventListener("change", () => setSheetExpanded(false));
window.addEventListener("resize", () => updateSheet());

// ---------------------------------------------------------------------------------------------------------------
// Needs: welcome (first visit only), the profile chip and the settings dialog

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

function profileInfo(name) {
    return PROFILES[name] || CUSTOM;
}

function applyNeeds(needs) {
    state.needs = needs;
    const info = profileInfo(needs.profile);
    $("profile-chip-label").textContent = info.short || info.label;
    setIcon($("profile-chip-icon"), info.icon);
    $("grade-input").value = needs.maxGrade;
    $("grade-output").value = gradeText(needs.maxGrade);
    $("steps-check").checked = needs.avoidSteps;
    $("surface-check").checked = needs.avoidRoughSurface;
    $("barriers-check").checked = needs.avoidBarriers;
    for (const b of document.querySelectorAll("#settings-choices .choice")) {
        b.setAttribute("aria-pressed", String(b.dataset.profile === needs.profile));
    }
}

function profileNeeds(name) {
    const { maxGrade, avoidSteps, avoidRoughSurface } = PROFILES[name];
    return { profile: name, maxGrade, avoidSteps, avoidRoughSurface, avoidBarriers: true };
}

function gradeText(g) {
    return g >= GRADE_LIMIT ? "sem limite" : `${g}%`;
}

function renderChoices(container, onPick) {
    container.replaceChildren();
    for (const [name, p] of Object.entries(PROFILES)) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "choice";
        b.dataset.profile = name;
        b.innerHTML = `<span class="choice-ic">${iconHtml(p.icon)}</span><span></span>`;
        b.lastChild.textContent = p.label;
        b.addEventListener("click", () => onPick(name));
        container.append(b);
    }
    refreshIcons();
}

renderChoices($("welcome-choices"), (name) => {
    applyNeeds(profileNeeds(name));
    saveNeeds();
    $("welcome").hidden = true;
    $("where-btn").focus();
});

renderChoices($("settings-choices"), (name) => {
    applyNeeds({ ...profileNeeds(name), avoidBarriers: state.needs.avoidBarriers });
    saveNeeds();
});

let needsWhenOpened = null;
$("profile-chip").addEventListener("click", () => {
    needsWhenOpened = JSON.stringify(state.needs);
    applyNeeds(state.needs);
    $("settings").showModal();
});
$("settings-close").addEventListener("click", () => $("settings").close());
$("settings-done").addEventListener("click", () => $("settings").close());
$("settings").addEventListener("close", () => {
    // New needs: show the route that fits them.
    if (JSON.stringify(state.needs) !== needsWhenOpened && state.to && state.screen === "route") planRoute();
});

$("grade-input").addEventListener("input", (e) => { $("grade-output").value = gradeText(Number(e.target.value)); });

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
    const parts = [];
    if (needs.maxGrade < GRADE_LIMIT) parts.push(`subidas até ${needs.maxGrade}%`);
    if (needs.avoidSteps) parts.push("sem escadas");
    if (needs.avoidRoughSurface) parts.push("piso regular");
    if (parts.length === 0) return "";
    return parts.slice(0, -1).join(", ") + (parts.length > 1 ? " e " : "") + parts[parts.length - 1];
}

// ---------------------------------------------------------------------------------------------------------------
// Search (full screen on phones). Nominatim, limited to the Porto area, only when the person presses search
// (its usage policy allows light use, not search-as-you-type).

const PORTO_VIEWBOX = "-8.70,41.19,-8.54,41.13"; // left,top,right,bottom

$("where-btn").addEventListener("click", () => openSearch("to"));
for (const b of document.querySelectorAll(".js-from-change")) b.addEventListener("click", () => openSearch("from"));

function openSearch(mode) {
    state.searchMode = mode;
    const label = mode === "to" ? "Para onde quer ir?" : "De onde parte?";
    $("search-input").placeholder = label;
    $("search-label").textContent = label;
    $("search-input").value = "";
    $("search-results").replaceChildren();
    $("search-status").textContent = "Escreva uma rua, praça ou local do Porto e carregue em pesquisar.";
    $("quick-gps-item").hidden = mode !== "from";
    $("search").hidden = false;
    $("search-input").focus();
}

function closeSearch() {
    $("search").hidden = true;
}

$("search-back").addEventListener("click", closeSearch);
$("search").addEventListener("keydown", (e) => { if (e.key === "Escape") closeSearch(); });

$("quick-gps").addEventListener("click", () => {
    closeSearch();
    setPlace("from", null);
    startWatchingPosition();
    if (state.to) planRoute();
});

$("quick-map").addEventListener("click", () => {
    const which = state.searchMode;
    closeSearch();
    setPick(which, which === "to" ? "Toque no mapa para onde quer ir." : "Toque no mapa no ponto de partida.");
});

$("search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = $("search-input").value.trim();
    const list = $("search-results");
    if (!query) return;
    list.replaceChildren();
    $("search-status").textContent = "A procurar…";
    const url = "https://nominatim.openstreetmap.org/search?" + new URLSearchParams({
        q: query, format: "jsonv2", limit: "6", countrycodes: "pt",
        viewbox: PORTO_VIEWBOX, bounded: "1", "accept-language": "pt-PT",
    });
    let results;
    try {
        results = await (await fetch(url)).json();
    } catch {
        $("search-status").textContent = "A pesquisa falhou. Tente de novo, ou escolha no mapa.";
        return;
    }
    $("search-status").textContent = results.length ? "" : "Não encontrámos esse sítio no Porto. Tente outro nome.";
    for (const r of results) {
        const [name, ...rest] = r.display_name.split(", ");
        const li = document.createElement("li");
        const b = document.createElement("button");
        b.type = "button";
        b.innerHTML = `<span class="list-ic">${iconHtml("map-pin")}</span><span class="list-text"><strong></strong><small></small></span>`;
        b.querySelector("strong").textContent = name;
        b.querySelector("small").textContent = rest.slice(0, 2).join(", ");
        b.addEventListener("click", () => {
            closeSearch();
            choosePlace(state.searchMode, { lat: Number(r.lat), lon: Number(r.lon), label: name });
        });
        li.append(b);
        list.append(li);
    }
    refreshIcons();
});

async function chooseFromMap(which, point) {
    choosePlace(which, { ...point, label: "Ponto no mapa" });
    const label = await reverseGeocode(point);
    const place = state[which];
    if (label && place && place.lat === point.lat) {
        place.label = label;
        updatePlaceLabels();
    }
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

// Choosing a destination (or a new start once there is one) shows the route straight away.
function choosePlace(which, place) {
    setPlace(which, place);
    if (state.to) planRoute();
}

function setPlace(which, place) {
    state[which] = place;
    if (which === "from") {
        if (fromMarker) map.removeLayer(fromMarker);
        fromMarker = place ? L.marker([place.lat, place.lon], { icon: pinIcon("pin-from"), title: "Partida" }).addTo(map) : null;
    } else {
        if (toMarker) map.removeLayer(toMarker);
        toMarker = place ? L.marker([place.lat, place.lon], { icon: pinIcon("pin-to"), title: "Destino" }).addTo(map) : null;
    }
    updatePlaceLabels();
}

function updatePlaceLabels() {
    for (const el of document.querySelectorAll(".from-label")) {
        el.textContent = state.from ? state.from.label : "a sua localização";
    }
    $("route-title").textContent = state.to ? state.to.label : "Destino";
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
            icon: L.divIcon({ className: "person", html: PERSON_SVG, iconSize: [38, 38], iconAnchor: [19, 19] }),
            title: "Está aqui",
            zIndexOffset: 1000,
            keyboard: false,
        }).addTo(map);
        if (!state.guiding) $("recenter-btn").hidden = false;
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
                    type: m.type,
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
    const pedestrian = { type: needs.avoidRoughSurface ? "wheelchair" : "foot" }; // wheelchair = only hard surfaces
    if (needs.maxGrade < GRADE_LIMIT) pedestrian.max_grade = needs.maxGrade;
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
// Plan → route

$("route-close").addEventListener("click", () => {
    clearRoute();
    setPlace("to", null);
    showScreen("plan");
});

let routeRequestId = 0;

async function planRoute() {
    if (!state.to) return;
    const myRequest = ++routeRequestId;
    showToast(state.from ? "A procurar o melhor caminho…" : "A procurar onde está e o melhor caminho…", 8000);
    const from = state.from || await currentPosition();
    if (myRequest !== routeRequestId) return;
    if (!from) {
        $("toast").hidden = true;
        showScreen("plan");
        showNotice($("plan-message"), "Não conseguimos saber onde está. Diga-nos de onde parte.", {
            label: "Escolher a partida",
            onClick: () => openSearch("from"),
        });
        return;
    }
    const result = await routeService.route(from, state.to, state.needs);
    if (myRequest !== routeRequestId) return;
    $("toast").hidden = true;
    if (!result.ok) {
        clearRoute();
        showScreen("plan");
        showRouteProblem(result.reason, (text, action) => showNotice($("plan-message"), text, action));
        return;
    }
    $("plan-message").hidden = true;
    showScreen("route");
    showRoute(result.route);
    fitRoute(result.route.shape);
}

// Never relax the person's limits on our own: explain and let them decide.
function showRouteProblem(reason, show) {
    const needs = state.needs;
    const where = state.to ? ` até ${state.to.label}` : "";
    if (reason === "no_route") {
        const higher = needs.maxGrade + 2;
        const text = `Não encontrámos um caminho${where} com ${describeNeeds(needs) || "estas opções"}.`;
        if (higher < GRADE_LIMIT) {
            show(text + " Se conseguir, pode aceitar subidas um pouco maiores.", {
                label: `Tentar com subidas até ${higher}%`,
                onClick: () => {
                    applyNeeds({ ...needs, maxGrade: higher, profile: "custom" });
                    saveNeeds();
                    planRoute();
                },
            });
        } else {
            show(text + " Experimente outro destino ou mude as opções em \"Como se desloca\".");
        }
    } else if (reason === "far_from_path") {
        show("A partida ou o destino estão longe de um passeio acessível. Escolha um ponto mais perto da rua.");
    } else {
        show("Não foi possível calcular o caminho agora. Tente de novo dentro de momentos.");
    }
}

function showRoute(route) {
    state.route = route;
    route.cumulative = cumulativeDistances(route.shape);
    drawRoute(route);
    updatePlaceLabels();
    $("sum-time").textContent = formatDuration(route.timeS);
    $("sum-meta").textContent = `${formatDistance(route.distanceKm)} · chega às ${clockIn(route.timeS)}`;
    setVerdict(true, describeNeeds(state.needs) ? `Caminho com ${describeNeeds(state.needs)}.` : "O caminho a pé mais direto.");
    $("slope-details").hidden = true;
    route.streets = streetList(route.maneuvers);
    renderStreets($("streets"), route.streets, -1);
    renderStreets($("guide-streets"), route.streets, 0);
    loadSlopes(route);
}

function setVerdict(ok, text) {
    const v = $("sum-verdict");
    v.className = `verdict ${ok ? "verdict-ok" : "verdict-warn"}`;
    v.innerHTML = iconHtml(ok ? "check" : "triangle-alert");
    v.append(document.createTextNode(" " + text));
    refreshIcons();
}

function drawRoute(route) {
    routeLayer.clearLayers();
    L.polyline(route.shape, { className: "route-casing", weight: 12, interactive: false }).addTo(routeLayer);
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
    const needs = state.needs;
    const edges = await routeService.slopes(route, needs);
    if (!edges || state.route !== route) return;
    let steepestUp = 0, steepestDown = 0, overLimit = 0, hasSteps = false;
    for (const e of edges) {
        if (e.use === "steps") hasSteps = true;
        if (Math.abs(e.max_upward_grade) >= NO_ELEVATION || Math.abs(e.max_downward_grade) >= NO_ELEVATION) continue;
        const up = degreesToPercent(e.max_upward_grade);
        const down = degreesToPercent(Math.abs(e.max_downward_grade));
        steepestUp = Math.max(steepestUp, up);
        steepestDown = Math.max(steepestDown, down);
        const over = needs.maxGrade < GRADE_LIMIT && Math.round(Math.max(up, down)) > needs.maxGrade;
        if (over) overLimit += 1;
        if ((over || (e.use === "steps" && needs.avoidSteps)) && e.end_shape_index > e.begin_shape_index) {
            const part = route.shape.slice(e.begin_shape_index, e.end_shape_index + 1);
            L.polyline(part, { className: "route-warning", weight: 7, interactive: false }).addTo(routeLayer);
        }
    }
    const problems = [];
    if (overLimit > 0) problems.push(overLimit === 1 ? "uma parte mais inclinada do que pediu" : `${overLimit} partes mais inclinadas do que pediu`);
    if (hasSteps && needs.avoidSteps) problems.push("escadas que não foi possível evitar");
    if (problems.length) setVerdict(false, `Atenção: tem ${problems.join(" e ")} (a laranja no mapa).`);
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
    $("recenter-btn").hidden = true;
    if (DEMO) {
        startDemoWalk();
    } else {
        startWatchingPosition();
        if (!await currentPosition() && state.guiding) {
            setBanner("navigation", "", "Não conseguimos saber onde está. Siga a linha azul e a lista de ruas.");
            return;
        }
    }
    updateGuidance();
}

function stopGuidance() {
    state.guiding = false;
    stopDemoWalk();
    showScreen("route");
    if (state.route) fitRoute(state.route.shape);
}

function updateGuidance() {
    const route = state.route;
    const p = state.position;
    if (!route || !p || state.arrived) return;

    if (state.following) centerOn([p.lat, p.lon], Math.max(map.getZoom(), 17));

    const near = nearestOnRoute(route, p);
    const total = route.cumulative[route.cumulative.length - 1];
    const toEnd = total - near.along;
    const toDestination = state.to ? metersBetween(p, state.to) : toEnd;

    if (toEnd < ARRIVED_M || toDestination < ARRIVED_M) {
        state.arrived = true;
        stopDemoWalk();
        setBanner("flag", "Chegou!", state.to ? state.to.label : "");
        setGuideStats(0, 0);
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
        setBanner(turnIcon(next), formatMeters(toTurn), next.arrive ? "Chega ao destino" : next.instruction);
    } else {
        setBanner("arrow-up", "", route.maneuvers[current].instruction);
    }
    setGuideStats(toEnd, route.timeS * (toEnd / Math.max(1, total)));
    const streetIndex = route.streets.findIndex((s) => current >= s.firstManeuver && current <= s.lastManeuver);
    renderStreets($("guide-streets"), route.streets, streetIndex);
}

function setGuideStats(meters, seconds) {
    $("guide-arrival").textContent = clockIn(seconds);
    $("guide-time").textContent = formatDuration(seconds);
    $("guide-dist").textContent = formatMeters(meters);
}

// Valhalla maneuver types → an arrow.
function turnIcon(m) {
    if (m.arrive) return "flag";
    if (m.type === 9) return "arrow-up-right";
    if (m.type === 10 || m.type === 11) return "corner-up-right";
    if (m.type === 16) return "arrow-up-left";
    if (m.type === 14 || m.type === 15) return "corner-up-left";
    if (m.type === 12 || m.type === 13) return "undo-2";
    return "arrow-up";
}

let bannerIconName = null;
function setBanner(icon, distance, text) {
    if (icon !== bannerIconName) {
        bannerIconName = icon;
        setIcon($("turn-icon"), icon);
    }
    $("turn-dist").textContent = distance;
    $("turn-dist").hidden = !distance;
    $("turn-text").textContent = text;
}

async function rerouteFromHere(message) {
    if (Date.now() - state.lastRerouteAt < REROUTE_EVERY_MS || !state.position || !state.to) return;
    state.lastRerouteAt = Date.now();
    setBanner("navigation", "", message);
    const result = await routeService.route(state.position, state.to, state.needs);
    if (!state.guiding) return;
    if (!result.ok) {
        showRouteProblem(result.reason, (text) => showNotice($("guide-message"), text));
        return;
    }
    state.offRouteCount = 0;
    showRoute(result.route);
    if (DEMO) startDemoWalk();
    updateGuidance();
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

function clockIn(seconds) {
    return new Date(Date.now() + seconds * 1000).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" });
}

// Valhalla's pt-PT templates contract "a" + article badly ("à o passeio"); fix the common cases.
function fixPortuguese(s) {
    const contracted = { o: "ao", os: "aos", a: "à", as: "às" };
    return (s || "").replace(/à (os|as|o|a)(?=[\s.,;]|$)/g, (_, article) => contracted[article]);
}

// ---------------------------------------------------------------------------------------------------------------
// Barriers. Two stores, chosen by config.brokerUrl:
//  - broker (Coreflux, MQTT): each report is one retained message on <prefix>/barriers/<id>; an empty retained
//    message removes it. Shared live with everyone. Photos stay on the reporting device (not in the contract).
//  - device (no broker yet): reports are kept in this browser's localStorage, so they show on the map and the
//    person's routes avoid them, but nobody else sees them.
// Reports past their expires_at are ignored.

const USE_BROKER = !!config.brokerUrl;
const LOCAL_BARRIERS_KEY = "access.barriers";
const REPORT_HOURS = 24;
const PHOTO_MAX_PX = 800;

let mqttClient = null;
let brokerOnline = false;
const barrierTopic = (id) => `${config.topicPrefix}/barriers/${id}`;

function connectBroker() {
    if (!USE_BROKER) {
        loadLocalBarriers();
        renderBarriers();
        setBrokerStatus(true, "Os seus reportes ficam guardados neste dispositivo.", "local");
        $("report-info").textContent = "Obras, um passeio bloqueado, um elevador avariado… Toque no botão laranja "
            + "para o marcar no mapa. Os seus caminhos passam a evitá-lo.";
        return;
    }
    mqttClient = mqtt.connect(config.brokerUrl, {
        username: config.brokerUsername || undefined,
        password: config.brokerPassword || undefined,
        clientId: `access-web-${Math.random().toString(16).slice(2, 10)}`,
        reconnectPeriod: 5000,
    });
    mqttClient.on("connect", () => {
        setBrokerStatus(true, "Obstáculos atualizados em tempo real.");
        mqttClient.subscribe(barrierTopic("+"));
    });
    mqttClient.on("reconnect", () => setBrokerStatus(false, "A ligar…"));
    mqttClient.on("offline", () => setBrokerStatus(false, "Sem ligação. A tentar de novo…"));
    mqttClient.on("error", (err) => {
        console.warn("MQTT error", err);
        setBrokerStatus(false, "Os reportes não estão disponíveis de momento.");
    });
    mqttClient.on("message", onBarrierMessage);
}

function onBarrierMessage(topic, payload) {
    const id = topic.split("/").pop();
    const text = payload.toString();
    if (!text) {
        state.barriers.delete(id);
        barriersChanged(null);
        return;
    }
    try {
        const b = JSON.parse(text);
        if (typeof b.lat !== "number" || typeof b.lon !== "number") return;
        const mine = state.barriers.get(id); // keep the photo of our own report
        const added = { ...b, id, photo: mine && mine.photo, address: mine && mine.address };
        state.barriers.set(id, added);
        barriersChanged(added);
    } catch {
        // not one of ours
    }
}

function loadLocalBarriers() {
    try {
        for (const b of JSON.parse(localStorage.getItem(LOCAL_BARRIERS_KEY)) || []) state.barriers.set(b.id, b);
    } catch { /* storage blocked or corrupt: start empty */ }
}

// Returns false when the browser refuses to store (full or blocked).
function saveLocalBarriers() {
    try {
        localStorage.setItem(LOCAL_BARRIERS_KEY, JSON.stringify(activeBarriers()));
        return true;
    } catch {
        return false;
    }
}

function addBarrier(barrier) {
    if (USE_BROKER) {
        const { photo, address, ...shared } = barrier; // extras outside the agreed barrier contract stay local
        if (!publish(barrierTopic(barrier.id), JSON.stringify(shared))) return "failed";
        state.barriers.set(barrier.id, barrier); // shown now; the broker echo keeps the photo
        barriersChanged(barrier);
        return "shared";
    }
    state.barriers.set(barrier.id, barrier);
    let result = "device";
    let saved = saveLocalBarriers();
    if (!saved && barrier.photo) {
        delete barrier.photo; // the photo did not fit in the browser's storage: keep the report without it
        saved = saveLocalBarriers();
        result = "device-no-photo";
    }
    if (!saved) result = "memory";
    barriersChanged(barrier);
    return result;
}

function removeBarrier(id) {
    if (USE_BROKER) return publish(barrierTopic(id), "");
    state.barriers.delete(id);
    saveLocalBarriers();
    barriersChanged(null);
    return true;
}

// Map, and routes: a new barrier ahead while walking → reroute from here; a shown route → recalculate.
function barriersChanged(added) {
    renderBarriers();
    if (!state.needs || !state.needs.avoidBarriers) return;
    if (state.guiding) {
        if (added && barrierAhead(added)) {
            state.lastRerouteAt = 0;
            rerouteFromHere("Há um obstáculo novo no seu caminho. A procurar outro caminho…");
        }
    } else if (state.screen === "route" && state.to) {
        planRoute();
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
    // Fixed width; panning clear of the floating panels is done by keepPopupVisible.
    const popupOptions = { minWidth: 240, maxWidth: 240, autoPan: false };
    for (const b of active) {
        const kind = BARRIER_KINDS[b.kind] || BARRIER_KINDS.other;
        const marker = L.marker([b.lat, b.lon], {
            icon: L.divIcon({ className: "barrier", html: iconHtml(kind.icon), iconSize: [32, 32], iconAnchor: [16, 16] }),
            title: kind.label,
        });
        marker.bindPopup(() => barrierPopup(b), popupOptions);
        barrierLayer.addLayer(marker);
    }
    refreshIcons();
    $("barrier-count").textContent = active.length === 0 ? ""
        : active.length === 1 ? "· 1 obstáculo no mapa" : `· ${active.length} obstáculos no mapa`;
}

// Leaflet's autoPan knows nothing about our floating panels: move the map until the popup is in the free part.
function keepPopupVisible(popup) {
    const el = popup.getElement();
    if (!el) return;
    const r = el.getBoundingClientRect();
    const box = $("map").getBoundingClientRect();
    const i = mapInsets();
    const margin = 12;
    let dx = 0, dy = 0;
    if (r.left < box.left + i.left + margin) dx = r.left - (box.left + i.left + margin);
    else if (r.right > box.right - i.right - 84) dx = r.right - (box.right - i.right - 84); // round buttons
    if (r.top < box.top + i.top + margin) dy = r.top - (box.top + i.top + margin);
    else if (r.bottom > box.bottom - i.bottom - margin) dy = r.bottom - (box.bottom - i.bottom - margin);
    if (dx || dy) map.panBy([dx, dy]);
}

map.on("popupopen", (e) => {
    requestAnimationFrame(() => keepPopupVisible(e.popup));
    const img = e.popup.getElement() && e.popup.getElement().querySelector("img");
    if (img && !img.complete) img.addEventListener("load", () => keepPopupVisible(e.popup), { once: true });
});

function barrierPopup(b) {
    const div = document.createElement("div");
    div.className = "popup";
    const title = document.createElement("strong");
    title.textContent = (BARRIER_KINDS[b.kind] || BARRIER_KINDS.other).label;
    div.append(title);
    if (b.address) {
        const where = document.createElement("p");
        where.className = "popup-address";
        where.textContent = b.address;
        div.append(where);
    }
    if (b.photo) {
        const img = document.createElement("img");
        img.src = b.photo;
        img.alt = "Foto do obstáculo";
        img.className = "popup-photo";
        div.append(img);
    }
    if (b.description) {
        const p = document.createElement("p");
        p.textContent = b.description;
        div.append(p);
    }
    const when = document.createElement("p");
    when.className = "popup-when";
    when.textContent = `Reportado ${new Date(b.reported_at).toLocaleString("pt-PT", { dateStyle: "short", timeStyle: "short" })}`;
    div.append(when);
    const gone = document.createElement("button");
    gone.type = "button";
    gone.className = "secondary";
    gone.textContent = "Já não está lá";
    gone.addEventListener("click", () => {
        map.closePopup();
        showToast(removeBarrier(b.id)
            ? "Obrigado! O obstáculo foi retirado do mapa."
            : "Não foi possível retirar o obstáculo. Tente de novo dentro de momentos.");
    });
    div.append(gone);
    return div;
}

function setBrokerStatus(online, text, kind) {
    brokerOnline = online;
    $("broker-dot").className = `dot ${kind === "local" ? "dot-local" : online ? "dot-on" : "dot-off"}`;
    $("broker-status").textContent = text;
}

function publish(topic, message) {
    if (!mqttClient || !mqttClient.connected) return false;
    mqttClient.publish(topic, message, { qos: 1, retain: true });
    return true;
}

// Report: orange button → pick the type (and, optionally, a photo or a few words) → send.
const report = { kind: null, photo: null };

for (const [kind, k] of Object.entries(BARRIER_KINDS)) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tile";
    b.dataset.kind = kind;
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", "false");
    b.innerHTML = `<span class="tile-ic">${iconHtml(k.icon)}</span><span></span>`;
    b.lastChild.textContent = k.label;
    b.addEventListener("click", () => selectReportKind(kind));
    $("report-tiles").append(b);
}

function selectReportKind(kind) {
    report.kind = kind;
    for (const t of document.querySelectorAll("#report-tiles .tile")) {
        t.setAttribute("aria-checked", String(t.dataset.kind === kind));
    }
    $("report-send").disabled = !kind;
    $("report-send").textContent = kind ? "Enviar" : "Escolha o tipo de obstáculo";
}

$("report-btn").addEventListener("click", () => {
    if (USE_BROKER && !brokerOnline) {
        showToast("Os reportes não estão disponíveis de momento. Tente mais tarde.");
        return;
    }
    openReportDialog();
});

$("report-close").addEventListener("click", () => $("report-dialog").close());

function mapCenterPoint() {
    const c = map.getCenter();
    return { lat: c.lat, lon: c.lng };
}

// The report map starts where the person is. If their position is not known yet, it asks for it and moves
// there when it arrives, unless they already started moving the map themselves.
function openReportDialog() {
    $("description-input").value = "";
    setReportPhoto(null);
    selectReportKind(null);
    $("report-dialog").showModal();
    $("report-dialog").scrollTop = 0;
    if (state.position) {
        showReportMap(state.position);
        return;
    }
    showReportMap(mapCenterPoint());
    setReportNote("A procurar onde está…");
    let movedByHand = false;
    const onDrag = () => { movedByHand = true; };
    reportMap.on("dragstart zoomstart", onDrag);
    currentPosition().then((p) => {
        reportMap.off("dragstart zoomstart", onDrag);
        if (!$("report-dialog").open || movedByHand) return;
        if (p) {
            setReportNote("");
            reportMap.setView([p.lat, p.lon], 18, { animate: false });
        } else {
            setReportNote("Não conseguimos saber onde está. Mova o mapa até ao obstáculo ou escreva a morada.");
        }
    });
}

// A note under the address (e.g. "couldn't find you") that stays until the person moves the map themselves.
let reportNote = "";
function setReportNote(text) {
    reportNote = text;
    $("report-address-status").textContent = text;
}

// Where is it? A small map inside the dialog with a fixed pin in the middle: the person moves the map under
// the pin (like ride-hailing apps), and the address under it fills itself in. Typing an address and searching,
// or "my location", move the map instead.
let reportMap = null;
let reportGeocodeTimer = null;
let reportGeocodeSeq = 0;
let reportKeepAddress = false; // the map moved to an address the person searched: keep their words

function showReportMap(point) {
    const ll = [point.lat, point.lon];
    if (!reportMap) {
        reportMap = L.map("report-map", { attributionControl: false, zoomControl: !phone.matches }).setView(ll, 18);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(reportMap);
        reportMap.on("moveend", onReportMapMoved);
        reportMap.on("dragstart", () => setReportNote(""));
    }
    reportMap.invalidateSize();
    reportMap.setView(ll, 18, { animate: false });
    onReportMapMoved();
}

function onReportMapMoved() {
    const c = reportMap.getCenter();
    state.reportPoint = { lat: c.lat, lon: c.lng };
    clearTimeout(reportGeocodeTimer);
    if (reportKeepAddress) {
        reportKeepAddress = false;
        return;
    }
    const seq = ++reportGeocodeSeq;
    $("report-address").value = "";
    $("report-address").placeholder = "A procurar a morada…";
    $("report-address-status").textContent = reportNote;
    // Nominatim allows about one request per second: ask only once the map has stopped.
    reportGeocodeTimer = setTimeout(async () => {
        const address = await addressAt(state.reportPoint);
        if (seq !== reportGeocodeSeq) return;
        $("report-address").placeholder = "Rua, número ou local";
        $("report-address").value = address || "";
        $("report-address-status").textContent = address ? reportNote : "Não encontrámos a morada deste sítio. Pode escrevê-la.";
    }, 700);
}

// Street and number first (that is what an address is); the name of a place only if there is no street.
async function addressAt(p) {
    const url = "https://nominatim.openstreetmap.org/reverse?" + new URLSearchParams({
        lat: p.lat, lon: p.lon, format: "jsonv2", zoom: "18", "accept-language": "pt-PT",
    });
    try {
        const r = await (await fetch(url)).json();
        const a = r.address || {};
        if (a.road) return a.house_number ? `${a.road}, ${a.house_number}` : a.road;
        return r.name || a.pedestrian || a.footway || a.square || null;
    } catch {
        return null;
    }
}

$("report-address-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = $("report-address").value.trim();
    if (!query) return;
    clearTimeout(reportGeocodeTimer);
    reportGeocodeSeq++; // a pending reverse lookup must not overwrite what the person typed
    $("report-address-status").textContent = "A procurar…";
    const url = "https://nominatim.openstreetmap.org/search?" + new URLSearchParams({
        q: query, format: "jsonv2", limit: "1", countrycodes: "pt",
        viewbox: PORTO_VIEWBOX, bounded: "1", "accept-language": "pt-PT",
    });
    try {
        const [r] = await (await fetch(url)).json();
        if (!r) {
            $("report-address-status").textContent = "Não encontrámos essa morada no Porto. Experimente mover o mapa.";
            return;
        }
        $("report-address-status").textContent = "Confirme no mapa que o pino está no sítio certo.";
        reportKeepAddress = true;
        reportMap.setView([Number(r.lat), Number(r.lon)], 18);
    } catch {
        $("report-address-status").textContent = "A pesquisa falhou. Experimente mover o mapa.";
    }
});

$("report-locate").addEventListener("click", async () => {
    $("report-address-status").textContent = "A procurar onde está…";
    const p = await currentPosition();
    if (!p) {
        $("report-address-status").textContent = "Não conseguimos saber onde está. Mova o mapa ou escreva a morada.";
        return;
    }
    reportMap.setView([p.lat, p.lon], 18);
});

// Photo: the phone offers the camera or the gallery; we shrink it so it fits in the browser's storage.
$("photo-btn").addEventListener("click", () => $("photo-input").click());
$("photo-remove").addEventListener("click", () => setReportPhoto(null));
$("photo-input").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try {
        setReportPhoto(await shrinkPhoto(file, PHOTO_MAX_PX));
    } catch {
        showToast("Não foi possível usar esta foto. Experimente outra.");
    }
});

function setReportPhoto(dataUrl) {
    report.photo = dataUrl;
    $("photo-preview").hidden = !dataUrl;
    $("photo-img").src = dataUrl || "";
    $("photo-btn-text").textContent = dataUrl ? "Trocar foto" : "Adicionar foto (opcional)";
}

async function shrinkPhoto(file, maxPx) {
    const url = URL.createObjectURL(file);
    try {
        const img = new Image();
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            img.src = url;
        });
        const scale = Math.min(1, maxPx / Math.max(img.naturalWidth, img.naturalHeight));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.naturalWidth * scale);
        canvas.height = Math.round(img.naturalHeight * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/jpeg", 0.7);
    } finally {
        URL.revokeObjectURL(url);
    }
}

$("report-send").addEventListener("click", () => {
    const point = state.reportPoint;
    if (!point || !report.kind) return;
    const now = new Date();
    const barrier = {
        id: `b${now.getTime().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
        kind: report.kind,
        description: $("description-input").value.trim(),
        lat: Number(point.lat.toFixed(6)),
        lon: Number(point.lon.toFixed(6)),
        reported_at: now.toISOString(),
        expires_at: new Date(now.getTime() + REPORT_HOURS * 3600 * 1000).toISOString(),
    };
    if (report.photo) barrier.photo = report.photo;
    const address = $("report-address").value.trim();
    if (address) barrier.address = address;
    $("report-dialog").close();
    const messages = {
        shared: "Obrigado! Os caminhos de todos passam a evitar este obstáculo.",
        device: "Obrigado! O obstáculo ficou no mapa e os seus caminhos passam a evitá-lo.",
        "device-no-photo": "Guardámos o obstáculo, mas a foto não coube na memória do navegador.",
        memory: "O obstáculo está no mapa, mas o navegador não o deixou guardar: desaparece se fechar a página.",
        failed: "Não foi possível enviar o reporte. Tente de novo dentro de momentos.",
    };
    showToast(messages[addBarrier(barrier)], 4500);
});

// Expired barriers disappear without waiting for a new message.
setInterval(renderBarriers, 60 * 1000);

// ---------------------------------------------------------------------------------------------------------------
// Start

refreshIcons();
const saved = loadNeeds();
applyNeeds(saved || profileNeeds("wheelchair"));
$("welcome").hidden = !!saved;
showScreen("plan");
renderBarriers();
connectBroker();
