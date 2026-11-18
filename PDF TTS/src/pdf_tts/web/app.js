const $ = (id) => document.getElementById(id);

const RECIPES = {
  auto: { content: "auto", chapters: "auto", label: "Automático" },
  review: { content: "auto", chapters: "manual", label: "Identificar capítulos" },
  all: { content: "all", chapters: "auto", label: "Tudo útil" },
  raw: { content: "raw", chapters: "auto", label: "Tudo literal" },
};

const PROFILE_LABELS = {
  pathway: "Pathway (Semanas/S01–S07)",
  outline: "índice do PDF",
  generic: "genérico (títulos)",
  fallback: "blocos de páginas",
  manual: "manual",
  none: "livro inteiro",
};

const STRUCTURE_LABELS = {
  pathway: "Pathway",
  outline: "índice do PDF",
  headings: "títulos do PDF",
  fallback: "blocos de páginas",
  manual: "manual",
  none: "livro inteiro",
};

const state = {
  uploadId: null,
  discovery: null,
  totalPages: 0,
  jobId: null,
  timer: null,
  healthTimer: null,
  healthChecking: false,
  healthOk: true,
  defaultVoice: "pt-BR-FranciscaNeural",
  profile: "auto",
  analyzing: false,
  uploading: false,
};

class ConnectionError extends Error {
  constructor() {
    super("O programa não está respondendo. Mantenha a janelinha do Pathway PDF TTS aberta ou abra o programa novamente.");
    this.name = "ConnectionError";
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (_) {
    throw new ConnectionError();
  }
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (_) {
      data = {};
    }
  }
  if (!response.ok) {
    const detail = data.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg || JSON.stringify(item)).join("; "));
    }
    throw new Error(detail || `Erro HTTP ${response.status}`);
  }
  return data;
}

function showBanner(container, text, type = "warn") {
  if (!container) return;
  const div = document.createElement("div");
  div.className = type;
  div.textContent = text;
  container.appendChild(div);
}

function clearBanners(container) {
  if (container) container.innerHTML = "";
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

function currentRecipe() {
  return document.querySelector('input[name="recipe"]:checked')?.value || "auto";
}

function recipeContentMode() {
  return RECIPES[currentRecipe()]?.content || "auto";
}

function setConnectionState(ok) {
  state.healthOk = ok;
  const chip = $("health");
  const banner = $("connectionBanner");
  if (ok) {
    chip.textContent = "pronto";
    chip.className = "status-chip ok";
    banner.hidden = true;
  } else {
    chip.textContent = "sem conexão";
    chip.className = "status-chip bad";
    banner.hidden = false;
  }
  updateGenerateState();
}

function updateGenerateState() {
  const button = $("generate");
  if (!button) return;
  const hasText = Boolean(state.discovery && state.discovery.text_pages > 0);
  button.disabled = !hasText || !state.healthOk || state.uploading || state.analyzing;
}

async function checkHealth() {
  if (state.healthChecking) return state.healthOk;
  state.healthChecking = true;
  try {
    await api("/api/health");
    setConnectionState(true);
    return true;
  } catch (_) {
    setConnectionState(false);
    return false;
  } finally {
    state.healthChecking = false;
  }
}

function loadHealth() {
  return checkHealth();
}

async function loadDefaults() {
  try {
    const defaults = await api("/api/defaults");
    state.defaultVoice = defaults.voice || state.defaultVoice;
    const rate = $("rate");
    if ([...rate.options].some((option) => option.value === defaults.rate)) {
      rate.value = defaults.rate;
    }
    if (defaults.profile) {
      $("profile").value = defaults.profile;
      state.profile = defaults.profile;
    }
  } catch (_) {
    // Usa os padrões do HTML.
  }
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
  state.totalPages = 0;
  state.jobId = null;
  state.analyzing = false;
  state.uploading = false;
  $("analysisCard").hidden = true;
  $("progressCard").hidden = true;
  $("result").hidden = true;
  $("dropzone").hidden = false;
  $("fileInput").value = "";
  $("uploadProgress").textContent = "";
  $("uploadProgress").className = "hint";
  clearBanners($("uploadError"));
  updateGenerateState();
}

function uploadPdf(form, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/analyze");
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded, event.total);
    };
    xhr.onload = () => {
      const data = xhr.response || {};
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
        return;
      }
      const detail = data.detail;
      reject(new Error(Array.isArray(detail) ? detail.map((item) => item.msg || JSON.stringify(item)).join("; ") : (detail || `Erro HTTP ${xhr.status}`)));
    };
    xhr.onerror = () => reject(new ConnectionError());
    xhr.ontimeout = () => reject(new ConnectionError());
    xhr.send(form);
  });
}

async function analyzeFile(file) {
  if (!file || state.uploading || state.analyzing) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    alert("Escolha um arquivo PDF.");
    return;
  }
  state.uploading = true;
  state.analyzing = false;
  clearBanners($("uploadError"));
  const drop = $("dropzone");
  const title = drop.querySelector("h2");
  const oldTitle = title.textContent;
  const progress = $("uploadProgress");
  progress.className = "hint";
  progress.textContent = "Preparando o envio…";
  drop.classList.add("drag");
  updateGenerateState();

  let phase = "upload";
  const started = Date.now();
  const ticker = setInterval(() => {
    if (phase === "analysis") {
      const seconds = Math.round((Date.now() - started) / 1000);
      title.innerHTML = `<span class="spinner"></span> Analisando o PDF… ${seconds}s`;
      progress.textContent = "O envio terminou. Agora o app está lendo as páginas e procurando os capítulos.";
    }
  }, 1000);

  try {
    const form = new FormData();
    form.append("file", file);
    form.append("chapter_mode", "auto");
    form.append("chapter_size", "10");
    form.append("profile", $("profile").value);
    const data = await uploadPdf(form, (loaded, total) => {
      const percent = total ? Math.round((loaded / total) * 100) : 0;
      const mb = (loaded / (1024 * 1024)).toFixed(1);
      const totalMb = (total / (1024 * 1024)).toFixed(1);
      title.innerHTML = `<span class="spinner"></span> Enviando o PDF… ${percent}%`;
      progress.textContent = `${mb} MB de ${totalMb} MB enviados.`;
    });
    phase = "analysis";
    state.uploadId = data.upload_id;
    state.discovery = data.discovery;
    state.totalPages = data.discovery.total_pages;
    renderAnalysis(data.filename, data.discovery);
    drop.hidden = true;
    progress.textContent = "";
  } catch (error) {
    if (error instanceof ConnectionError) {
      setConnectionState(false);
    } else {
      showBanner($("uploadError"), error.message, "error");
    }
    progress.className = "hint error-text";
    progress.textContent = error.message;
  } finally {
    clearInterval(ticker);
    state.uploading = false;
    state.analyzing = false;
    title.textContent = oldTitle;
    drop.classList.remove("drag");
    updateGenerateState();
  }
}

function describeDetection(discovery) {
  const used = discovery.profile_used || discovery.structure || "generic";
  const label = PROFILE_LABELS[used] || used;
  const structure = STRUCTURE_LABELS[discovery.structure] || discovery.structure;
  const count = discovery.chapters?.length || 0;
  if (used === "pathway") {
    return `Perfil Pathway: ${count} capítulos detectados por Semanas/S01–S07.`;
  }
  if (used === "outline") {
    return `Detecção pelo índice do PDF: ${count} capítulos.`;
  }
  if (used === "generic") {
    return `Detecção genérica por títulos (${structure}): ${count} capítulos.`;
  }
  if (used === "fallback") {
    return `Não encontrei títulos de capítulo. O PDF foi dividido em ${count} blocos de páginas.`;
  }
  if (used === "manual" || used === "none") {
    return `Conversão manual: ${count} capítulo(s).`;
  }
  return `Detecção: ${label} (${structure}); ${count} capítulos.`;
}

function renderAnalysis(filename, discovery) {
  $("fileName").textContent = filename;
  const used = discovery.profile_used || discovery.structure || "generic";
  const label = PROFILE_LABELS[used] || used;
  $("fileMeta").textContent = `${discovery.total_pages} páginas · ${discovery.text_pages} com texto · ${discovery.chapters.length} capítulos · perfil: ${label}`;
  $("detectionInfo").textContent = describeDetection(discovery);

  const warnings = $("warnings");
  clearBanners(warnings);
  for (const warning of discovery.warnings || []) showBanner(warnings, warning, "warn");
  if (discovery.text_pages === 0) {
    showBanner(warnings, "Este PDF não tem texto extraível. A versão atual não narra PDFs escaneados.", "error");
  }

  state.discovery = discovery;
  state.totalPages = discovery.total_pages;
  populateChapters(discovery.chapters, true);
  applyChapterMode();
  $("analysisCard").hidden = false;
  $("analysisCard").scrollIntoView({ behavior: "smooth", block: "start" });
  updateGenerateState();
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

function looksLikeSingleBookRow() {
  const rows = $("chapterRows").querySelectorAll("tr");
  return rows.length === 1 && rows[0].querySelector(".ch-title")?.value === "Livro completo";
}

function applyChapterMode() {
  const mode = $("chapterMode").value;
  if (mode === "none") {
    populateChapters([{ title: "Livro completo", start_page: 1, end_page: state.totalPages }], true);
    $("chapterHint").textContent = "O PDF inteiro será um único audiolivro.";
    setChapterEditing(false);
  } else if (mode === "manual") {
    $("chapterHint").textContent = "Ajuste títulos e páginas. Os intervalos devem ser contínuos, de 1 até a última página.";
    if (!state.discovery || looksLikeSingleBookRow()) {
      populateChapters(state.discovery?.chapters || [{ title: "Parte 01", start_page: 1, end_page: state.totalPages }], false);
    } else {
      setChapterEditing(true);
    }
    setChapterEditing(true);
  } else {
    $("chapterHint").textContent = "Detectados automaticamente. Para editar, escolha “Editar capítulos” ou o modo “Identificar capítulos”.";
    populateChapters(state.discovery?.chapters || [], true);
    setChapterEditing(false);
  }
}

function applyRecipe() {
  const recipe = currentRecipe();
  const config = RECIPES[recipe] || RECIPES.auto;
  for (const card of document.querySelectorAll(".mode-card")) {
    const input = card.querySelector("input");
    card.classList.toggle("selected", input.checked);
  }
  $("chapterMode").value = config.chapters;
  if (state.discovery) applyChapterMode();
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
        content_mode: recipeContentMode(),
        profile: $("profile").value,
        voice: $("voice").value,
        rate: $("rate").value,
      }),
    });
    state.jobId = data.job_id;
    startPolling();
  } catch (error) {
    if (error instanceof ConnectionError) setConnectionState(false);
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
      $("progressMessage").textContent = job.message || job.error || "Veja o log em logs/app.log.";
      $("progressStage").textContent = "Erro";
      $("progressBar").classList.remove("indeterminate");
      $("progressBar").style.width = "0%";
      $("generate").disabled = false;
    }
  } catch (error) {
    if (error instanceof ConnectionError) {
      setConnectionState(false);
      $("progressMessage").textContent = "Conexão com o programa perdida. Mantenha a janelinha aberta e aguarde ou clique em Tentar novamente.";
    } else {
      $("progressMessage").textContent = error.message;
    }
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
      if (error instanceof ConnectionError) setConnectionState(false);
      alert(error.message);
    }
  };
}

async function reanalyze() {
  if (!state.uploadId || state.analyzing) return;
  const newProfile = $("profile").value;
  if ($("chapterMode").value === "manual" && !confirm("Trocar o perfil refaz a detecção e perde as edições manuais dos capítulos. Continuar?")) {
    $("profile").value = state.profile;
    return;
  }
  const oldProfile = state.profile;
  state.profile = newProfile;
  state.analyzing = true;
  updateGenerateState();
  $("reanalyze").disabled = true;
  $("detectionInfo").textContent = "Reanalisando o PDF com o novo perfil…";
  try {
    const data = await api("/api/reanalyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_id: state.uploadId, profile: newProfile }),
    });
    state.discovery = data.discovery;
    state.totalPages = data.discovery.total_pages;
    renderAnalysis(data.filename, data.discovery);
  } catch (error) {
    state.profile = oldProfile;
    $("profile").value = oldProfile;
    if (error instanceof ConnectionError) setConnectionState(false);
    if (state.discovery) $("detectionInfo").textContent = describeDetection(state.discovery);
    clearBanners($("warnings"));
    showBanner($("warnings"), error.message, "error");
  } finally {
    state.analyzing = false;
    $("reanalyze").disabled = false;
    updateGenerateState();
  }
}

function onProfileChange() {
  const value = $("profile").value;
  if (!state.uploadId) {
    state.profile = value;
    return;
  }
  reanalyze();
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
  setConnectionState(true);
  $("restart").addEventListener("click", resetToUpload);
  $("reanalyze").addEventListener("click", reanalyze);
  $("profile").addEventListener("change", onProfileChange);
  $("chapterMode").addEventListener("change", applyChapterMode);
  $("addChapter").addEventListener("click", () => {
    const rows = $("chapterRows");
    const last = rows.querySelector("tr:last-child");
    const start = Number(last?.querySelector(".ch-end")?.value || 0) + 1;
    addChapterRow(`Parte ${rows.children.length + 1}`, Math.max(1, start), state.totalPages, false);
  });
  for (const radio of document.querySelectorAll('input[name="recipe"]')) {
    radio.addEventListener("change", applyRecipe);
  }
  $("retryConnection").addEventListener("click", async () => {
    const ok = await checkHealth();
    if (ok && state.jobId) pollJob();
  });
  $("generate").addEventListener("click", generate);
  applyRecipe();
  state.healthTimer = setInterval(checkHealth, 5000);
}

document.addEventListener("DOMContentLoaded", init);
