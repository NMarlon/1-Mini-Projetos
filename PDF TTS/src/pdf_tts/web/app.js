const $ = (id) => document.getElementById(id);

const state = {
  uploadId: null,
  discovery: null,
  totalPages: 0,
  jobId: null,
  timer: null,
  defaultVoice: "pt-BR-FranciscaNeural",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let data = {};
  try { data = await response.json(); } catch (_) { /* resposta vazia */ }
  if (!response.ok) {
    throw new Error(data.detail || `Erro HTTP ${response.status}`);
  }
  return data;
}

function showBanner(container, text, type = "warn") {
  const div = document.createElement("div");
  div.className = type;
  div.textContent = text;
  container.appendChild(div);
}

function clearBanners(container) {
  container.innerHTML = "";
}

function stageLabel(stage) {
  const labels = {
    "na fila": "Na fila",
    "iniciando": "Iniciando",
    "analisando": "Analisando PDF",
    "extraindo": "Extraindo texto",
    "segmentando": "Dividindo capítulos",
    "preparando": "Preparando síntese",
    "sintetizando": "Gerando narração",
    "montando": "Montando áudio",
    "verificando": "Verificando",
    "concluído": "Concluído",
    "erro": "Erro",
  };
  return labels[stage] || stage || "—";
}

function humanDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h ? `${h}h${String(m).padStart(2, "0")}` : `${m}min${String(s).padStart(2, "0")}`;
}

async function loadHealth() {
  const chip = $("health");
  try {
    await api("/api/health");
    chip.textContent = "pronto";
    chip.className = "status-chip ok";
  } catch (error) {
    chip.textContent = "servidor indisponível";
    chip.className = "status-chip bad";
  }
}

async function loadDefaults() {
  try {
    const defaults = await api("/api/defaults");
    state.defaultVoice = defaults.voice || state.defaultVoice;
    const rate = $("rate");
    if ([...rate.options].some((option) => option.value === defaults.rate)) {
      rate.value = defaults.rate;
    }
  } catch (_) { /* usa os padrões do HTML */ }
}

async function loadVoices() {
  const select = $("voice");
  try {
    const data = await api("/api/voices");
    const voices = data.voices || [];
    if (!voices.length) return;
    select.innerHTML = "";
    for (const voice of voices) {
      const option = document.createElement("option");
      option.value = voice.name;
      option.textContent = `${voice.name.replace("pt-BR-", "").replace("Neural", "")} (${voice.gender === "Female" ? "feminina" : "masculina"})`;
      select.appendChild(option);
    }
    if (voices.some((voice) => voice.name === state.defaultVoice)) {
      select.value = state.defaultVoice;
    }
  } catch (_) {
    // Mantém as opções padrão do HTML.
  }
}

function resetToUpload() {
  if (state.timer) clearInterval(state.timer);
  state.uploadId = null;
  state.discovery = null;
  state.jobId = null;
  $("analysisCard").hidden = true;
  $("progressCard").hidden = true;
  $("result").hidden = true;
  $("dropzone").hidden = false;
  $("fileInput").value = "";
}

async function analyzeFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    alert("Escolha um arquivo PDF.");
    return;
  }
  const drop = $("dropzone");
  const title = drop.querySelector("h2");
  const oldTitle = title.textContent;
  title.innerHTML = '<span class="spinner"></span> Analisando PDF…';
  drop.classList.add("drag");
  try {
    const form = new FormData();
    form.append("file", file);
    form.append("chapter_mode", "auto");
    form.append("chapter_size", "10");
    const data = await api("/api/analyze", { method: "POST", body: form });
    state.uploadId = data.upload_id;
    state.discovery = data.discovery;
    state.totalPages = data.discovery.total_pages;
    renderAnalysis(data.filename, data.discovery);
    drop.hidden = true;
  } catch (error) {
    alert(error.message);
  } finally {
    title.textContent = oldTitle;
    drop.classList.remove("drag");
  }
}

function renderAnalysis(filename, discovery) {
  $("fileName").textContent = filename;
  $("fileMeta").textContent = `${discovery.total_pages} páginas · ${discovery.text_pages} com texto · detecção: ${discovery.structure}`;
  const warnings = $("warnings");
  clearBanners(warnings);
  for (const warning of discovery.warnings || []) showBanner(warnings, warning, "warn");
  if (discovery.text_pages === 0) {
    showBanner(warnings, "Este PDF não tem texto extraível. A v1 não consegue narrar PDFs escaneados.", "error");
    $("generate").disabled = true;
  } else {
    $("generate").disabled = false;
  }
  $("chapterMode").value = "auto";
  $("contentMode").value = "auto";
  populateChapters(discovery.chapters, true);
  $("addChapter").hidden = true;
  $("estimate").textContent = "A duração real aparece no resultado.";
  $("analysisCard").hidden = false;
  $("analysisCard").scrollIntoView({ behavior: "smooth", block: "start" });
}

function populateChapters(chapters, readOnly) {
  const body = $("chapterRows");
  body.innerHTML = "";
  for (const chapter of chapters || []) {
    addChapterRow(chapter.title, chapter.start_page, chapter.end_page, readOnly);
  }
  if (!body.children.length) {
    addChapterRow("Livro completo", 1, state.totalPages, readOnly);
  }
}

function addChapterRow(title, start, end, readOnly) {
  const body = $("chapterRows");
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="text" class="ch-title" value="${escapeHtml(title)}" ${readOnly ? "readonly" : ""}></td>
    <td><input type="number" class="ch-start" min="1" max="${state.totalPages}" value="${start}" ${readOnly ? "readonly" : ""}></td>
    <td><input type="number" class="ch-end" min="1" max="${state.totalPages}" value="${end}" ${readOnly ? "readonly" : ""}></td>
    <td>${readOnly ? "" : '<button class="danger-link ch-remove">remover</button>'}</td>
  `;
  const remove = tr.querySelector(".ch-remove");
  if (remove) {
    remove.addEventListener("click", () => {
      if (body.children.length <= 1) return;
      tr.remove();
    });
  }
  body.appendChild(tr);
}

function setChapterEditing(editable) {
  for (const input of $("chapterRows").querySelectorAll("input")) {
    input.readOnly = !editable;
  }
  for (const button of $("chapterRows").querySelectorAll(".ch-remove")) {
    button.style.display = editable ? "" : "none";
  }
  $("addChapter").hidden = !editable;
}

function onChapterModeChange() {
  const mode = $("chapterMode").value;
  if (mode === "none") {
    populateChapters([{ title: "Livro completo", start_page: 1, end_page: state.totalPages }], true);
    $("chapterHint").textContent = "O PDF inteiro será um único audiolivro.";
    setChapterEditing(false);
  } else if (mode === "manual") {
    $("chapterHint").textContent = "Ajuste títulos e páginas. Os intervalos devem ser contínuos, de 1 até a última página.";
    if (!$("chapterRows").children.length || $("chapterRows").querySelector(".ch-title")?.value === "Livro completo") {
      populateChapters([{ title: "Parte 01", start_page: 1, end_page: state.totalPages }], false);
    }
    setChapterEditing(true);
  } else {
    $("chapterHint").textContent = "Detectados automaticamente. Para editar, escolha “Editar capítulos”.";
    populateChapters(state.discovery?.chapters || [], true);
    setChapterEditing(false);
  }
}

function collectChapters() {
  const rows = [];
  for (const tr of $("chapterRows").querySelectorAll("tr")) {
    const title = tr.querySelector(".ch-title")?.value.trim() || "";
    const start = Number(tr.querySelector(".ch-start")?.value);
    const end = Number(tr.querySelector(".ch-end")?.value);
    if (!title || !Number.isFinite(start) || !Number.isFinite(end)) {
      throw new Error("Preencha título, página inicial e página final de todos os capítulos.");
    }
    rows.push({ title, start_page: start, end_page: end });
  }
  rows.sort((a, b) => a.start_page - b.start_page);
  if (!rows.length) throw new Error("Adicione pelo menos um capítulo.");
  if (rows[0].start_page !== 1) throw new Error("O primeiro capítulo deve começar na página 1.");
  if (rows[rows.length - 1].end_page !== state.totalPages) {
    throw new Error(`O último capítulo deve terminar na página ${state.totalPages}.`);
  }
  for (let index = 0; index < rows.length; index += 1) {
    if (rows[index].end_page < rows[index].start_page) {
      throw new Error(`Capítulo inválido: ${rows[index].title}.`);
    }
    if (index + 1 < rows.length && rows[index + 1].start_page !== rows[index].end_page + 1) {
      throw new Error("Os capítulos devem ser contínuos, sem lacunas ou sobreposição.");
    }
  }
  return rows;
}

async function generate() {
  if (!state.uploadId) return;
  let chapters = null;
  const chapterMode = $("chapterMode").value;
  if (chapterMode === "manual") {
    try {
      chapters = collectChapters();
    } catch (error) {
      alert(error.message);
      return;
    }
  }
  $("generate").disabled = true;
  $("progressCard").hidden = false;
  $("result").hidden = true;
  $("progressTitle").textContent = "Preparando…";
  $("progressMessage").textContent = "Enviando o trabalho para a fila.";
  $("progressStage").textContent = "Na fila";
  $("progressBar").style.width = "0%";
  $("progressBar").classList.remove("indeterminate");
  $("progressCount").textContent = "";
  $("progressPercent").textContent = "";
  try {
    const data = await api("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_id: state.uploadId,
        chapter_mode: chapterMode,
        chapter_size: 10,
        chapters,
        content_mode: $("contentMode").value,
        voice: $("voice").value,
        rate: $("rate").value,
      }),
    });
    state.jobId = data.job_id;
    startPolling();
  } catch (error) {
    $("generate").disabled = false;
    $("progressMessage").textContent = error.message;
    $("progressStage").textContent = "Erro";
  }
}

function startPolling() {
  if (state.timer) clearInterval(state.timer);
  state.timer = setInterval(pollJob, 1000);
  pollJob();
}

async function pollJob() {
  if (!state.jobId) return;
  try {
    const job = await api(`/api/jobs/${state.jobId}`);
    $("progressTitle").textContent = job.title || "Convertendo…";
    $("progressMessage").textContent = job.message || "";
    $("progressStage").textContent = stageLabel(job.stage);
    const total = Number(job.total || 0);
    const current = Number(job.current || 0);
    if (total > 0) {
      const percent = Math.max(0, Math.min(100, Math.round((current / total) * 100)));
      $("progressBar").classList.remove("indeterminate");
      $("progressBar").style.width = `${percent}%`;
      $("progressCount").textContent = `${current} de ${total}`;
      $("progressPercent").textContent = `${percent}%`;
    } else {
      $("progressBar").classList.add("indeterminate");
      $("progressCount").textContent = "";
      $("progressPercent").textContent = "";
    }
    if (job.status === "done") {
      clearInterval(state.timer);
      state.timer = null;
      $("progressTitle").textContent = "Áudios prontos!";
      $("progressMessage").textContent = "Você já pode ouvir ou abrir a pasta.";
      $("progressStage").textContent = "Concluído";
      $("progressBar").classList.remove("indeterminate");
      $("progressBar").style.width = "100%";
      renderResult(job);
      $("generate").disabled = false;
    } else if (job.status === "error" || job.status === "interrupted") {
      clearInterval(state.timer);
      state.timer = null;
      $("progressTitle").textContent = job.status === "interrupted" ? "Interrompido" : "Não foi possível gerar";
      $("progressMessage").textContent = job.message || job.error || "Veja o log.";
      $("progressStage").textContent = "Erro";
      $("progressBar").classList.remove("indeterminate");
      $("progressBar").style.width = "0%";
      $("generate").disabled = false;
    }
  } catch (error) {
    $("progressMessage").textContent = error.message;
  }
}

function renderResult(job) {
  $("result").hidden = false;
  const coverage = job.coverage || {};
  const summary = $("resultSummary");
  summary.innerHTML = "";
  const lines = [];
  if (coverage.pages_total) {
    lines.push(`Páginas: ${coverage.pages_narrated}/${coverage.pages_with_text} com texto narradas.`);
  }
  if (coverage.chapters) lines.push(`${coverage.chapters.length} capítulos.`);
  if (coverage.pages_without_audio?.length) {
    lines.push(`Páginas com texto sem áudio: ${coverage.pages_without_audio.join(", ")}.`);
  }
  if (coverage.image_only_pages?.length) {
    lines.push(`Páginas só de imagem (não narradas): ${coverage.image_only_pages.join(", ")}.`);
  }
  for (const line of lines) {
    const p = document.createElement("p");
    p.textContent = line;
    summary.appendChild(p);
  }
  for (const warning of coverage.warnings || []) showBanner(summary, warning, "warn");
  const list = $("resultFiles");
  list.innerHTML = "";
  for (const file of job.files || []) {
    const li = document.createElement("li");
    li.textContent = file;
    list.appendChild(li);
  }
  $("openFolder").onclick = async () => {
    try {
      await api("/api/open-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: state.jobId }),
      });
    } catch (error) {
      alert(error.message);
    }
  };
}

function setupDropzone() {
  const drop = $("dropzone");
  const input = $("fileInput");
  $("chooseFile").addEventListener("click", () => input.click());
  input.addEventListener("change", () => analyzeFile(input.files?.[0]));
  drop.addEventListener("click", (event) => {
    if (event.target === drop || event.target.classList.contains("drop-icon")) input.click();
  });
  for (const eventName of ["dragenter", "dragover"]) {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.add("drag");
    });
  }
  for (const eventName of ["dragleave", "drop"]) {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.remove("drag");
    });
  }
  drop.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (file) analyzeFile(file);
  });
}

function init() {
  loadHealth();
  loadDefaults();
  loadVoices();
  setupDropzone();
  $("restart").addEventListener("click", resetToUpload);
  $("chapterMode").addEventListener("change", onChapterModeChange);
  $("addChapter").addEventListener("click", () => {
    const rows = $("chapterRows");
    const last = rows.querySelector("tr:last-child");
    const start = Number(last?.querySelector(".ch-end")?.value || 0) + 1;
    addChapterRow(`Parte ${rows.children.length + 1}`, Math.max(1, start), state.totalPages, false);
  });
  $("generate").addEventListener("click", generate);
}

document.addEventListener("DOMContentLoaded", init);
