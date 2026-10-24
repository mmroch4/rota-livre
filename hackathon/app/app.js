// Accessible route planner: picks two points, asks Valhalla for a pedestrian route under the user's limits,
// and shares barrier reports through the Coreflux broker (MQTT over WebSocket).
"use strict";

const config = window.APP_CONFIG;
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------------------------------------------
// Profiles. Valhalla's pedestrian costing has two types: "wheelchair" (only hard surfaces, compacted or better)
// and "foot". Kerb height is not something Valhalla can filter on, so there is no option for it.

const PROFILES = {
    wheelchair: { maxGrade: 6, avoidSteps: true, avoidRoughSurface: true },
    walker: { maxGrade: 8, avoidSteps: true, avoidRoughSurface: true },
    stroller: { maxGrade: 10, avoidSteps: true, avoidRoughSurface: false },
};

const MAX_STEP_PENALTY = 43200; // seconds: Valhalla's upper bound (12 h), so steps are used only as a last resort
const GRADE_LIMIT = 15;         // highest slope the slider offers, in %
const BARRIER_RADIUS_M = 15;    // half the side of the square excluded around each barrier
const NO_ELEVATION = 32768;     // Valhalla's marker for "no elevation data" on an edge

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
    from: null, // {lat, lon, label}
    to: null,
    barriers: new Map(), // id -> barrier message
    reporting: false,
    pendingReport: null, // {lat, lon} waiting for the dialog
};

let routeLayer = null;
let markers = { from: null, to: null };
const barrierLayer = L.layerGroup();
let mqttClient = null;

// ---------------------------------------------------------------------------------------------------------------
// Map

const map = L.map("map", { zoomControl: true }).setView(config.center, config.zoom);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
barrierLayer.addTo(map);

map.on("click", (e) => {
    const point = { lat: e.latlng.lat, lon: e.latlng.lng };
    if (state.reporting) {
        openReportDialog(point);
        return;
    }
    if (!state.from) setEndpoint("from", { ...point, label: formatCoords(point) });
    else setEndpoint("to", { ...point, label: formatCoords(point) });
});

function setEndpoint(which, point) {
    state[which] = point;
    $(`${which}-input`).value = point.label;
    if (markers[which]) {
        markers[which].setLatLng([point.lat, point.lon]);
    } else {
        markers[which] = L.marker([point.lat, point.lon], {
            draggable: true,
            title: which === "from" ? "Partida" : "Destino",
            icon: endpointIcon(which),
        }).addTo(map);
        markers[which].on("dragend", (e) => {
            const ll = e.target.getLatLng();
            const moved = { lat: ll.lat, lon: ll.lng };
            setEndpoint(which, { ...moved, label: formatCoords(moved) });
        });
    }
    if (state.from && state.to) requestRoute();
}

function endpointIcon(which) {
    return L.divIcon({
        className: `endpoint endpoint-${which}`,
        html: which === "from" ? "A" : "B",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

function formatCoords(p) {
    return `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`;
}

// ---------------------------------------------------------------------------------------------------------------
// Address search (Nominatim, limited to the Porto area). Its usage policy allows light use: we search only
// when the user presses Enter, never on every keystroke.

const PORTO_VIEWBOX = "-8.70,41.19,-8.54,41.13"; // left,top,right,bottom

for (const which of ["from", "to"]) {
    const input = $(`${which}-input`);
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            searchAddress(which, input.value.trim());
        }
    });
}

async function searchAddress(which, query) {
    const list = $(`${which}-suggestions`);
    list.replaceChildren();
    list.hidden = true;
    if (!query) return;
    const url = "https://nominatim.openstreetmap.org/search?" + new URLSearchParams({
        q: query,
        format: "jsonv2",
        limit: "5",
        countrycodes: "pt",
        viewbox: PORTO_VIEWBOX,
        bounded: "1",
        "accept-language": "pt-PT",
    });
    try {
        const res = await fetch(url, { headers: { Accept: "application/json" } });
        const results = await res.json();
        if (results.length === 0) {
            list.append(item("Sem resultados no Porto.", null));
        }
        for (const r of results) {
            list.append(item(r.display_name, () => {
                setEndpoint(which, { lat: Number(r.lat), lon: Number(r.lon), label: r.display_name });
                map.panTo([Number(r.lat), Number(r.lon)]);
                list.hidden = true;
            }));
        }
        list.hidden = false;
    } catch {
        list.append(item("A pesquisa falhou. Tente de novo ou toque no mapa.", null));
        list.hidden = false;
    }

    function item(text, onPick) {
        const li = document.createElement("li");
        if (onPick) {
            const b = document.createElement("button");
            b.type = "button";
            b.textContent = text;
            b.addEventListener("click", onPick);
            li.append(b);
        } else {
            li.textContent = text;
        }
        return li;
    }
}

$("locate-btn").addEventListener("click", () => {
    if (!navigator.geolocation) {
        showMessage("Este dispositivo não permite obter a localização.");
        return;
    }
    $("locate-btn").disabled = true;
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            $("locate-btn").disabled = false;
            const p = { lat: pos.coords.latitude, lon: pos.coords.longitude };
            setEndpoint("from", { ...p, label: "A minha localização" });
            map.setView([p.lat, p.lon], 17);
        },
        () => {
            $("locate-btn").disabled = false;
            showMessage("Não foi possível obter a sua localização. Toque no mapa para escolher a partida.");
        },
        { enableHighAccuracy: true, timeout: 10000 },
    );
});

// ---------------------------------------------------------------------------------------------------------------
// Needs (profile, slope, steps, surface)

$("profile-select").addEventListener("change", (e) => {
    const p = PROFILES[e.target.value];
    if (!p) return; // "custom" keeps whatever is set
    $("grade-input").value = p.maxGrade;
    $("grade-output").value = p.maxGrade;
    $("steps-check").checked = p.avoidSteps;
    $("surface-check").checked = p.avoidRoughSurface;
    rerouteIfReady();
});

$("grade-input").addEventListener("input", (e) => {
    $("grade-output").value = e.target.value;
});
for (const id of ["grade-input", "steps-check", "surface-check", "barriers-check"]) {
    $(id).addEventListener("change", () => {
        if (id !== "barriers-check") $("profile-select").value = matchingProfile();
        rerouteIfReady();
    });
}

function matchingProfile() {
    const needs = readNeeds();
    for (const [name, p] of Object.entries(PROFILES)) {
        if (p.maxGrade === needs.maxGrade && p.avoidSteps === needs.avoidSteps
            && p.avoidRoughSurface === needs.avoidRoughSurface) return name;
    }
    return "custom";
}

function readNeeds() {
    return {
        maxGrade: Number($("grade-input").value),
        avoidSteps: $("steps-check").checked,
        avoidRoughSurface: $("surface-check").checked,
        avoidBarriers: $("barriers-check").checked,
    };
}

function rerouteIfReady() {
    if (state.from && state.to) requestRoute();
}

// ---------------------------------------------------------------------------------------------------------------
// Routing (Valhalla)

$("route-btn").addEventListener("click", () => {
    if (!state.from || !state.to) {
        showMessage("Escolha a partida e o destino (pesquise ou toque no mapa).");
        return;
    }
    requestRoute();
});

$("clear-btn").addEventListener("click", () => {
    for (const which of ["from", "to"]) {
        state[which] = null;
        $(`${which}-input`).value = "";
        $(`${which}-suggestions`).hidden = true;
        if (markers[which]) map.removeLayer(markers[which]);
        markers[which] = null;
    }
    clearRoute();
    hideMessage();
});

function costing(needs) {
    const pedestrian = {
        // The wheelchair type is the only way to keep Valhalla off unpaved/rough surfaces.
        type: needs.avoidRoughSurface ? "wheelchair" : "foot",
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
    return [
        [lon - dLon, lat - dLat],
        [lon + dLon, lat - dLat],
        [lon + dLon, lat + dLat],
        [lon - dLon, lat + dLat],
        [lon - dLon, lat - dLat],
    ];
}

let routeRequestId = 0;

async function requestRoute() {
    if (!config.valhallaUrl) {
        showMessage("O servidor de percursos ainda não está configurado (valhallaUrl em config.js).");
        return;
    }
    const needs = readNeeds();
    const myRequest = ++routeRequestId;
    showMessage("A calcular o percurso…");
    $("route-btn").disabled = true;

    const body = {
        locations: [
            { lat: state.from.lat, lon: state.from.lon },
            { lat: state.to.lat, lon: state.to.lon },
        ],
        ...costing(needs),
        exclude_polygons: excludedAreas(needs),
        units: "kilometers",
        language: "pt-PT",
    };

    try {
        const res = await fetch(`${config.valhallaUrl}/route`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (myRequest !== routeRequestId) return; // a newer request replaced this one
        if (!res.ok || !data.trip) {
            showRouteError(data, needs);
            return;
        }
        const leg = data.trip.legs[0];
        const shape = decodePolyline6(leg.shape);
        drawRoute(shape);
        showSummary(data.trip, leg);
        hideMessage();
        loadSlopeDetails(leg.shape, needs, shape, myRequest);
    } catch {
        if (myRequest !== routeRequestId) return;
        clearRoute();
        showMessage("Não foi possível falar com o servidor de percursos. Verifique a ligação e tente de novo.");
    } finally {
        if (myRequest === routeRequestId) $("route-btn").disabled = false;
    }
}

// Never relax the limits on our own: explain and let the user decide.
function showRouteError(data, needs) {
    clearRoute();
    const code = data && data.error_code;
    if (code === 442 || code === 443) {
        const higher = needs.maxGrade + 2;
        const parts = [`Não há percurso que respeite as suas condições (inclinação até ${needs.maxGrade}%`];
        if (needs.avoidSteps) parts.push("sem escadas");
        if (needs.avoidRoughSurface) parts.push("piso regular");
        if (needs.avoidBarriers && activeBarriers().length) parts.push("a evitar obstáculos");
        let text = parts.join(", ") + ").";
        if (higher <= GRADE_LIMIT) {
            showMessage(text, {
                label: `Tentar com inclinação até ${higher}%`,
                onClick: () => {
                    $("grade-input").value = higher;
                    $("grade-output").value = higher;
                    $("profile-select").value = matchingProfile();
                    requestRoute();
                },
            });
        } else {
            showMessage(text + " Experimente outro destino ou desligue alguma das opções.");
        }
    } else if (code === 171 || code === 170) {
        showMessage("A partida ou o destino estão longe de um caminho acessível. Escolha um ponto mais perto de um passeio.");
    } else {
        showMessage(`O servidor de percursos devolveu um erro${data && data.error ? `: ${data.error}` : "."}`);
    }
}

function drawRoute(shape) {
    clearRoute();
    routeLayer = L.layerGroup().addTo(map);
    L.polyline(shape, { className: "route-line", weight: 6 }).addTo(routeLayer);
    map.fitBounds(L.latLngBounds(shape), { padding: [40, 40] });
}

function clearRoute() {
    if (routeLayer) map.removeLayer(routeLayer);
    routeLayer = null;
    $("summary").hidden = true;
}

function showSummary(trip, leg) {
    $("sum-distance").textContent = formatDistance(trip.summary.length);
    $("sum-time").textContent = formatDuration(trip.summary.time);
    $("sum-slopes").textContent = "";
    $("warnings").replaceChildren();
    const list = $("maneuvers");
    list.replaceChildren();
    for (const m of leg.maneuvers) {
        const li = document.createElement("li");
        li.textContent = m.instruction;
        if (m.length > 0) {
            const span = document.createElement("span");
            span.className = "dist";
            span.textContent = ` (${formatDistance(m.length)})`;
            li.append(span);
        }
        list.append(li);
    }
    $("summary").hidden = false;
}

// Asks Valhalla for the slope and surface of every edge of the route, to show the steepest parts.
// Valhalla stores edge slopes in degrees; we show them as % like the slider.
async function loadSlopeDetails(encodedShape, needs, shape, myRequest) {
    try {
        const res = await fetch(`${config.valhallaUrl}/trace_attributes`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                encoded_polyline: encodedShape,
                shape_match: "edge_walk",
                ...costing(needs),
                filters: {
                    attributes: [
                        "edge.length", "edge.use", "edge.surface", "edge.max_upward_grade",
                        "edge.max_downward_grade", "edge.begin_shape_index", "edge.end_shape_index",
                    ],
                    action: "include",
                },
            }),
        });
        const data = await res.json();
        if (myRequest !== routeRequestId || !res.ok || !data.edges) return;
        showSlopeDetails(data.edges, needs, shape);
    } catch {
        // The details are a bonus: the route itself is already on screen.
    }
}

function showSlopeDetails(edges, needs, shape) {
    let steepestUp = 0;
    let steepestDown = 0;
    let unknown = 0;
    const warnings = [];
    const nearLimit = Math.max(needs.maxGrade - 1, 3);

    for (const e of edges) {
        const known = Math.abs(e.max_upward_grade) < NO_ELEVATION && Math.abs(e.max_downward_grade) < NO_ELEVATION;
        if (!known) {
            unknown += e.length || 0;
            continue;
        }
        const up = degreesToPercent(e.max_upward_grade);
        const down = degreesToPercent(Math.abs(e.max_downward_grade));
        steepestUp = Math.max(steepestUp, up);
        steepestDown = Math.max(steepestDown, down);
        const steep = Math.max(up, down);
        if (steep >= nearLimit) {
            warnings.push({ text: `Troço com ${Math.round(steep)}% de inclinação (${formatDistance(e.length)})`, e });
        }
        if (e.use === "steps") {
            warnings.push({ text: "Este percurso tem escadas: não foi possível evitá-las.", e });
        }
    }

    let slopes = `Subida mais íngreme: ${Math.round(steepestUp)}% · Descida mais íngreme: ${Math.round(steepestDown)}%`;
    if (unknown > 0.05) slopes += ` · Sem dados de inclinação em ${formatDistance(unknown)}`;
    $("sum-slopes").textContent = slopes;

    const list = $("warnings");
    list.replaceChildren();
    for (const w of warnings.slice(0, 8)) {
        const li = document.createElement("li");
        li.textContent = w.text;
        list.append(li);
        if (routeLayer && w.e.end_shape_index > w.e.begin_shape_index) {
            const part = shape.slice(w.e.begin_shape_index, w.e.end_shape_index + 1);
            L.polyline(part, { className: "route-warning", weight: 8 }).addTo(routeLayer);
        }
    }
}

function degreesToPercent(deg) {
    return Math.tan((deg * Math.PI) / 180) * 100;
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

function formatDistance(km) {
    return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1).replace(".", ",")} km`;
}

function formatDuration(seconds) {
    const min = Math.max(1, Math.round(seconds / 60));
    return min < 60 ? `${min} min` : `${Math.floor(min / 60)} h ${min % 60} min`;
}

function showMessage(text, action) {
    const el = $("message");
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

function hideMessage() {
    $("message").hidden = true;
}

// ---------------------------------------------------------------------------------------------------------------
// Barriers (MQTT). Each report is one retained message on <prefix>/barriers/<id>; an empty retained message
// removes it. Reports past their expires_at are ignored.

const barrierTopic = (id) => `${config.topicPrefix}/barriers/${id}`;

function connectBroker() {
    if (!config.brokerUrl) {
        setBrokerStatus("off", "Sem ligação ao servidor de obstáculos (brokerUrl em config.js).");
        return;
    }
    mqttClient = mqtt.connect(config.brokerUrl, {
        username: config.brokerUsername || undefined,
        password: config.brokerPassword || undefined,
        clientId: `access-web-${Math.random().toString(16).slice(2, 10)}`,
        reconnectPeriod: 5000,
    });
    mqttClient.on("connect", () => {
        setBrokerStatus("on", "Ligado: os obstáculos aparecem em tempo real.");
        mqttClient.subscribe(barrierTopic("+"));
    });
    mqttClient.on("reconnect", () => setBrokerStatus("wait", "A ligar…"));
    mqttClient.on("offline", () => setBrokerStatus("off", "Sem ligação. A tentar de novo…"));
    mqttClient.on("error", () => setBrokerStatus("off", "Erro na ligação ao servidor de obstáculos."));
    mqttClient.on("message", onBarrierMessage);
}

function onBarrierMessage(topic, payload) {
    const id = topic.split("/").pop();
    const text = payload.toString();
    if (!text) {
        state.barriers.delete(id);
    } else {
        try {
            const b = JSON.parse(text);
            if (typeof b.lat === "number" && typeof b.lon === "number") state.barriers.set(id, { ...b, id });
        } catch {
            return; // not one of ours
        }
    }
    renderBarriers();
    if (readNeeds().avoidBarriers) rerouteIfReady();
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
            icon: L.divIcon({ className: `barrier barrier-${b.kind}`, html: "!", iconSize: [26, 26], iconAnchor: [13, 13] }),
            title: BARRIER_KINDS[b.kind] || BARRIER_KINDS.other,
        });
        marker.bindPopup(() => barrierPopup(b));
        barrierLayer.addLayer(marker);
    }
    $("barrier-count").textContent = active.length === 1 ? "1 obstáculo ativo." : `${active.length} obstáculos ativos.`;
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
    when.className = "hint";
    when.textContent = `Reportado ${new Date(b.reported_at).toLocaleString("pt-PT")}`
        + (b.expires_at ? ` · evitar até ${new Date(b.expires_at).toLocaleString("pt-PT")}` : "");
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
    $("report-btn").disabled = kind !== "on";
}

function publish(topic, message) {
    if (!mqttClient || !mqttClient.connected) {
        showMessage("Sem ligação ao servidor de obstáculos: o reporte não foi enviado.");
        return;
    }
    mqttClient.publish(topic, message, { qos: 1, retain: true });
}

$("report-btn").addEventListener("click", () => setReporting(true));
$("report-cancel").addEventListener("click", () => setReporting(false));

function setReporting(on) {
    state.reporting = on;
    $("report-hint").hidden = !on;
    $("report-btn").hidden = on;
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
    setReporting(false);
    if ($("report-dialog").returnValue !== "send" || !point) return;
    const hours = Number($("duration-select").value);
    const now = new Date();
    const id = `b${now.getTime().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    const barrier = {
        id,
        kind: $("kind-select").value,
        description: $("description-input").value.trim(),
        lat: Number(point.lat.toFixed(6)),
        lon: Number(point.lon.toFixed(6)),
        reported_at: now.toISOString(),
        expires_at: new Date(now.getTime() + hours * 3600 * 1000).toISOString(),
    };
    publish(barrierTopic(id), JSON.stringify(barrier));
});

// Expired barriers disappear without waiting for a new message.
setInterval(renderBarriers, 60 * 1000);

renderBarriers();
connectBroker();
