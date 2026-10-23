// Porto Street Maintenance: citizen-facing report form.
// Frontend only for now: reports are kept in localStorage. Later, sendReport()
// will publish the same JSON to the Coreflux broker on "porto/reports/new".

const PORTO_CENTER = [41.1579, -8.6291];
const STORAGE_KEY = "porto-reports";

// Category → label and the city team that receives it.
const CATEGORIES = {
  pothole:     { label: "Pothole",          department: "Roads" },
  sidewalk:    { label: "Broken sidewalk",  department: "Roads" },
  streetlight: { label: "Streetlight",      department: "Lighting" },
  garbage:     { label: "Garbage",          department: "Waste" },
  graffiti:    { label: "Graffiti",         department: "Waste" },
  tree:        { label: "Tree / park",      department: "Green spaces" },
  signage:     { label: "Road sign",        department: "Roads" },
  other:       { label: "Other",            department: "General" },
};

const form = document.getElementById("report-form");
const dropzone = document.getElementById("dropzone");
const photoInput = document.getElementById("photo");
const photoPreview = document.getElementById("photo-preview");
const photoError = document.getElementById("photo-error");
const categoryError = document.getElementById("category-error");
const descriptionInput = document.getElementById("description");
const locationStatus = document.getElementById("location-status");
const myLocationButton = document.getElementById("use-my-location");
const routing = document.getElementById("routing");
const submitButton = document.getElementById("submit");
const reportList = document.getElementById("report-list");
const reportCount = document.getElementById("report-count");
const emptyState = document.getElementById("empty");
const toast = document.getElementById("toast");

let photoData = null;       // resized photo as a data URL
let pickedLocation = null;  // { lat, lng, source }

function selectedCategory() {
  return form.querySelector('input[name="category"]:checked')?.value || null;
}

// --- Map -------------------------------------------------------------------

const map = L.map("map").setView(PORTO_CENTER, 13);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);
let marker = null;

function setLocationStatus(text, kind) {
  locationStatus.textContent = text;
  locationStatus.className = "location-chip" + (kind ? " " + kind : "");
}

function setLocation(lat, lng, source) {
  pickedLocation = { lat, lng, source };
  if (marker) marker.setLatLng([lat, lng]);
  else marker = L.marker([lat, lng]).addTo(map);
  map.setView([lat, lng], 17);
  const labels = { photo: "from photo", browser: "your location", map: "set on map" };
  setLocationStatus(`${lat.toFixed(5)}, ${lng.toFixed(5)} · ${labels[source]}`, "set");
}

map.on("click", (e) => setLocation(e.latlng.lat, e.latlng.lng, "map"));

myLocationButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setLocationStatus("Location not available in this browser. Click the map instead.", "warn");
    return;
  }
  setLocationStatus("Getting your location…");
  navigator.geolocation.getCurrentPosition(
    (pos) => setLocation(pos.coords.latitude, pos.coords.longitude, "browser"),
    () => setLocationStatus("Couldn't get your location. Click the map instead.", "warn")
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
    setLocationStatus("This photo has no location. Use your location or click the map.", "warn");
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
  const { department } = CATEGORIES[e.target.value];
  routing.innerHTML = `Will be routed to <strong>${department}</strong>`;
});

// --- Submit ----------------------------------------------------------------

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const category = selectedCategory();

  photoError.hidden = !!photoData;
  categoryError.hidden = !!category;
  if (!pickedLocation) {
    setLocationStatus("A location is required: use your location or click the map.", "warn");
  }
  if (!photoData || !category || !pickedLocation) return;

  const report = {
    id: `R-${Date.now().toString(36).toUpperCase().slice(-6)}`,
    category,
    department: CATEGORIES[category].department,
    description: descriptionInput.value.trim(),
    lat: pickedLocation.lat,
    lng: pickedLocation.lng,
    gpsSource: pickedLocation.source,
    photo: photoData,
    createdAt: new Date().toISOString(),
    status: "received",
  };

  submitButton.disabled = true;
  sendReport(report);
  submitButton.disabled = false;

  resetForm();
  showToast(`Report ${report.id} sent to ${report.department}`);
});

function resetForm() {
  form.reset();
  photoData = null;
  photoPreview.hidden = true;
  dropzone.classList.remove("has-photo");
  pickedLocation = null;
  if (marker) { map.removeLayer(marker); marker = null; }
  map.setView(PORTO_CENTER, 13);
  setLocationStatus("Upload a photo, use your location, or click the map");
  routing.textContent = "Select an issue type to see which team receives it";
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
    const info = CATEGORIES[r.category] || { label: r.category, department: "General" };
    const li = document.createElement("li");
    li.className = "ticket";
    li.innerHTML = `
      <img src="${r.photo}" alt="">
      <div class="ticket-body">
        <div class="ticket-top">
          <span class="ticket-id"></span>
          <span class="status status-${r.status}">${r.status}</span>
        </div>
        <div class="ticket-title"></div>
        <div class="ticket-desc"></div>
        <div class="ticket-meta"></div>
      </div>`;
    li.querySelector(".ticket-id").textContent = r.id;
    li.querySelector(".ticket-title").textContent = `${info.label} · ${info.department}`;
    li.querySelector(".ticket-desc").textContent = r.description || "No description";
    li.querySelector(".ticket-meta").textContent = new Date(r.createdAt).toLocaleString();
    reportList.appendChild(li);
  }
}

renderReports();
