// Terabox Auto-Backuper - Frontend

const API = '/api';

// Seleção de mapeamentos (backup) e de arquivos (restauração)
let mappingsCache = [];
let mappingSelectionBusy = 0;

const RESTORE_SELECTION_KEY_V1 = 'terabox_restore_selected_v1';
const RESTORE_SELECTION_KEY = 'terabox_restore_selected_v2';
const RESTORE_SAVE_DELAY_MS = 250;
let restoreFilesCache = [];
let restoreTree = null;
let restoreSelection = new Set();
let restoreSelectionDirty = false;
let restoreSaveTimer = null;
let restoreDirNodes = new Map();
let restoreConfirmOverwrite = true;

// ── Navegação por abas ──
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});

// ── Auth ──
async function checkAuth() {
    try {
        const res = await fetch(API + '/auth/status');
        const data = await res.json();
        const statusEl = document.getElementById('auth-status');
        const btnConnect = document.getElementById('btn-connect');
        const btnDisconnect = document.getElementById('btn-disconnect');
        if (data.connecting) {
            statusEl.textContent = '⏳ Conectando... (o Dia pode estar reiniciando)';
            btnConnect.style.display = 'none';
            btnDisconnect.style.display = 'none';
            // Continua verificando até concluir
            setTimeout(checkAuth, 2000);
        } else if (data.authenticated) {
            statusEl.textContent = `✅ Conectado via ${data.browser} (${data.cookies_found} cookies)`;
            btnConnect.style.display = 'none';
            btnDisconnect.style.display = 'inline-block';
        } else {
            const err = data.error ? ` — ${data.error}` : '';
            statusEl.textContent = '❌ Não conectado ao Terabox' + err;
            btnConnect.style.display = 'inline-block';
            btnDisconnect.style.display = 'none';
        }
    } catch (e) {
        document.getElementById('auth-status').textContent = '⚠️ Erro ao verificar auth';
    }
}

async function onBrowserChange() {
    const browser = document.getElementById('auth-browser').value;
    const profileLabel = document.getElementById('profile-label');
    const profileSelect = document.getElementById('auth-profile');
    if (browser === 'manual' || browser === 'auto') {
        profileLabel.style.display = 'none';
        return;
    }
    profileLabel.style.display = 'flex';
    profileSelect.innerHTML = '<option value="">Carregando...</option>';
    try {
        const res = await fetch(API + '/auth/profiles?browser=' + browser);
        const profiles = await res.json();
        profileSelect.innerHTML = '';
        if (profiles.length === 0) {
            if (browser === 'dia') {
                profileSelect.innerHTML = '<option value="">Dia não encontrado. Instale-o ou use outro navegador.</option>';
            } else {
                profileSelect.innerHTML = '<option value="">Nenhum perfil encontrado</option>';
            }
            return;
        }
        profiles.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name;
            let icon = ' ❔';
            if (p.has_terabox === true) icon = ' ✅';
            else if (p.has_terabox === false) icon = ' ❌';
            opt.textContent = p.name + icon + (p.is_default ? ' (padrão)' : '');
            profileSelect.appendChild(opt);
        });
        // Selecionar o primeiro com Terabox
        const withTb = profiles.find(p => p.has_terabox === true);
        if (withTb) {
            profileSelect.value = withTb.name;
        }
    } catch (e) {
        profileSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

async function connectAuth() {
    const browser = document.getElementById('auth-browser').value;
    if (browser === 'manual') {
        document.getElementById('manual-cookies').style.display = 'block';
        return;
    }
    document.getElementById('manual-cookies').style.display = 'none';
    const profile = document.getElementById('auth-profile').value || null;
    if (browser === 'dia') {
        const ok = confirm('Para ler os cookies do Dia, ele precisará ser FECHADO e reaberto automaticamente. Continuar?');
        if (!ok) return;
    }
    document.getElementById('auth-status').textContent = '⏳ Conectando em segundo plano... (o Dia pode ser reiniciado)';
    try {
        const res = await fetch(API + '/auth/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ browser, profile })
        });
        const data = await res.json();
        if (data.authenticated && !data.connecting) {
            alert('Conectado com sucesso!');
            checkAuth();
            return;
        }
        // A conexão roda em background no servidor: acompanhar o status.
        // Se a página for fechada (Dia reiniciado), ao reabrir o app o status já aparecerá.
        document.getElementById('auth-status').textContent = '⏳ Conectando... o Dia será reiniciado e reaberto automaticamente.';
        const started = Date.now();
        const timer = setInterval(async () => {
            try {
                const sres = await fetch(API + '/auth/status');
                const sdata = await sres.json();
                if (sdata.connecting) {
                    document.getElementById('auth-status').textContent = '⏳ Conectando... aguarde o Dia reabrir.';
                    return;
                }
                clearInterval(timer);
                if (sdata.authenticated) {
                    alert('Conectado com sucesso!');
                } else {
                    alert('Não foi possível conectar: ' + (sdata.error || 'erro desconhecido'));
                }
                checkAuth();
            } catch (e) {
                // Página pode ter sido fechada pelo reinício do Dia; ao reabrir, o status será atualizado.
            }
            if (Date.now() - started > 120000) {
                clearInterval(timer);
                checkAuth();
            }
        }, 1000);
    } catch (e) {
        // Se o Dia fechar a página no meio da requisição, não é erro real.
        console.warn('Requisição interrompida (provável reinício do Dia):', e.message);
    }
}

async function connectManual() {
    const cookies = document.getElementById('manual-cookies-input').value.trim();
    if (!cookies) {
        alert('Cole os cookies primeiro.');
        return;
    }
    document.getElementById('auth-status').textContent = '⏳ Conectando...';
    try {
        const res = await fetch(API + '/auth/connect-manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cookies })
        });
        const data = await res.json();
        if (data.authenticated) {
            alert('Conectado com sucesso!');
            document.getElementById('manual-cookies').style.display = 'none';
        } else {
            alert('Erro: ' + (data.error || 'Desconhecido'));
        }
        checkAuth();
    } catch (e) {
        alert('Erro de conexão: ' + e.message);
    }
}

async function disconnectAuth() {
    await fetch(API + '/auth/disconnect', { method: 'POST' });
    checkAuth();
}

// ── Mappings ──
async function loadMappings() {
    try {
        const res = await fetch(API + '/mappings');
        const data = await res.json();
        mappingsCache = Array.isArray(data) ? data : [];
        const list = document.getElementById('mappings-list');
        list.innerHTML = '';
        if (mappingsCache.length === 0) {
            list.innerHTML = '<p>Nenhum mapeamento configurado.</p>';
            updateMappingsCount();
            return;
        }
        mappingsCache.forEach(m => {
            const div = document.createElement('div');
            div.className = 'mapping-item' + (m.enabled ? '' : ' mapping-disabled');
            div.innerHTML = `
                <label class="mapping-select" title="Incluir este mapeamento no backup">
                    <input type="checkbox" class="mapping-enabled" data-id="${m.id}" ${m.enabled ? 'checked' : ''}
                        onchange="toggleMapping(${m.id}, this.checked)">
                    <span>Sincronizar</span>
                </label>
                <div class="info">
                    <strong>${escapeHtml(m.name)}</strong> ${m.is_file ? '📄' : '📁'}<br>
                    <small>${escapeHtml(m.local_path)} → ${escapeHtml(m.remote_path)}</small><br>
                    <small>${m.is_file ? 'Arquivo' : 'Pasta'} | Subpastas: ${m.include_subfolders ? 'Sim' : 'Não'} | Criptografia: ${m.encrypt ? 'Sim' : 'Não'} | ${m.enabled ? 'Selecionado para backup' : 'NÃO será sincronizado'}</small>
                </div>
                <div class="actions">
                    <button onclick="deleteMapping(${m.id})">🗑️</button>
                </div>
            `;
            list.appendChild(div);
        });
        updateMappingsCount();
    } catch (e) {
        console.error(e);
    }
}

function updateMappingsCount() {
    const el = document.getElementById('mappings-count');
    if (!el) return;
    const total = mappingsCache.length;
    const selected = mappingsCache.filter(m => m.enabled).length;
    el.textContent = total
        ? `${selected} de ${total} mapeamento(s) selecionado(s) para o backup`
        : 'Nenhum mapeamento configurado';
}

function getSelectedMappingIds() {
    return Array.from(document.querySelectorAll('.mapping-enabled:checked'))
        .map(cb => parseInt(cb.dataset.id, 10))
        .filter(id => Number.isFinite(id));
}

async function toggleMapping(id, checked) {
    mappingSelectionBusy++;
    try {
        const res = await fetch(`${API}/mappings/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: checked })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'falha ao salvar a seleção');
        }
        await loadMappings();
    } catch (e) {
        alert('Não foi possível salvar a seleção do mapeamento: ' + e.message);
        await loadMappings();
    } finally {
        mappingSelectionBusy--;
    }
}

async function setAllMappings(enabled) {
    if (!mappingsCache.length) return;
    mappingSelectionBusy++;
    try {
        const ids = mappingsCache.map(m => m.id);
        const res = await fetch(`${API}/mappings/bulk-enabled`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, enabled })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'falha ao salvar a seleção');
        }
        await loadMappings();
    } catch (e) {
        alert('Não foi possível salvar a seleção: ' + e.message);
        await loadMappings();
    } finally {
        mappingSelectionBusy--;
    }
}

async function createMapping(e) {
    e.preventDefault();
    const body = {
        name: document.getElementById('m-name').value,
        local_path: document.getElementById('m-local').value,
        remote_path: document.getElementById('m-remote').value,
        include_subfolders: document.getElementById('m-subfolders').checked,
        encrypt: document.getElementById('m-encrypt').checked,
        enabled: true
    };
    try {
        const res = await fetch(API + '/mappings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            document.getElementById('form-mapping').reset();
            loadMappings();
        } else {
            const err = await res.json();
            alert('Erro: ' + (err.detail || 'Desconhecido'));
        }
    } catch (e) {
        alert('Erro: ' + e.message);
    }
}

async function deleteMapping(id) {
    if (!confirm('Remover este mapeamento?')) return;
    await fetch(API + '/mappings/' + id, { method: 'DELETE' });
    loadMappings();
}

async function importCsv() {
    const text = document.getElementById('csv-input').value.trim();
    const result = document.getElementById('csv-result');
    if (!text) {
        result.textContent = 'Cole a lista primeiro.';
        return;
    }
    result.textContent = '⏳ Validando lista...';
    try {
        const payload = {
            csv: text,
            include_subfolders: document.getElementById('csv-subfolders').checked,
            dry_run: true
        };
        let res = await fetch(API + '/mappings/import-csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        let data = await res.json();
        if (!res.ok) {
            result.textContent = '❌ Erro: ' + (data.detail || 'desconhecido');
            return;
        }

        const would = data.would_create || [];
        const errors = data.errors || [];
        let msg = `✅ Válidos: ${(data.parsed || []).length}\n`;
        msg += `🆕 Serão criados: ${would.length}\n`;
        msg += `⏭️ Já existem/duplicados: ${(data.skipped || []).length}\n`;
        msg += `⚠️ Erros: ${errors.length}`;
        if (errors.length) {
            msg += '\n\n' + errors.slice(0, 20).map(e => `Linha ${e.line}: ${e.error}`).join('\n');
        }
        if (would.length) {
            msg += '\n\n' + would.slice(0, 30).map(i => `${i.local_path} → ${i.remote_path}`).join('\n');
            if (would.length > 30) msg += `\n... e mais ${would.length - 30}`;
        }
        result.textContent = msg;
        if (!would.length) return;
        if (!confirm(`Criar ${would.length} mapeamento(s) agora?`)) return;

        payload.dry_run = false;
        res = await fetch(API + '/mappings/import-csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        data = await res.json();
        if (!res.ok) {
            result.textContent = '❌ Erro: ' + (data.detail || 'desconhecido');
            return;
        }
        let done = `✅ Criados: ${(data.created || []).length}\n`;
        done += `⏭️ Ignorados: ${(data.skipped || []).length}\n`;
        done += `⚠️ Erros: ${(data.errors || []).length}`;
        if ((data.errors || []).length) {
            done += '\n\n' + data.errors.slice(0, 20).map(e => `Linha ${e.line}: ${e.error}`).join('\n');
        }
        result.textContent = done;
        loadMappings();
    } catch (e) {
        result.textContent = '❌ Erro: ' + e.message;
    }
}

// ── Sync ──
async function previewSync() {
    const box = document.getElementById('sync-status');
    if (mappingSelectionBusy > 0) {
        box.textContent = '⏳ Aguarde a seleção de mapeamentos ser salva...';
        return;
    }
    const selectedIds = getSelectedMappingIds();
    if (!selectedIds.length) {
        box.textContent = '⚠️ Nenhum mapeamento selecionado. Marque ao menos um na aba Configuração.';
        return;
    }
    box.textContent = '🔍 Gerando prévia... (nenhum arquivo será enviado)';
    try {
        const res = await fetch(API + '/sync/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mapping_ids: selectedIds })
        });
        const data = await res.json();
        if (!res.ok) {
            box.textContent = '❌ ' + (data.detail || 'Falha ao gerar prévia');
            return;
        }
        const c = data.counts || {};
        let msg = '🔍 Prévia do sync\n';
        msg += `📊 Total: ${data.files_total} arquivos\n`;
        msg += `⬆️ Novos: ${c.upload || 0}\n`;
        msg += `♻️ Substituir: ${c.replace || 0}\n`;
        msg += `⏭️ Ignorar: ${c.skip || 0}\n`;
        msg += `⚠️ Erros: ${c.error || 0}\n`;
        msg += `📁 Pastas a criar: ${data.directories || 0}`;
        if ((data.errors || []).length) {
            msg += '\n\nErros:\n' + data.errors.slice(0, 20).map(e =>
                `${e.file || ''}: ${e.error}`).join('\n');
        }
        if ((data.items || []).length) {
            msg += '\n\nPrimeiros itens:\n' + data.items.slice(0, 50).map(item => {
                const icon = item.action === 'upload' ? '⬆️' :
                    item.action === 'replace' ? '♻️' :
                    item.action === 'skip' ? '⏭️' : '⚠️';
                return `${icon} ${item.local_rel_path} → ${item.remote_path}\n   ${item.reason}`;
            }).join('\n');
            if (data.truncated) msg += '\n\n(mostrando só os primeiros 500 itens)';
        }
        box.textContent = msg;
        if (data.files_total > 0 && confirm('Executar este plano agora?')) {
            startSync(selectedIds);
        }
    } catch (e) {
        box.textContent = '❌ Erro ao gerar prévia: ' + e.message;
    }
}

async function startSync(mappingIds = null) {
    if (mappingSelectionBusy > 0) {
        alert('Aguarde a seleção de mapeamentos ser salva.');
        return;
    }
    const ids = mappingIds || getSelectedMappingIds();
    if (!ids.length) {
        alert('Selecione ao menos um mapeamento para sincronizar.');
        return;
    }
    try {
        const res = await fetch(API + '/sync/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mapping_ids: ids })
        });
        const data = await res.json();
        alert('Sync iniciado! Run ID: ' + data.run_id);
        pollSyncStatus();
    } catch (e) {
        alert('Erro: ' + e.message);
    }
}

async function stopSync() {
    await fetch(API + '/sync/stop', { method: 'POST' });
    alert('Sync parado.');
}

async function pollSyncStatus() {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(API + '/sync/status');
            const data = await res.json();
            const box = document.getElementById('sync-status');
            let msg = '';
            if (data.running) {
                msg = `⏳ Sincronizando... ${data.files_uploaded + data.files_skipped + data.files_failed}/${data.files_total} processados\n`;
                msg += `  ✅ Enviados: ${data.files_uploaded}\n`;
                msg += `  ⏭️ Ignorados: ${data.files_skipped}\n`;
                msg += `  ❌ Falhas: ${data.files_failed}\n`;
                if (data.current_file) msg += `  📄 Atual: ${data.current_file}`;
            } else {
                msg = data.error ? `❌ Sync com erro: ${data.error}\n` : `✅ Sync concluído!\n`;
                msg += `  📊 Total: ${data.files_total} arquivos\n`;
                msg += `  ✅ Enviados: ${data.files_uploaded}\n`;
                msg += `  ⏭️ Ignorados: ${data.files_skipped}\n`;
                msg += `  ❌ Falhas: ${data.files_failed}`;
            }
            if ((data.errors || []).length) {
                msg += '\n\n⚠️ Detalhes das falhas:\n' + data.errors.slice(0, 30).map(e =>
                    `${e.file || ''}: ${e.error}`).join('\n');
            }
            box.textContent = msg;
            if (!data.running) {
                clearInterval(interval);
                loadSyncHistory();
            }
        } catch (e) {
            // Mantém o polling; erro transitório de rede não deve parar a UI
        }
    }, 1000);
}

async function loadSyncHistory() {
    try {
        const res = await fetch(API + '/sync/history');
        const data = await res.json();
        const div = document.getElementById('sync-history');
        div.innerHTML = '';
        data.forEach(run => {
            const p = document.createElement('p');
            p.textContent = `Run #${run.id} - ${run.status} - ${run.files_uploaded}/${run.files_total} enviados, ${run.files_failed} falhas (${run.started_at})`;
            div.appendChild(p);
        });
    } catch (e) {
        console.error(e);
    }
}

// ── Restaurar ──

function getRestoreStorageItem(key) {
    try {
        return localStorage.getItem(key);
    } catch (e) {
        return null;
    }
}

function resolveRestoreSelection() {
    const allPaths = restoreFilesCache
        .map(file => file.remote_path)
        .filter(Boolean);
    const selected = RestoreTree.resolveInitialSelection({
        v2Raw: getRestoreStorageItem(RESTORE_SELECTION_KEY),
        v1Raw: getRestoreStorageItem(RESTORE_SELECTION_KEY_V1),
        allPaths: allPaths
    });
    return RestoreTree.pruneSelection(selected, allPaths);
}

function saveRestoreSelectionNow() {
    if (restoreSaveTimer) {
        clearTimeout(restoreSaveTimer);
        restoreSaveTimer = null;
    }
    if (!restoreSelectionDirty) return;
    try {
        localStorage.setItem(
            RESTORE_SELECTION_KEY,
            JSON.stringify(Array.from(restoreSelection))
        );
    } catch (e) {
        // localStorage indisponível: a seleção vale só para esta página
    }
    restoreSelectionDirty = false;
}

function scheduleRestoreSelectionSave() {
    restoreSelectionDirty = true;
    if (restoreSaveTimer) clearTimeout(restoreSaveTimer);
    restoreSaveTimer = setTimeout(saveRestoreSelectionNow, RESTORE_SAVE_DELAY_MS);
}

function updateRestoreCount() {
    const el = document.getElementById('restore-count');
    if (!el) return;
    if (!restoreTree) {
        el.textContent = '';
        return;
    }
    const summary = RestoreTree.selectionSummary(restoreTree, restoreSelection);
    el.textContent = `${summary.count.toLocaleString('pt-BR')} de ${summary.total.toLocaleString('pt-BR')} arquivo(s) selecionado(s) • ${formatBytes(summary.size)} de ${formatBytes(summary.totalSize)}`;
}

function updateRestoreFolderDom(node) {
    if (!node.checkbox) return;
    const state = RestoreTree.folderState(node, restoreSelection);
    node.checkbox.checked = state.checked;
    node.checkbox.indeterminate = state.indeterminate;
    if (node.metaEl) {
        node.metaEl.textContent = `${state.count.toLocaleString('pt-BR')}/${state.total.toLocaleString('pt-BR')} • ${formatBytes(node.totalSize)}`;
    }
}

function refreshRestoreSelectionUI() {
    if (!restoreTree) return;
    RestoreTree.walkDirs(restoreTree, updateRestoreFolderDom);
    document.querySelectorAll('#manifest-list .tree-file-checkbox').forEach(cb => {
        cb.checked = restoreSelection.has(cb.value);
    });
    updateRestoreCount();
}

function isMappingDisabled(mappingId) {
    const mapping = mappingsCache.find(
        m => Number(m.id) === Number(mappingId)
    );
    return mapping ? !mapping.enabled : false;
}

function remoteUnderRestore(remotePath, rootPath) {
    const remote = String(remotePath || '').replace(/\\/g, '/');
    const root = String(rootPath || '')
        .replace(/\\/g, '/')
        .replace(/\/+$/, '');
    return Boolean(root) &&
        (remote === root || remote.startsWith(root + '/'));
}

function mappingRemoteRootLength(mapping) {
    return String(mapping.remote_path || '')
        .replace(/\\/g, '/')
        .replace(/\/+$/, '')
        .length;
}

function mappingMatchesRestore(mapping, mappingName, remotePath) {
    const underRemote = remoteUnderRestore(remotePath, mapping.remote_path);
    const sameName = Boolean(mappingName) &&
        String(mapping.name || '').toLowerCase() ===
        String(mappingName || '').toLowerCase();
    return underRemote || sameName;
}

function getRestoreMapping(mappingId, mappingName, remotePath) {
    const byId = mappingsCache.find(
        m => Number(m.id) === Number(mappingId)
    );
    if (byId && mappingMatchesRestore(byId, mappingName, remotePath)) {
        return byId;
    }

    const byPrefix = mappingsCache.filter(
        m => remoteUnderRestore(remotePath, m.remote_path)
    );
    if (byPrefix.length) {
        const maxLen = Math.max(
            ...byPrefix.map(mappingRemoteRootLength)
        );
        const best = byPrefix.filter(
            m => mappingRemoteRootLength(m) === maxLen
        );
        if (best.length === 1) return best[0];
    }

    const byName = mappingsCache.filter(m =>
        mappingName &&
        String(m.name || '').toLowerCase() ===
        String(mappingName || '').toLowerCase()
    );
    return byName.length === 1 ? byName[0] : null;
}

function getRestoreNodeMapping(node) {
    const file = node.allFiles && node.allFiles[0];
    if (!file) return null;
    return getRestoreMapping(node.mappingId, file.mappingName, file.remotePath);
}

function updateRestoreMode() {
    const el = document.getElementById('restore-mode');
    if (!el) return;
    el.textContent = restoreConfirmOverwrite
        ? 'Modo atual: perguntar antes de sobrescrever arquivos existentes.'
        : 'Modo atual: sobrescrever arquivos existentes sem perguntar (o relatório final mostra as substituições).';
}

function setRestoreFolderExpanded(node, expanded) {
    if (!node.childrenEl) return;
    node.childrenEl.hidden = !expanded;
    node.toggleEl.textContent = expanded ? '▾' : '▸';
    node.toggleEl.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    node.toggleEl.setAttribute(
        'aria-label',
        `${expanded ? 'Recolher' : 'Expandir'} ${node.name}`
    );
}

function renderRestoreDir(node) {
    const wrapper = document.createElement('div');
    wrapper.className = 'tree-folder' + (node.isMapping ? ' tree-mapping' : '');
    wrapper.dataset.dirKey = node.key;

    const row = document.createElement('div');
    row.className = 'tree-folder-row';
    row.style.setProperty('--depth', String(Math.max(0, node.depth - 1)));
    if (node.isMapping && isMappingDisabled(node.mappingId)) {
        row.classList.add('restore-disabled-backup');
    }

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'tree-toggle';
    toggle.textContent = '▸';
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', `Expandir ${node.name}`);
    row.appendChild(toggle);

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'tree-folder-checkbox';
    checkbox.dataset.dirKey = node.key;
    checkbox.title = 'Selecionar todos os arquivos desta pasta';
    checkbox.setAttribute(
        'aria-label',
        `Selecionar todos os arquivos de ${node.name}`
    );
    row.appendChild(checkbox);

    const icon = document.createElement('span');
    icon.className = 'tree-folder-icon';
    icon.textContent = node.isMapping ? '📦' : '📁';
    row.appendChild(icon);

    const name = document.createElement('span');
    name.className = 'tree-folder-name';
    name.textContent = node.name;
    name.title = node.isMapping ? `Mapeamento: ${node.name}` : node.key;
    row.appendChild(name);

    if (node.isMapping && isMappingDisabled(node.mappingId)) {
        const warning = document.createElement('span');
        warning.className = 'tree-badge-warning';
        warning.textContent = '⚠️ backup desativado';
        row.appendChild(warning);
    }

    const meta = document.createElement('span');
    meta.className = 'tree-folder-meta';
    row.appendChild(meta);

    const children = document.createElement('div');
    children.className = 'tree-children';
    children.hidden = true;

    node.rowEl = row;
    node.toggleEl = toggle;
    node.checkbox = checkbox;
    node.metaEl = meta;
    node.childrenEl = children;

    for (const child of node.dirs.values()) {
        children.appendChild(renderRestoreDir(child));
    }
    for (const file of node.files) {
        children.appendChild(renderRestoreFile(file));
    }

    wrapper.appendChild(row);

    if (node.isMapping) {
        const mapping = getRestoreNodeMapping(node);
        const dest = document.createElement('div');
        dest.className = 'tree-mapping-dest';
        if (mapping) {
            dest.textContent = `${mapping.is_file ? '📄 Arquivo' : '📁 Pasta'}: ${mapping.local_path}`;
            dest.title = mapping.local_path;
            if (!mapping.enabled) {
                dest.classList.add('restore-disabled-backup');
            }
        } else {
            dest.textContent = '⚠️ Mapeamento não encontrado em Configuração';
            dest.classList.add('restore-mapping-missing');
        }
        wrapper.appendChild(dest);
    }

    wrapper.appendChild(children);
    restoreDirNodes.set(node.key, node);
    return wrapper;
}

function renderRestoreFile(file) {
    const label = document.createElement('label');
    label.className = 'tree-file' +
        (isMappingDisabled(file.mappingId) ? ' restore-disabled-backup' : '');
    label.style.setProperty('--depth', String(Math.max(0, file.depth - 1)));
    label.title = file.relPath;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'tree-file-checkbox';
    checkbox.value = file.remotePath;
    checkbox.dataset.filePath = file.remotePath;
    label.appendChild(checkbox);

    const icon = document.createElement('span');
    icon.className = 'tree-file-icon';
    icon.textContent = '📄';
    label.appendChild(icon);

    const name = document.createElement('span');
    name.className = 'tree-file-name';
    name.textContent = file.name;
    label.appendChild(name);

    if (file.encrypted) {
        const encrypted = document.createElement('span');
        encrypted.className = 'tree-badge';
        encrypted.textContent = '🔒';
        label.appendChild(encrypted);
    }

    if (isMappingDisabled(file.mappingId)) {
        const warning = document.createElement('span');
        warning.className = 'tree-badge-warning';
        warning.textContent = '⚠️';
        label.appendChild(warning);
    }

    const size = document.createElement('span');
    size.className = 'tree-file-size';
    size.textContent = formatBytes(file.size);
    label.appendChild(size);

    return label;
}

function renderRestoreTree() {
    const container = document.getElementById('manifest-list');
    container.innerHTML = '';
    restoreDirNodes = new Map();
    const fragment = document.createDocumentFragment();
    for (const mapping of restoreTree.dirs.values()) {
        fragment.appendChild(renderRestoreDir(mapping));
    }
    container.appendChild(fragment);
    refreshRestoreSelectionUI();
}

function getRestoreDirNode(element) {
    const wrapper = element.closest('.tree-folder');
    if (!wrapper) return null;
    return restoreDirNodes.get(wrapper.dataset.dirKey) || null;
}

function onRestoreTreeClick(event) {
    if (!(event.target instanceof Element)) return;
    if (event.target.closest('input[type="checkbox"]')) return;
    const row = event.target.closest('.tree-folder-row');
    if (!row) return;
    const node = getRestoreDirNode(row);
    if (!node) return;
    setRestoreFolderExpanded(node, node.childrenEl.hidden);
}

function onRestoreTreeChange(event) {
    const target = event.target;
    if (target.classList.contains('tree-file-checkbox')) {
        if (target.checked) restoreSelection.add(target.value);
        else restoreSelection.delete(target.value);
        scheduleRestoreSelectionSave();
        refreshRestoreSelectionUI();
        return;
    }

    if (target.classList.contains('tree-folder-checkbox')) {
        const node = restoreDirNodes.get(target.dataset.dirKey);
        if (!node) return;
        RestoreTree.applyFolderSelection(node, restoreSelection, target.checked);
        scheduleRestoreSelectionSave();
        refreshRestoreSelectionUI();
    }
}

function setAllRestore(checked) {
    if (!restoreTree) return;
    RestoreTree.applyAllSelection(restoreTree, restoreSelection, checked);
    scheduleRestoreSelectionSave();
    refreshRestoreSelectionUI();
}

function invertRestore() {
    if (!restoreTree) return;
    RestoreTree.invertSelection(restoreTree, restoreSelection);
    scheduleRestoreSelectionSave();
    refreshRestoreSelectionUI();
}

function expandAllRestore() {
    if (!restoreTree) return;
    RestoreTree.walkDirs(restoreTree, node => setRestoreFolderExpanded(node, true));
}

function collapseAllRestore() {
    if (!restoreTree) return;
    RestoreTree.walkDirs(restoreTree, node => setRestoreFolderExpanded(node, false));
}

async function loadManifest() {
    const div = document.getElementById('manifest-list');
    const toolbar = document.getElementById('restore-toolbar');
    const actions = document.getElementById('restore-actions');
    const loadButton = document.getElementById('restore-load-btn');
    const planSummary = document.getElementById('restore-plan-summary');

    if (planSummary) {
        planSummary.hidden = true;
        planSummary.textContent = '';
        planSummary.classList.remove('has-conflicts', 'has-errors');
    }

    try {
        if (!mappingsCache.length) await loadMappings();

        if (loadButton) {
            loadButton.disabled = true;
            loadButton.textContent = '⏳ Carregando manifesto...';
        }
        div.innerHTML = '<p class="restore-loading">Baixando manifesto do Terabox...</p>';
        if (toolbar) toolbar.style.display = 'none';
        if (actions) actions.style.display = 'none';

        const res = await fetch(API + '/restore/manifest');
        if (!res.ok) {
            let detail = `HTTP ${res.status}`;
            try {
                const error = await res.json();
                detail = error.detail || detail;
            } catch (e) {
                // resposta sem JSON
            }
            throw new Error(detail);
        }
        const data = await res.json();
        restoreFilesCache = Array.isArray(data.files)
            ? data.files.filter(file => file && file.remote_path)
            : [];

        if (restoreFilesCache.length === 0) {
            restoreTree = null;
            restoreSelection = new Set();
            restoreDirNodes = new Map();
            div.innerHTML = '';
            const message = document.createElement('p');
            message.textContent = data.error || 'Nenhum arquivo no manifesto.';
            div.appendChild(message);
            if (toolbar) toolbar.style.display = 'none';
            if (actions) actions.style.display = 'none';
            return;
        }

        restoreSelection = resolveRestoreSelection();
        restoreTree = RestoreTree.buildRestoreTree(restoreFilesCache);
        restoreSelectionDirty = false;
        renderRestoreTree();

        if (toolbar) toolbar.style.display = 'flex';
        if (actions) actions.style.display = 'block';
        updateRestoreMode();
    } catch (e) {
        restoreTree = null;
        restoreSelection = new Set();
        restoreDirNodes = new Map();
        div.innerHTML = '';
        const message = document.createElement('p');
        message.className = 'restore-error';
        message.textContent = 'Erro ao carregar manifesto: ' + e.message;
        div.appendChild(message);
        if (toolbar) toolbar.style.display = 'none';
        if (actions) actions.style.display = 'none';
    } finally {
        if (loadButton) {
            loadButton.disabled = false;
            loadButton.textContent = '📥 Carregar Manifesto';
        }
    }
}

function restoreErrorText(detail, fallback) {
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (detail.message) return detail.message;
    return fallback;
}

function updateRestorePlanSummary(summary, conflicts, errors) {
    const el = document.getElementById('restore-plan-summary');
    if (!el) return;
    if (!summary || !summary.total) {
        el.hidden = true;
        el.textContent = '';
        el.classList.remove('has-conflicts', 'has-errors');
        return;
    }
    el.hidden = false;
    el.textContent =
        `${summary.create || 0} criar • ` +
        `${summary.replace || 0} substituir • ` +
        `${summary.errors || 0} erro(s)` +
        (summary.mappings ? ` • ${summary.mappings} mapeamento(s)` : '');
    el.classList.toggle('has-conflicts', conflicts > 0);
    el.classList.toggle('has-errors', errors > 0);
}

async function requestRestoreDownload(files, allowOverwrite) {
    const res = await fetch(API + '/restore/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            files: files,
            allow_overwrite: allowOverwrite
        })
    });

    let payload = null;
    try {
        payload = await res.json();
    } catch (e) {
        payload = null;
    }

    if (!res.ok) {
        const err = new Error(restoreErrorText(
            payload && payload.detail,
            `HTTP ${res.status}`
        ));
        err.status = res.status;
        err.detail = payload && payload.detail;
        throw err;
    }
    return payload || {};
}

async function startRestore() {
    if (!restoreTree) {
        alert('Carregue o manifesto primeiro.');
        return;
    }
    if (restoreSelectionDirty) saveRestoreSelectionNow();

    const files = RestoreTree.collectSelectedPaths(restoreTree, restoreSelection);
    if (files.length === 0) {
        alert('Selecione ao menos um arquivo.');
        return;
    }
    const selection = RestoreTree.selectionSummary(restoreTree, restoreSelection);

    try {
        const statusRes = await fetch(API + '/sync/status');
        if (statusRes.ok) {
            const status = await statusRes.json();
            if (status.running && !confirm(
                'Há um sync em andamento. Restaurar agora pode alterar ' +
                'arquivos que estão sendo enviados.\n\nContinuar?'
            )) {
                return;
            }
        }
    } catch (e) {
        // Sem status do sync, segue com a restauração.
    }

    let plan;
    try {
        const res = await fetch(API + '/restore/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: files })
        });
        if (!res.ok) {
            let detail = `HTTP ${res.status}`;
            try {
                const error = await res.json();
                detail = restoreErrorText(error.detail, detail);
            } catch (e) {
                // resposta sem JSON
            }
            throw new Error(detail);
        }
        plan = await res.json();
    } catch (e) {
        alert('Erro ao preparar a restauração: ' + e.message);
        return;
    }

    const summary = plan.summary || {};
    const targets = Array.isArray(plan.files) ? plan.files : [];
    const valid = targets.filter(target => target.action !== 'error');
    const errors = targets.filter(target => target.action === 'error');
    const conflicts = valid.filter(target => target.action === 'replace');
    updateRestorePlanSummary(summary, conflicts.length, errors.length);

    if (!valid.length) {
        const examples = errors.slice(0, 12).map(target =>
            `${target.remote_path}: ${target.error || 'erro'}`
        ).join('\n');
        alert(
            'Nenhum arquivo pode ser restaurado.\n\n' +
            (examples || 'Verifique os mapeamentos na aba Configuração.')
        );
        return;
    }

    const lines = [
        `${valid.length.toLocaleString('pt-BR')} arquivo(s) para restaurar.`,
        `${summary.create || 0} serão criados.`,
        `${conflicts.length} já existem e serão substituídos.`
    ];
    if (errors.length) {
        lines.push(`${errors.length} arquivo(s) serão ignorados por erro.`);
    }
    lines.push(`Tamanho selecionado: ${formatBytes(selection.size)}.`);

    if (errors.length) {
        const examples = errors.slice(0, 10).map(target =>
            `${target.remote_path}: ${target.error || 'erro'}`
        ).join('\n');
        const proceed = confirm(
            lines.join('\n') + '\n\nNão será possível restaurar:\n' +
            examples +
            (errors.length > 10 ? `\n... e mais ${errors.length - 10}.` : '') +
            '\n\nContinuar apenas com os arquivos válidos?'
        );
        if (!proceed) return;
    }

    if (valid.length > 100 || selection.size > 500 * 1024 * 1024) {
        const confirmed = confirm(
            `Restaurar ${valid.length.toLocaleString('pt-BR')} arquivo(s) ` +
            `(${formatBytes(selection.size)}) nas pastas originais?\n\n` +
            'Isso pode demorar. Continuar?'
        );
        if (!confirmed) return;
    }

    if (conflicts.length && restoreConfirmOverwrite) {
        const examples = conflicts.slice(0, 10)
            .map(target => target.local_path || target.remote_path)
            .join('\n');
        const confirmed = confirm(
            `${conflicts.length.toLocaleString('pt-BR')} arquivo(s) já existem ` +
            'e serão substituídos:\n\n' +
            examples +
            (conflicts.length > 10 ? `\n... e mais ${conflicts.length - 10}.` : '') +
            '\n\nDeseja continuar?'
        );
        if (!confirmed) return;
    }

    const validFiles = valid.map(target => target.remote_path);
    const allowOverwrite = conflicts.length > 0;
    const startBtn = document.getElementById('restore-start-btn');
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.textContent = '⏳ Restaurando...';
    }

    try {
        let data;
        try {
            data = await requestRestoreDownload(validFiles, allowOverwrite);
        } catch (e) {
            if (e.status === 409 && e.detail && Array.isArray(e.detail.conflicts)) {
                const newConflicts = e.detail.conflicts;
                const examples = newConflicts.slice(0, 10)
                    .map(target => target.local_path || target.remote_path)
                    .join('\n');
                const shouldReplace = !restoreConfirmOverwrite || confirm(
                    `${newConflicts.length.toLocaleString('pt-BR')} arquivo(s) ` +
                    'passaram a existir e serão substituídos:\n\n' +
                    examples +
                    '\n\nSubstituir mesmo assim?'
                );
                if (!shouldReplace) return;
                data = await requestRestoreDownload(validFiles, true);
            } else {
                throw e;
            }
        }

        const results = Array.isArray(data.results) ? data.results : [];
        const resultSummary = data.summary || {};
        const replaced = results.filter(result => result.success && result.overwritten);
        const failures = results.filter(result => !result.success);

        let msg = 'Restauração concluída.\n\n' +
            `Restaurados: ${resultSummary.restored ?? results.filter(result => result.success).length}` +
            ` • Criados: ${resultSummary.created ?? 0}` +
            ` • Substituídos: ${resultSummary.replaced ?? replaced.length}` +
            ` • Falhas: ${resultSummary.failed ?? failures.length}`;

        if (replaced.length) {
            msg += '\n\nSubstituídos:\n' + replaced.slice(0, 20)
                .map(result => result.local_path || result.remote_path)
                .join('\n');
            if (replaced.length > 20) {
                msg += `\n... e mais ${replaced.length - 20}.`;
            }
        }

        if (failures.length) {
            msg += '\n\nFalhas:\n' + failures.slice(0, 20).map(result =>
                `${result.remote_path}: ${result.error || 'erro desconhecido'}`
            ).join('\n');
            if (failures.length > 20) {
                msg += `\n... e mais ${failures.length - 20}.`;
            }
        }

        alert(msg);
    } catch (e) {
        alert('Erro ao restaurar: ' + e.message);
    } finally {
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.textContent = '⬇️ Restaurar Selecionados';
        }
    }
}

// ── Settings ──
async function loadSettings() {
    try {
        const res = await fetch(API + '/settings');
        const data = await res.json();
        document.getElementById('s-interval').value = data.sync_interval_minutes;
        document.getElementById('s-autosync').checked = data.auto_sync;
        document.getElementById('s-notifications').checked = data.notifications;
        document.getElementById('s-concurrent').value = data.max_concurrent_uploads;
        document.getElementById('s-browser').value = data.browser_preference;
        document.getElementById('s-autostart').checked = data.autostart;
        restoreConfirmOverwrite = data.restore_confirm_overwrite !== false;
        document.getElementById('s-restore-confirm').checked = restoreConfirmOverwrite;
        updateRestoreMode();
    } catch (e) {
        console.error(e);
    }
}

async function saveSettings(e) {
    e.preventDefault();
    const body = {
        sync_interval_minutes: parseInt(document.getElementById('s-interval').value),
        auto_sync: document.getElementById('s-autosync').checked,
        notifications: document.getElementById('s-notifications').checked,
        max_concurrent_uploads: parseInt(document.getElementById('s-concurrent').value),
        browser_preference: document.getElementById('s-browser').value,
        autostart: document.getElementById('s-autostart').checked,
        restore_confirm_overwrite: document.getElementById('s-restore-confirm').checked
    };
    try {
        const res = await fetch(API + '/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            restoreConfirmOverwrite =
                document.getElementById('s-restore-confirm').checked;
            updateRestoreMode();
            alert('Configurações salvas!');
        }
    } catch (e) {
        alert('Erro: ' + e.message);
    }
}

// ── Seletor de pastas ──
async function pickFolder(inputId) {
    const input = document.getElementById(inputId);
    const oldValue = input.value;
    input.placeholder = 'Abrindo seletor de pastas...';
    input.disabled = true;
    try {
        const res = await fetch(API + '/system/pick-folder');
        const data = await res.json();
        if (data.path) {
            input.value = data.path;
        }
    } catch (e) {
        alert('Não foi possível abrir o seletor de pastas: ' + e.message);
    } finally {
        input.disabled = false;
        input.placeholder = oldValue ? '' : 'C:\\minha\\pasta';
    }
}

// ── Helpers ──
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
    const manifestList = document.getElementById('manifest-list');
    if (manifestList) {
        manifestList.addEventListener('click', onRestoreTreeClick);
        manifestList.addEventListener('change', onRestoreTreeChange);
    }
    window.addEventListener('beforeunload', saveRestoreSelectionNow);

    updateRestoreMode();
    checkAuth();
    loadMappings();
    loadSyncHistory();
    loadSettings();
});