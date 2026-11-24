const $ = (selector) => document.querySelector(selector);
const dashboardUrl = "/api/dashboard";
const galleryPageSize = 24;

let allPhotos = [];
let photos = [];
let comparisonIndex = 0;
let referencePhoto = null;
let selectedMonth = "";
let visiblePhotos = galleryPageSize;
let playbackTimer = null;
let dialogIndex = -1;

const dialog = $("#photoDialog");
const slider = $("#rango");

function formatDate(value, options = { day: "numeric", month: "short", year: "numeric" }) {
  if (!value) return "Fecha no disponible";
  return new Date(`${value}T12:00:00`).toLocaleDateString("es-CR", options);
}

function formatDateTime(photo) {
  const date = formatDate(photo.f);
  return photo.h ? `${date} · ${photo.h}` : date;
}

function setApiStatus(connected, message) {
  const state = $("#apiState");
  state.classList.toggle("is-offline", !connected);
  $("#apiStateText").textContent = message;
}

function dayDifference(start, end) {
  if (!start || !end) return 0;
  const first = Date.parse(`${start}T00:00:00Z`);
  const last = Date.parse(`${end}T00:00:00Z`);
  return Number.isFinite(first) && Number.isFinite(last)
    ? Math.max(0, Math.round((last - first) / 86_400_000))
    : 0;
}

function renderProject(data) {
  const stats = data.estadisticas;
  const total = allPhotos.length;
  const percent = stats.porcentaje_conservadas;
  const dates = allPhotos.map((photo) => photo.f).filter(Boolean).sort();
  const firstDate = dates[0];
  const lastDate = dates.at(-1);
  const lastEvidence = photos.at(-1);
  const heroPhoto = [...photos].reverse().find((photo) => !photo.rev) || lastEvidence;

  $("#totalMetric").textContent = stats.total.toLocaleString("es-CR");
  $("#keptMetric").textContent = stats.conservadas.toLocaleString("es-CR");
  $("#dropMetric").textContent = stats.descartadas.toLocaleString("es-CR");
  $("#reviewMetric").textContent = stats.revision.toLocaleString("es-CR");
  $("#inventoryCount").textContent = stats.total.toLocaleString("es-CR");
  $("#darkCount").textContent = stats.descartadas.toLocaleString("es-CR");
  $("#reviewCount").textContent = stats.revision.toLocaleString("es-CR");
  $("#archiveCount").textContent = stats.conservadas.toLocaleString("es-CR");
  $("#keepPercent").textContent = `${percent.toFixed(1)}% CONSERVADAS`;
  $("#keepBar").style.width = `${percent}%`;
  $("#dropBar").style.width = `${100 - percent}%`;
  $("#projectName").textContent = data.obra.nombre || "Proyecto sin nombre";
  $("#projectRange").textContent = firstDate && lastDate
    ? `${formatDate(firstDate)} — ${formatDate(lastDate)}`
    : "Periodo no disponible";
  $("#periodValue").textContent = firstDate && lastDate
    ? dayDifference(firstDate, lastDate)
    : "—";

  if (heroPhoto) {
    $("#heroImage").src = heroPhoto.p;
    $("#heroImage").alt = `Fotografía del ${formatDateTime(heroPhoto)}.`;
    $("#ultimaHero").textContent = formatDateTime(heroPhoto);
    $("#heroReview").hidden = !heroPhoto.rev;
  }

  $("#proc").textContent = `Fuente: ${data.fuente} · Actualizado ${data.generado || "sin fecha"}`;
  renderOfficialFacts(data.obra);
}

function renderOfficialFacts(project) {
  const fields = [
    ["Ubicación", project.ubicacion],
    ["Institución ejecutora", project.institucion_ejecutora],
    ["Monto", project.monto_colones == null
      ? null
      : new Intl.NumberFormat("es-CR", { style: "currency", currency: "CRC" }).format(project.monto_colones)],
    ["Avance previsto", project.avance_previsto_pct == null ? null : `${project.avance_previsto_pct}%`],
    ["Avance observado", project.avance_observado_pct == null ? null : `${project.avance_observado_pct}%`],
  ];
  const list = $("#officialFacts");
  list.replaceChildren();

  for (const [label, value] of fields) {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value ?? "Dato no disponible";
    item.append(term, description);
    list.append(item);
  }
}

function renderMonths() {
  const container = $("#monthCoverage");
  const counts = new Map();
  for (const photo of photos) {
    const month = photo.f.slice(0, 7);
    counts.set(month, (counts.get(month) || 0) + 1);
  }
  const maxCount = Math.max(1, ...counts.values());
  container.replaceChildren();

  const addMonthButton = (month, label, count) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "month-select";
    button.setAttribute("aria-pressed", String(selectedMonth === month));
    button.dataset.month = month;

    const name = document.createElement("span");
    name.textContent = label;
    const bar = document.createElement("i");
    bar.style.setProperty("--month-fill", `${(count / maxCount) * 100}%`);
    const quantity = document.createElement("b");
    quantity.textContent = count.toLocaleString("es-CR");
    button.append(name, bar, quantity);
    button.addEventListener("click", () => {
      selectedMonth = month;
      visiblePhotos = galleryPageSize;
      renderMonths();
      renderGallery();
    });
    container.append(button);
  };

  addMonthButton("", "Todo el periodo", photos.length);
  for (const [month, count] of [...counts].sort(([a], [b]) => a.localeCompare(b))) {
    const label = new Date(`${month}-01T12:00:00`).toLocaleDateString("es-CR", {
      month: "long",
      year: "numeric",
    });
    addMonthButton(month, label, count);
  }
}

function filteredPhotos() {
  const query = $("#searchPhotos").value.trim().toLocaleLowerCase("es");
  const reviewOnly = $("#reviewOnly").checked;

  return photos.filter((photo) => {
    const matchesText = !query || `${photo.n} ${photo.f} ${photo.h}`.toLocaleLowerCase("es").includes(query);
    const matchesMonth = !selectedMonth || photo.f.startsWith(selectedMonth);
    return matchesText && matchesMonth && (!reviewOnly || photo.rev);
  });
}

function makeGalleryItem(photo) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `photo-item${photo.rev ? " needs-review" : ""}`;
  button.setAttribute("aria-label", `Ver fotografía ${photo.n}, ${formatDateTime(photo)}${photo.rev ? ", requiere revisión" : ""}`);
  const image = document.createElement("img");
  image.src = photo.p;
  image.alt = "";
  image.loading = "lazy";
  image.onerror = () => {
    image.alt = "Imagen no disponible";
    image.classList.add("image-missing");
  };

  const index = document.createElement("span");
  index.className = "photo-index";
  index.textContent = formatDate(photo.f, { day: "2-digit", month: "short" });
  const details = document.createElement("span");
  details.className = "photo-details";
  const time = document.createElement("b");
  time.textContent = photo.h || "Hora no disponible";
  const file = document.createElement("span");
  file.textContent = photo.n;
  details.append(time, file);
  button.append(image, index, details);
  button.addEventListener("click", () => openDialog(photo));
  return button;
}

function renderGallery() {
  const matching = filteredPhotos();
  const gallery = $("#gallery");
  const shown = matching.slice(0, visiblePhotos);
  gallery.replaceChildren(...shown.map(makeGalleryItem));
  $("#galleryCount").textContent = `${matching.length} ${matching.length === 1 ? "foto" : "fotos"}`;
  $("#emptyState").hidden = matching.length > 0;
  $("#loadMorePhotos").hidden = matching.length <= visiblePhotos;
}

function updateComparison(index, pause = true) {
  if (!photos.length) return;
  if (pause) stopPlayback();
  comparisonIndex = Math.max(0, Math.min(index, photos.length - 1));
  const selected = photos[comparisonIndex];
  const first = referencePhoto;

  $("#img0").src = first.p;
  $("#img1").src = selected.p;
  $("#img0").alt = `Fotografía de referencia del ${formatDateTime(first)}.`;
  $("#img1").alt = `Fotografía del ${formatDateTime(selected)}.`;
  $("#cap0").textContent = formatDate(first.f);
  $("#cap1").textContent = formatDate(selected.f);
  $("#timelineDate").textContent = formatDateTime(selected);
  $("#dayCounter").textContent = `${dayDifference(first.f, selected.f)} DÍAS`;
  $("#aviso").textContent = selected.rev
    ? "Alerta de encuadre: esta foto se conserva, pero requiere revisión."
    : "Comparación visual solamente; no representa porcentaje de avance.";
  $("#aviso").classList.toggle("review-warning", selected.rev);
  slider.value = String(comparisonIndex);
}

function stopPlayback() {
  if (playbackTimer !== null) {
    window.clearInterval(playbackTimer);
    playbackTimer = null;
  }
  $("#playPhotos").textContent = "▶ Recorrer la secuencia";
  $("#playPhotos").setAttribute("aria-pressed", "false");
}

function togglePlayback() {
  if (playbackTimer !== null) {
    stopPlayback();
    return;
  }
  if (comparisonIndex >= photos.length - 1) updateComparison(0);
  $("#playPhotos").textContent = "Ⅱ Pausar recorrido";
  $("#playPhotos").setAttribute("aria-pressed", "true");
  playbackTimer = window.setInterval(() => {
    if (comparisonIndex >= photos.length - 1) {
      stopPlayback();
      return;
    }
    updateComparison(comparisonIndex + 1, false);
  }, 1100);
}

function openDialog(photo) {
  dialogIndex = photos.findIndex((item) => item.id === photo.id);
  if (dialogIndex < 0) return;
  renderDialogPhoto();
  dialog.showModal();
}

function renderDialogPhoto() {
  const photo = photos[dialogIndex];
  if (!photo) return;
  $("#dialogTitle").textContent = formatDateTime(photo);
  $("#dialogImage").src = photo.p;
  $("#dialogImage").alt = `Fotografía ${photo.n}`;
  $("#dialogInfo").textContent = `${photo.n}${photo.b == null ? "" : ` · Brillo medio ${photo.b}`}${photo.rev ? " · Revisión de encuadre pendiente" : ""}`;
}

function moveDialog(direction) {
  if (!photos.length) return;
  dialogIndex = (dialogIndex + direction + photos.length) % photos.length;
  renderDialogPhoto();
}

function setupInteractions() {
  slider.addEventListener("input", () => updateComparison(Number(slider.value)));
  $("#prevPhoto").addEventListener("click", () => updateComparison(comparisonIndex - 1));
  $("#nextPhoto").addEventListener("click", () => updateComparison(comparisonIndex + 1));
  $("#playPhotos").addEventListener("click", togglePlayback);
  $("#searchPhotos").addEventListener("input", () => {
    visiblePhotos = galleryPageSize;
    renderGallery();
  });
  $("#reviewOnly").addEventListener("change", () => {
    visiblePhotos = galleryPageSize;
    renderGallery();
  });
  $("#clearFilters").addEventListener("click", () => {
    $("#searchPhotos").value = "";
    $("#reviewOnly").checked = false;
    selectedMonth = "";
    visiblePhotos = galleryPageSize;
    renderMonths();
    renderGallery();
  });
  $("#loadMorePhotos").addEventListener("click", () => {
    visiblePhotos += galleryPageSize;
    renderGallery();
  });
  $("#closeDialog").addEventListener("click", () => dialog.close());
  $("#dialogPrev").addEventListener("click", () => moveDialog(-1));
  $("#dialogNext").addEventListener("click", () => moveDialog(1));
  $("#dialogCompare").addEventListener("click", () => {
    const photo = photos[dialogIndex];
    const index = photos.findIndex((item) => item.id === photo.id);
    dialog.close();
    updateComparison(index);
    $("#archivo").scrollIntoView({ behavior: "smooth" });
  });
}

async function start() {
  try {
    const response = await fetch(dashboardUrl, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || `La API respondió ${response.status}.`);
    }
    const data = await response.json();
    if (!Array.isArray(data.fotos) || !data.estadisticas || !data.obra) {
      throw new Error("La API devolvió un formato de datos inesperado.");
    }

    allPhotos = data.fotos;
    photos = allPhotos
      .filter((photo) => photo.d === "CONSERVADA" && photo.p && photo.f)
      .sort((a, b) => a.f.localeCompare(b.f) || a.h.localeCompare(b.h) || a.id - b.id);
    if (!photos.length) throw new Error("La API no tiene fotografías disponibles para mostrar.");

    referencePhoto = photos.find((photo) => !photo.rev) || photos[0];
    comparisonIndex = photos.indexOf(referencePhoto);
    slider.max = String(photos.length - 1);
    slider.value = String(comparisonIndex);
    renderProject(data);
    renderMonths();
    renderGallery();
    updateComparison(comparisonIndex, false);
    setApiStatus(true, "API conectada");
  } catch (error) {
    setApiStatus(false, "API desconectada");
    $("#dataError").textContent = `No se pudieron cargar los datos: ${error.message} Inicia el servidor del proyecto y vuelve a cargar la página.`;
    $("#dataError").hidden = false;
    $("#galleryCount").textContent = "Sin datos";
  }
}

setupInteractions();
start();
