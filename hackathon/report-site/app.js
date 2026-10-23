// Rua Viva: citizen-facing report form.
// Frontend only for now: reports are kept in localStorage. Later, sendReport()
// will publish the same JSON to the Coreflux broker on "porto/reports/new".

// Rough bounding box of the municipality of Porto (south-west, north-east).
const PORTO_BOUNDS = L.latLngBounds([41.136, -8.695], [41.188, -8.551]);
// OpenStreetMap's free geocoder (max ~1 request/second, fine for a demo).
const NOMINATIM = "https://nominatim.openstreetmap.org";
const STORAGE_KEY = "porto-reports";

// Category → label shown to citizens and the department that receives it.
// Keys stay in English (they go into the report JSON / MQTT); labels are pt-PT.
const DEPARTMENTS = {
  roads:    "Vias públicas",
  lighting: "Iluminação pública",
  waste:    "Higiene urbana",
  green:    "Espaços verdes",
  general:  "Geral",
};
const CATEGORIES = {
  pothole:     { label: "Buraco na estrada",  department: "roads" },
  sidewalk:    { label: "Passeio danificado", department: "roads" },
  streetlight: { label: "Iluminação",         department: "lighting" },
  garbage:     { label: "Lixo",               department: "waste" },
  graffiti:    { label: "Grafíti",            department: "waste" },
  tree:        { label: "Árvore / jardim",    department: "green" },
  signage:     { label: "Sinalização",        department: "roads" },
  other:       { label: "Outro",              department: "general" },
};
const STATUS_LABELS = { received: "Recebida", assigned: "Atribuída", fixed: "Resolvida" };

const form = document.getElementById("report-form");
const dropzone = document.getElementById("dropzone");
const photoInput = document.getElementById("photo");
const photoPreview = document.getElementById("photo-preview");
const photoError = document.getElementById("photo-error");
const categoryError = document.getElementById("category-error");
const otherTypeWrap = document.getElementById("other-type-wrap");
const otherTypeInput = document.getElementById("other-type");
const descriptionInput = document.getElementById("description");
const locationStatus = document.getElementById("location-status");
const addressInput = document.getElementById("address");
const addressResults = document.getElementById("address-results");
const myLocationButton = document.getElementById("use-my-location");
const routing = document.getElementById("routing");
const submitButton = document.getElementById("submit");
const reportList = document.getElementById("report-list");
const reportCount = document.getElementById("report-count");
const emptyState = document.getElementById("empty");
const toast = document.getElementById("toast");

let photoData = null;       // resized photo as a data URL
let pickedLocation = null;  // { lat, lng, source, address }

function selectedCategory() {
  return form.querySelector('input[name="category"]:checked')?.value || null;
}

// --- Map -------------------------------------------------------------------

const map = L.map("map", {
  maxBounds: PORTO_BOUNDS.pad(0.05),
  maxBoundsViscosity: 1.0,   // can't drag the map out of Porto
  minZoom: 12,
}).fitBounds(PORTO_BOUNDS);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
  bounds: PORTO_BOUNDS.pad(0.05),
}).addTo(map);
let marker = null;

// Dim everything outside the service area.
const world = [[-85, -180], [-85, 180], [85, 180], [85, -180]];
const area = [
  PORTO_BOUNDS.getSouthWest(), PORTO_BOUNDS.getNorthWest(),
  PORTO_BOUNDS.getNorthEast(), PORTO_BOUNDS.getSouthEast(),
];
L.polygon([world, area], {
  stroke: false, fillColor: "#14212f", fillOpacity: 0.35, interactive: false,
}).addTo(map);
L.rectangle(PORTO_BOUNDS, {
  color: "#f5a400", weight: 2, dashArray: "6 6", fill: false, interactive: false,
}).addTo(map);

function setLocationStatus(text, kind) {
  locationStatus.textContent = text;
  locationStatus.className = "location-chip" + (kind ? " " + kind : "");
}

function setLocation(lat, lng, source, address) {
  if (!PORTO_BOUNDS.contains([lat, lng])) {
    const where = { photo: "Esta fotografia foi tirada", browser: "Está", map: "Esse ponto fica", address: "Essa morada fica" }[source];
    setLocationStatus(`${where} fora do Porto. Só é possível comunicar ocorrências no Porto; clique dentro da área.`, "warn");
    return;
  }
  const loc = { lat, lng, source, address: address || null };
  pickedLocation = loc;
  if (marker) marker.setLatLng([lat, lng]);
  else marker = L.marker([lat, lng]).addTo(map);
  map.setView([lat, lng], 17);
  showPickedLocation();
  if (address) addressInput.value = address;
  else lookUpAddress(loc);
}

function showPickedLocation() {
  const { lat, lng, source, address } = pickedLocation;
  const labels = { photo: "da fotografia", browser: "a sua localização", map: "marcado no mapa", address: "da morada" };
  const where = address || `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  setLocationStatus(`${where} · ${labels[source]}`, "set");
}

// --- Address: search and reverse lookup -----------------------------------

// "Rua X, 100, Cedofeita, Porto, ..." → "Rua X 100, Cedofeita"
function shortAddress(a, fallback) {
  if (!a) return fallback;
  const street = [a.road || a.pedestrian || a.footway || a.square, a.house_number].filter(Boolean).join(" ");
  const area = a.suburb || a.quarter || a.neighbourhood || a.city_district;
  return [street, area].filter(Boolean).join(", ") || fallback;
}

// The bounding box also covers bits of Gaia and Matosinhos; the address tells us for sure.
function municipalityOf(a) {
  return a && (a.city || a.town || a.municipality || a.village);
}

// Fills in the street name for a point picked on the map, by photo or by GPS.
async function lookUpAddress(loc) {
  try {
    const res = await fetch(`${NOMINATIM}/reverse?format=jsonv2&accept-language=pt-PT&addressdetails=1&zoom=18&lat=${loc.lat}&lon=${loc.lng}`);
    const data = await res.json();
    if (pickedLocation !== loc) return;   // user picked another point meanwhile
    const city = municipalityOf(data.address);
    if (city && city !== "Porto") {
      pickedLocation = null;
      map.removeLayer(marker);
      marker = null;
      addressInput.value = "";
      setLocationStatus(`Esse ponto fica em ${city}, fora do Porto. Só é possível comunicar ocorrências no Porto.`, "warn");
      return;
    }
    loc.address = shortAddress(data.address, data.display_name);
    addressInput.value = loc.address || "";
    showPickedLocation();
  } catch (_) { /* keep showing coordinates */ }
}

let searchTimer = null;
let searchResults = [];
let activeResult = -1;

addressInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const q = addressInput.value.trim();
  if (q.length < 3) { hideResults(); return; }
  searchTimer = setTimeout(() => searchAddress(q), 450);
});

async function searchAddress(q) {
  const box = [PORTO_BOUNDS.getWest(), PORTO_BOUNDS.getNorth(), PORTO_BOUNDS.getEast(), PORTO_BOUNDS.getSouth()].join(",");
  const url = `${NOMINATIM}/search?format=jsonv2&accept-language=pt-PT&addressdetails=1&limit=5&countrycodes=pt`
    + `&viewbox=${box}&bounded=1&q=${encodeURIComponent(q)}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    if (addressInput.value.trim() !== q) return;   // user kept typing
    const seen = new Set();
    searchResults = data
      .filter((r) => municipalityOf(r.address) === "Porto")
      .map((r) => ({
        lat: parseFloat(r.lat),
        lng: parseFloat(r.lon),
        title: shortAddress(r.address, r.name || r.display_name),
        detail: [r.address?.postcode, r.address?.city || "Porto"].filter(Boolean).join(" "),
      }))
      .filter((r) => !seen.has(r.title) && seen.add(r.title));   // one row per street/place
    renderResults();
  } catch (_) {
    searchResults = [];
    renderResults("A pesquisa de moradas não está disponível. Clique no mapa.");
  }
}

function renderResults(note) {
  activeResult = -1;
  addressResults.innerHTML = "";
  if (!searchResults.length) {
    const li = document.createElement("li");
    li.className = "note";
    li.textContent = note || "Nenhuma morada encontrada no Porto.";
    addressResults.appendChild(li);
  }
  searchResults.forEach((r, i) => {
    const li = document.createElement("li");
    li.innerHTML = "<span></span><small></small>";
    li.firstChild.textContent = r.title;
    li.lastChild.textContent = r.detail;
    li.addEventListener("mousedown", (e) => { e.preventDefault(); chooseResult(i); });
    addressResults.appendChild(li);
  });
  addressResults.hidden = false;
}

function chooseResult(i) {
  const r = searchResults[i];
  if (!r) return;
  hideResults();
  setLocation(r.lat, r.lng, "address", r.title);
}

function hideResults() {
  addressResults.hidden = true;
  searchResults = [];
}

addressInput.addEventListener("keydown", (e) => {
  if (addressResults.hidden) return;
  const items = addressResults.querySelectorAll("li:not(.note)");
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    activeResult = (activeResult + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
    items.forEach((li, i) => li.classList.toggle("active", i === activeResult));
  } else if (e.key === "Enter") {
    e.preventDefault();   // don't submit the whole form
    chooseResult(Math.max(activeResult, 0));
  } else if (e.key === "Escape") {
    hideResults();
  }
});
addressInput.addEventListener("blur", () => setTimeout(hideResults, 100));

map.on("click", (e) => setLocation(e.latlng.lat, e.latlng.lng, "map"));

myLocationButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setLocationStatus("Localização indisponível neste navegador. Escreva uma morada ou clique no mapa.", "warn");
    return;
  }
  setLocationStatus("A obter a sua localização…");
  navigator.geolocation.getCurrentPosition(
    (pos) => setLocation(pos.coords.latitude, pos.coords.longitude, "browser"),
    (err) => setLocationStatus(err.code === err.PERMISSION_DENIED
      ? "O acesso à localização está bloqueado neste navegador. Permita-o ou escreva uma morada."
      : "Não foi possível obter a sua localização. Escreva uma morada ou clique no mapa.", "warn")
  );
});

// --- Photo -----------------------------------------------------------------

["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, () => dropzone.classList.add("drag")));
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, () => dropzone.classList.remove("drag")));

photoInput.addEventListener("change", async () => {
  const file = photoInput.files[0];
  if (!file) return;

  photoData = await resizeImage(file, 800);
  photoPreview.src = photoData;
  photoPreview.hidden = false;
  dropzone.classList.add("has-photo");
  photoError.hidden = true;

  // Phone photos usually carry GPS coordinates in their EXIF metadata.
  try {
    const gps = await exifr.gps(file);
    if (gps) {
      setLocation(gps.latitude, gps.longitude, "photo");
      return;
    }
  } catch (_) { /* no EXIF, fall through */ }
  if (!pickedLocation) {
    setLocationStatus("Esta fotografia não tem localização. Escreva uma morada ou clique no mapa.", "warn");
  }
});

// Shrinks the image so it stays small enough to send over MQTT later.
function resizeImage(file, maxWidth) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxWidth / img.width);
      const canvas = document.createElement("canvas");
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(img.src);
      resolve(canvas.toDataURL("image/jpeg", 0.7));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

// --- Category → routing hint -------------------------------------------------

form.addEventListener("change", (e) => {
  if (e.target.name !== "category") return;
  categoryError.hidden = true;
  const isOther = e.target.value === "other";
  otherTypeWrap.hidden = !isOther;
  if (isOther) otherTypeInput.focus();
  const { department } = CATEGORIES[e.target.value];
  routing.innerHTML = `Será encaminhada para <strong>${DEPARTMENTS[department]}</strong>`;
});

// --- Submit ----------------------------------------------------------------

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const category = selectedCategory();
  const otherType = category === "other" ? otherTypeInput.value.trim() : "";
  const categoryOk = category && (category !== "other" || otherType);

  photoError.hidden = !!photoData;
  categoryError.textContent = category ? "Indique que tipo de problema é." : "Escolha o tipo de problema.";
  categoryError.hidden = !!categoryOk;
  if (!pickedLocation) {
    setLocationStatus("A localização é obrigatória: escreva uma morada ou clique no mapa.", "warn");
  }
  if (!photoData || !categoryOk || !pickedLocation) return;

  const report = {
    id: `R-${Date.now().toString(36).toUpperCase().slice(-6)}`,
    category,
    otherType,
    department: CATEGORIES[category].department,
    description: descriptionInput.value.trim(),
    lat: pickedLocation.lat,
    lng: pickedLocation.lng,
    gpsSource: pickedLocation.source,
    address: pickedLocation.address,
    photo: photoData,
    createdAt: new Date().toISOString(),
    status: "received",
  };

  submitButton.disabled = true;
  sendReport(report);
  submitButton.disabled = false;

  resetForm();
  showToast(`Ocorrência ${report.id} enviada para ${DEPARTMENTS[report.department]}`);
});

function resetForm() {
  form.reset();
  photoData = null;
  photoPreview.hidden = true;
  dropzone.classList.remove("has-photo");
  otherTypeWrap.hidden = true;
  pickedLocation = null;
  if (marker) { map.removeLayer(marker); marker = null; }
  map.fitBounds(PORTO_BOUNDS);
  addressInput.value = "";
  setLocationStatus("Carregue uma fotografia, escreva uma morada ou clique no mapa");
  routing.textContent = "Escolha o tipo de problema para ver que equipa o recebe";
}

let toastTimer = null;
function showToast(text) {
  toast.textContent = text;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toast.hidden = true), 3500);
}

// TODO: replace with an MQTT publish to the Coreflux broker.
function sendReport(report) {
  console.log("Report payload:", report);
  const reports = loadReports();
  reports.unshift(report);
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(reports)); } catch (_) {}
  renderReports();
}

function loadReports() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; } catch (_) { return []; }
}

// --- My reports ------------------------------------------------------------

function renderReports() {
  const reports = loadReports();
  reportCount.textContent = reports.length;
  emptyState.hidden = reports.length > 0;
  reportList.innerHTML = "";
  for (const r of reports) {
    const info = CATEGORIES[r.category] || { label: r.category, department: "general" };
    const li = document.createElement("li");
    li.className = "ticket";
    li.innerHTML = `
      <img src="${r.photo}" alt="">
      <div class="ticket-body">
        <div class="ticket-top">
          <span class="ticket-id"></span>
          <span class="status status-${r.status}">${STATUS_LABELS[r.status] || r.status}</span>
        </div>
        <div class="ticket-title"></div>
        <div class="ticket-desc"></div>
        <div class="ticket-meta"></div>
      </div>`;
    li.querySelector(".ticket-id").textContent = r.id;
    const label = r.otherType ? `Outro: ${r.otherType}` : info.label;
    li.querySelector(".ticket-title").textContent = `${label} · ${DEPARTMENTS[info.department] || info.department}`;
    li.querySelector(".ticket-desc").textContent = r.description || "Sem descrição";
    li.querySelector(".ticket-meta").textContent =
      [r.address, new Date(r.createdAt).toLocaleString("pt-PT")].filter(Boolean).join(" · ");
    reportList.appendChild(li);
  }
}

renderReports();
