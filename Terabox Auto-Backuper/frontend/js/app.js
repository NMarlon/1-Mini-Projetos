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

// Configuração remota de mapeamentos
const REMOTE_BANNER_DISMISS_KEY = 'terabox_remote_config_dismissed_hash';
let remoteConfigStatus = null;
let remoteImportPlan = null;
let remoteImportSelected = new Set();
let remoteConfigCheckInFlight = false;
let remoteConfigAuthWasReady = false;

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
            if (!remoteConfigAuthWasReady) {
                remoteConfigAuthWasReady = true;
                checkRemoteConfig(true);
            }
        } else {
            const err = data.error ? ` — ${data.error}` : '';
            statusEl.textContent = '❌ Não conectado ao Terabox' + err;
            btnConnect.style.display = 'inline-block';
            btnDisconnect.style.display = 'none';
            remoteConfigAuthWasReady = false;
            const remoteStatus = document.getElementById('remote-config-status');
            if (remoteStatus && !remoteConfigStatus) {
                remoteStatus.textContent =
                    'Conecte ao Terabox para verificar a configuração remota.';
                remoteStatus.classList.remove('has-error');
            }
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
    remoteConfigAuthWasReady = false;
    remoteConfigStatus = null;
    hideRemoteConfigBanner();
    checkAuth();
}

// ── Configuração remota de mapeamentos ──

function getDismissedRemoteConfigHash() {
    try {
        return localStorage.getItem(REMOTE_BANNER_DISMISS_KEY) || '';
    } catch (e) {
        return '';
    }
}

function setDismissedRemoteConfigHash(hash) {
    try {
        localStorage.setItem(REMOTE_BANNER_DISMISS_KEY, hash || '');
    } catch (e) {
        // localStorage indisponível: o banner pode reaparecer
    }
}

function hideRemoteConfigBanner() {
    const banner = document.getElementById('remote-config-banner');
    if (banner) banner.hidden = true;
}

function dismissRemoteConfigBanner() {
    const remote = (remoteConfigStatus && remoteConfigStatus.remote) || {};
    setDismissedRemoteConfigHash(remote.config_hash || '');
    hideRemoteConfigBanner();
}

function showRemoteConfigBanner(status) {
    const banner = document.getElementById('remote-config-banner');
    const detail = document.getElementById('remote-config-banner-detail');
    if (!banner || !detail) return;
    const remote = status.remote || {};
    const summary = remote.import_summary || {};
    const parts = [];
    if (summary.new) parts.push(`${summary.new} novo(s)`);
    if (summary.conflicts) parts.push(`${summary.conflicts} conflito(s)`);
    const source = remote.source === 'shortcut'
        ? 'encontrada pelo atalho da raiz'
        : 'encontrada no caminho configurado';
    detail.textContent =
        `${parts.join(' e ') || 'Novos mapeamentos'} em ` +
        `${remote.mappings_total || 0} mapeamento(s), ${source}. ` +
        'Revise antes de importar para este computador.';
    banner.hidden = false;
}

async function checkRemoteConfig(showBanner = false) {
    if (remoteConfigCheckInFlight) return;
    remoteConfigCheckInFlight = true;
    try {
        const res = await fetch(API + '/remote-config?check_remote=true');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        remoteConfigStatus = data;
        renderRemoteConfigStatus(data);

        const remote = data.remote || {};
        const dismissed = getDismissedRemoteConfigHash();
        const canShow = Boolean(
            showBanner &&
            data.enabled &&
            remote.exists &&
            remote.needs_import &&
            remote.config_hash &&
            remote.config_hash !== dismissed
        );
        if (canShow) showRemoteConfigBanner(data);
        else hideRemoteConfigBanner();
    } catch (e) {
        const el = document.getElementById('remote-config-status');
        if (el) {
            el.textContent = '⚠️ Não foi possível verificar a configuração remota: ' + e.message;
            el.classList.add('has-error');
        }
        hideRemoteConfigBanner();
    } finally {
        remoteConfigCheckInFlight = false;
    }
}

function renderRemoteConfigStatus(data) {
    const el = document.getElementById('remote-config-status');
    if (!el) return;
    const lines = [];
    if (!data.enabled) {
        lines.push('⏸️ Configuração remota desativada. Nada será salvo no Terabox.');
    } else {
        lines.push(`Computador: ${data.machine_name || '(sem nome)'}`);
        lines.push(`Arquivo: ${data.path || ''}`);
        lines.push(`Atalho fixo: ${data.shortcut_path || ''}`);

        const remote = data.remote || {};
        if (!remote.checked) {
            lines.push('ℹ️ Conecte ao Terabox para verificar o arquivo remoto.');
        } else if (remote.error) {
            lines.push('⚠️ ' + remote.error);
        } else if (!remote.exists) {
            lines.push('ℹ️ Nenhum arquivo remoto encontrado ainda. Ele será criado no próximo salvamento.');
        } else {
            const source = remote.source === 'shortcut'
                ? 'atalho da raiz'
                : 'caminho configurado';
            lines.push(`✅ Arquivo encontrado (${source}): ${remote.path || ''}`);
            const summary = remote.import_summary;
            if (summary) {
                lines.push(
                    `Mapeamentos no arquivo: ${remote.mappings_total || 0}. ` +
                    `Neste PC: ${summary.new || 0} novo(s), ` +
                    `${summary.existing || 0} existente(s), ` +
                    `${summary.conflicts || 0} conflito(s).`
                );
            }
            if (remote.needs_import) {
                lines.push('📥 Use "Revisar importação" para escolher os caminhos deste computador.');
            }
        }

        if (data.last_saved_at) {
            lines.push('Último salvamento: ' + data.last_saved_at);
        }
        if (data.last_error) {
            lines.push('⚠️ Último erro: ' + data.last_error);
        }
        if (data.dirty) {
            lines.push('⏳ Alterações aguardando salvamento...');
        }
    }
    el.textContent = lines.join('\n');
    el.classList.toggle(
        'has-error',
        Boolean(data.last_error || (data.remote && data.remote.error))
    );
}

async function saveRemoteConfigNow(force = false) {
    const el = document.getElementById('remote-config-status');
    if (el) {
        el.textContent = force
            ? '⏳ Substituindo a configuração remota...'
            : '⏳ Salvando configuração no Terabox...';
        el.classList.remove('has-error');
    }
    try {
        const res = await fetch(API + '/remote-config/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force })
        });
        let data = {};
        try {
            data = await res.json();
        } catch (e) {
            data = {};
        }
        if (!res.ok) {
            if (!force && res.status === 409) {
                const detail = typeof data.detail === 'string'
                    ? data.detail
                    : 'A configuração remota precisa de confirmação.';
                if (confirm(detail + '\n\nDeseja substituir mesmo assim?')) {
                    return saveRemoteConfigNow(true);
                }
                if (el) el.textContent = 'Salvamento cancelado.';
                return;
            }
            throw new Error(restoreErrorText(data.detail, `HTTP ${res.status}`));
        }
        if (data.skipped) {
            if (el) el.textContent = 'Configuração remota desativada.';
        } else if (data.changed) {
            if (el) el.textContent = '✅ Configuração salva no Terabox.';
        } else {
            if (el) el.textContent = '✅ A configuração já estava atualizada.';
        }
        await checkRemoteConfig(false);
    } catch (e) {
        if (el) {
            el.textContent = '⚠️ ' + e.message;
            el.classList.add('has-error');
        }
    }
}

function findRemoteImportInput(uid) {
    return Array.from(document.querySelectorAll('.remote-import-path'))
        .find(element => element.dataset.uid === uid) || null;
}

function findRemoteImportRow(uid) {
    if (!remoteImportPlan) return null;
    return (remoteImportPlan.mappings || []).find(row => row.uid === uid) || null;
}

async function openRemoteConfigImport() {
    const modal = document.getElementById('remote-config-modal');
    const list = document.getElementById('remote-import-list');
    const summary = document.getElementById('remote-import-summary');
    if (!modal || !list) return;

    modal.hidden = false;
    list.innerHTML = '<p class="restore-loading">Baixando configuração do Terabox...</p>';
    if (summary) summary.textContent = '';

    try {
        const res = await fetch(API + '/remote-config/import/plan', {
            method: 'POST'
        });
        let data = {};
        try {
            data = await res.json();
        } catch (e) {
            data = {};
        }
        if (!res.ok) {
            throw new Error(restoreErrorText(data.detail, `HTTP ${res.status}`));
        }
        if (data.error) throw new Error(data.error);
        if (!data.exists) {
            closeRemoteConfigModal();
            alert(
                'Nenhuma configuração foi encontrada no Terabox.\n\n' +
                'Salve os mapeamentos deste computador primeiro ou confira o ' +
                'caminho configurado.'
            );
            return;
        }
        if (!Array.isArray(data.mappings) || data.mappings.length === 0) {
            closeRemoteConfigModal();
            alert('O arquivo de configuração remota não contém mapeamentos.');
            return;
        }
        remoteImportPlan = data;
        remoteImportSelected = RemoteConfigUI.defaultSelection(data.mappings);
        renderRemoteImportPlan();
    } catch (e) {
        closeRemoteConfigModal();
        alert('Erro ao carregar a configuração remota: ' + e.message);
    }
}

function closeRemoteConfigModal() {
    const modal = document.getElementById('remote-config-modal');
    if (modal) modal.hidden = true;
}

function renderRemoteImportPlan() {
    const list = document.getElementById('remote-import-list');
    const summaryEl = document.getElementById('remote-import-summary');
    if (!list || !remoteImportPlan) return;

    const summary = remoteImportPlan.summary || {};
    if (summaryEl) {
        const source = remoteImportPlan.source === 'shortcut'
            ? 'atalho da raiz'
            : 'caminho configurado';
        summaryEl.textContent =
            `Arquivo: ${remoteImportPlan.path || ''} (${source})\n` +
            `${summary.new || 0} novo(s), ${summary.existing || 0} já existente(s), ` +
            `${summary.conflicts || 0} conflito(s). ` +
            'Revise os caminhos e marque o que deseja importar.';
    }

    list.innerHTML = '';
    for (const row of remoteImportPlan.mappings || []) {
        const rowEl = document.createElement('div');
        rowEl.className = 'remote-import-row' + (row.blocked ? ' is-blocked' : '');
        rowEl.dataset.uid = row.uid;

        const checked = remoteImportSelected.has(row.uid);
        const typeIcon = row.is_file ? '📄' : '📁';
        const status = RemoteConfigUI.statusLabel(row);
        const otherMachines = (row.other_machines || []).map(machine =>
            `${escapeHtml(machine.machine_name)}: ${escapeHtml(machine.local_path)}`
        ).join('<br>');
        const warnings = (row.warnings || [])
            .map(warning => `<div class="remote-import-warning">⚠️ ${escapeHtml(warning)}</div>`)
            .join('');
        const conflicts = (row.conflicts || [])
            .map(conflict => `<div class="remote-import-error">⛔ ${escapeHtml(conflict)}</div>`)
            .join('');
        const pathError = row.path_error
            ? `<div class="remote-import-error remote-import-path-error">⛔ ${escapeHtml(row.path_error)}</div>`
            : '';
        const existingInfo = row.status === 'existing' && row.current_local_path
            ? `<div class="remote-import-existing">Já existe neste PC: ${escapeHtml(row.current_local_path)}</div>`
            : '';

        rowEl.innerHTML = `
            <label class="remote-import-check" title="Importar/atualizar este mapeamento">
                <input type="checkbox" class="remote-import-checkbox"
                    data-uid="${escapeAttr(row.uid)}" ${checked ? 'checked' : ''}
                    ${row.blocked ? 'disabled' : ''}>
            </label>
            <div class="remote-import-body">
                <div class="remote-import-title">
                    <strong>${typeIcon} ${escapeHtml(row.name)}</strong>
                    <span class="remote-import-badge ${escapeHtml(row.status)}">${escapeHtml(status)}</span>
                </div>
                <div class="remote-import-remote">${escapeHtml(row.remote_path)}</div>
                ${existingInfo}
                ${otherMachines ? `<div class="remote-import-other">Também usado em:<br>${otherMachines}</div>` : ''}
                ${conflicts}${warnings}${pathError}
                <div class="input-row remote-import-path-row">
                    <input type="text" class="remote-import-path"
                        data-uid="${escapeAttr(row.uid)}"
                        value="${escapeAttr(row.local_path || '')}"
                        placeholder="C:\\...">
                    <button type="button" class="btn-browse remote-import-pick"
                        data-uid="${escapeAttr(row.uid)}"
                        data-is-file="${row.is_file ? 'true' : 'false'}">
                        ${row.is_file ? '📄 Selecionar...' : '📁 Selecionar...'}
                    </button>
                </div>
            </div>
        `;
        list.appendChild(rowEl);
    }
    updateRemoteImportCount();
}

function updateRemoteImportCount() {
    const el = document.getElementById('remote-import-count');
    const confirmButton = document.getElementById('remote-import-confirm');
    if (!el) return;
    const rows = remoteImportPlan ? remoteImportPlan.mappings : [];
    const summary = RemoteConfigUI.selectionSummary(rows, remoteImportSelected);
    el.textContent =
        `${summary.selected} de ${summary.total} selecionado(s) • ` +
        `${summary.new} novo(s) • ${summary.existing} existente(s) • ` +
        `${summary.conflicts} conflito(s)`;
    if (confirmButton) confirmButton.disabled = summary.selected === 0;
}

function setAllRemoteImport(checked) {
    if (!remoteImportPlan) return;
    for (const row of remoteImportPlan.mappings || []) {
        if (row.blocked) continue;
        if (checked) remoteImportSelected.add(row.uid);
        else remoteImportSelected.delete(row.uid);
    }
    document.querySelectorAll('.remote-import-checkbox').forEach(checkbox => {
        checkbox.checked = remoteImportSelected.has(checkbox.dataset.uid);
    });
    updateRemoteImportCount();
}

function applyRemoteRebase() {
    if (!remoteImportPlan) return;
    const oldPrefix = document.getElementById('remote-rebase-old').value.trim();
    const newPrefix = document.getElementById('remote-rebase-new').value.trim();
    if (!oldPrefix || !newPrefix) {
        alert('Informe o prefixo antigo e o novo prefixo.');
        return;
    }
    const before = new Map(
        (remoteImportPlan.mappings || []).map(row => [row.uid, row.local_path])
    );
    remoteImportPlan.mappings = RemoteConfigUI.rebaseRows(
        remoteImportPlan.mappings,
        oldPrefix,
        newPrefix,
        remoteImportSelected
    );
    let changed = 0;
    for (const row of remoteImportPlan.mappings) {
        if (before.get(row.uid) === row.local_path) continue;
        changed++;
        row.path_error = null;
        const input = findRemoteImportInput(row.uid);
        if (input) input.value = row.local_path;
        const rowEl = input && input.closest('.remote-import-row');
        if (rowEl) {
            const errorEl = rowEl.querySelector('.remote-import-path-error');
            if (errorEl) errorEl.remove();
        }
    }
    if (!changed) {
        alert('Nenhum caminho selecionado usa esse prefixo.');
    }
}

async function pickRemoteImportPath(uid, isFile) {
    const endpoint = isFile ? '/system/pick-file' : '/system/pick-folder';
    try {
        const res = await fetch(API + endpoint);
        const data = await res.json();
        if (!data.path) return;
        const row = findRemoteImportRow(uid);
        const input = findRemoteImportInput(uid);
        if (row) {
            row.local_path = data.path;
            row.path_error = null;
        }
        if (input) {
            input.value = data.path;
            const rowEl = input.closest('.remote-import-row');
            if (rowEl) {
                const errorEl = rowEl.querySelector('.remote-import-path-error');
                if (errorEl) errorEl.remove();
            }
        }
    } catch (e) {
        alert('Não foi possível abrir o seletor: ' + e.message);
    }
}

async function confirmRemoteImport() {
    if (!remoteImportPlan) return;
    const selectedRows = (remoteImportPlan.mappings || [])
        .filter(row => remoteImportSelected.has(row.uid) && !row.blocked);
    if (selectedRows.length === 0) {
        alert('Selecione ao menos um mapeamento para importar.');
        return;
    }

    const mappings = [];
    for (const row of selectedRows) {
        const input = findRemoteImportInput(row.uid);
        const localPath = (input ? input.value : row.local_path || '').trim();
        const hint = RemoteConfigUI.validateLocalPathHint(row, localPath);
        if (hint) {
            alert(`${row.name}: ${hint}`);
            if (input) input.focus();
            return;
        }
        mappings.push({ uid: row.uid, local_path: localPath });
    }

    const confirmed = confirm(
        `Importar ${mappings.length} mapeamento(s) para este computador?\n\n` +
        'Os mapeamentos já existentes serão atualizados e os novos serão ' +
        'criados. Nenhum arquivo será restaurado agora; isso apenas prepara a ' +
        'aba Restaurar.'
    );
    if (!confirmed) return;

    const button = document.getElementById('remote-import-confirm');
    if (button) {
        button.disabled = true;
        button.textContent = '⏳ Importando...';
    }
    try {
        const res = await fetch(API + '/remote-config/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                config_hash: remoteImportPlan.config_hash || '',
                mappings,
                adopt_path: true
            })
        });
        let data = {};
        try {
            data = await res.json();
        } catch (e) {
            data = {};
        }
        if (!res.ok) {
            const detail = restoreErrorText(data.detail, `HTTP ${res.status}`);
            if (res.status === 409) {
                alert(
                    'A configuração remota mudou ou precisa de atenção:\n\n' +
                    detail +
                    '\n\nRecarregue a revisão e tente novamente.'
                );
                await openRemoteConfigImport();
                return;
            }
            throw new Error(detail);
        }

        const created = (data.created || []).length;
        const updated = (data.updated || []).length;
        const skipped = (data.skipped || []).length;
        const errors = data.errors || [];
        let message =
            'Importação concluída.\n\n' +
            `Criados: ${created} • Atualizados: ${updated} • ` +
            `Ignorados: ${skipped} • Erros: ${errors.length}`;
        if (errors.length) {
            message += '\n\n' + errors.slice(0, 10)
                .map(error => `${error.uid}: ${error.error}`)
                .join('\n');
            if (errors.length > 10) {
                message += `\n... e mais ${errors.length - 10}.`;
            }
        }
        if (data.remote_config_save_error) {
            message += '\n\n⚠️ A importação funcionou, mas o arquivo remoto ' +
                'não pôde ser atualizado: ' + data.remote_config_save_error;
        }
        alert(message);
        remoteImportPlan = null;
        remoteImportSelected = new Set();
        closeRemoteConfigModal();
        await loadMappings();
        await loadSettings();
        await checkRemoteConfig(false);
    } catch (e) {
        alert('Erro ao importar a configuração: ' + e.message);
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = 'Importar selecionados';
        }
    }
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
    const kind = document.getElementById('m-kind').value;
    const body = {
        name: document.getElementById('m-name').value,
        local_path: document.getElementById('m-local').value,
        remote_path: document.getElementById('m-remote').value,
        include_subfolders: document.getElementById('m-subfolders').checked,
        encrypt: document.getElementById('m-encrypt').checked,
        enabled: true,
        is_file: kind === 'file' ? true : (kind === 'folder' ? false : null)
    };
    try {
        const res = await fetch(API + '/mappings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            document.getElementById('form-mapping').reset();
            const kind = document.getElementById('m-kind');
            if (kind) kind.value = '';
            updateMappingKind();
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
        const warnings = (data.parsed || []).flatMap(i =>
            (i.warnings || []).map(w => `Linha ${i.line}: ${w}`)
        );
        if (warnings.length) {
            msg += '\n\nAvisos:\n' + warnings.slice(0, 20).join('\n');
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

function isMappingDisabled(mappingId, mappingUid = null) {
    let mapping = null;
    if (mappingUid) {
        mapping = mappingsCache.find(
            m => String(m.uid || '') === String(mappingUid)
        ) || null;
    }
    if (!mapping) {
        mapping = mappingsCache.find(
            m => Number(m.id) === Number(mappingId)
        ) || null;
    }
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

function getRestoreMapping(mappingId, mappingName, remotePath, mappingUid = null) {
    if (mappingUid) {
        const byUid = mappingsCache.find(
            m => String(m.uid || '') === String(mappingUid)
        );
        if (byUid) return byUid;
    }

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
    return getRestoreMapping(
        node.mappingId,
        file.mappingName,
        file.remotePath,
        node.mappingUid || file.mappingUid
    );
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
    if (node.isMapping && isMappingDisabled(node.mappingId, node.mappingUid)) {
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

    if (node.isMapping && isMappingDisabled(node.mappingId, node.mappingUid)) {
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
        (isMappingDisabled(file.mappingId, file.mappingUid)
            ? ' restore-disabled-backup'
            : '');
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

    if (isMappingDisabled(file.mappingId, file.mappingUid)) {
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
        document.getElementById('s-machine-name').value = data.machine_name || '';
        document.getElementById('s-remote-enabled').checked =
            data.remote_config_enabled !== false;
        document.getElementById('s-remote-path').value =
            data.remote_config_path || '';
        document.getElementById('s-remote-autosave').checked =
            data.remote_config_auto_save !== false;
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
        restore_confirm_overwrite: document.getElementById('s-restore-confirm').checked,
        machine_name: document.getElementById('s-machine-name').value,
        remote_config_enabled: document.getElementById('s-remote-enabled').checked,
        remote_config_path: document.getElementById('s-remote-path').value,
        remote_config_auto_save: document.getElementById('s-remote-autosave').checked
    };
    try {
        const res = await fetch(API + '/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            const saved = await res.json().catch(() => ({}));
            if (saved.remote_config_path) {
                document.getElementById('s-remote-path').value =
                    saved.remote_config_path;
            }
            if (saved.machine_name) {
                document.getElementById('s-machine-name').value =
                    saved.machine_name;
            }
            restoreConfirmOverwrite =
                document.getElementById('s-restore-confirm').checked;
            updateRestoreMode();
            checkRemoteConfig(false);
            alert('Configurações salvas!');
        } else {
            let detail = `HTTP ${res.status}`;
            try {
                const error = await res.json();
                detail = restoreErrorText(error.detail, detail);
            } catch (e) {
                // resposta sem JSON
            }
            alert('Erro ao salvar configurações: ' + detail);
        }
    } catch (e) {
        alert('Erro: ' + e.message);
    }
}

// ── Seletor de pastas e arquivos ──
function updateMappingKind() {
    const kind = document.getElementById('m-kind').value;
    const subfolders = document.getElementById('m-subfolders');
    if (!subfolders) return;
    if (kind === 'file') {
        subfolders.checked = false;
        subfolders.disabled = true;
    } else {
        subfolders.disabled = false;
    }
}

async function pickMappingSource() {
    const kind = document.getElementById('m-kind').value;
    await pickFolder('m-local', kind === 'file' ? 'pick-file' : 'pick-folder');
}

async function pickFolder(inputId, endpoint = 'pick-folder') {
    const input = document.getElementById(inputId);
    const oldValue = input.value;
    input.placeholder = 'Abrindo seletor...';
    input.disabled = true;
    try {
        const res = await fetch(API + '/system/' + endpoint);
        const data = await res.json();
        if (data.path) {
            input.value = data.path;
        }
    } catch (e) {
        alert('Não foi possível abrir o seletor: ' + e.message);
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

function escapeAttr(text) {
    return String(text == null ? '' : text)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
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

    const remoteImportList = document.getElementById('remote-import-list');
    if (remoteImportList) {
        remoteImportList.addEventListener('click', event => {
            const target = event.target;
            if (target.classList.contains('remote-import-pick')) {
                pickRemoteImportPath(
                    target.dataset.uid,
                    target.dataset.isFile === 'true'
                );
            }
        });
        remoteImportList.addEventListener('change', event => {
            const target = event.target;
            if (target.classList.contains('remote-import-checkbox')) {
                if (target.checked) remoteImportSelected.add(target.dataset.uid);
                else remoteImportSelected.delete(target.dataset.uid);
                updateRemoteImportCount();
            }
            if (target.classList.contains('remote-import-path')) {
                const row = findRemoteImportRow(target.dataset.uid);
                if (row) {
                    row.local_path = target.value;
                    row.path_error = null;
                }
                const rowEl = target.closest('.remote-import-row');
                if (rowEl) {
                    const errorEl = rowEl.querySelector('.remote-import-path-error');
                    if (errorEl) errorEl.remove();
                }
            }
        });
        remoteImportList.addEventListener('input', event => {
            const target = event.target;
            if (!target.classList.contains('remote-import-path')) return;
            const row = findRemoteImportRow(target.dataset.uid);
            if (row) {
                row.local_path = target.value;
                row.path_error = null;
            }
            const rowEl = target.closest('.remote-import-row');
            if (rowEl) {
                const errorEl = rowEl.querySelector('.remote-import-path-error');
                if (errorEl) errorEl.remove();
            }
        });
    }

    const remoteModal = document.getElementById('remote-config-modal');
    if (remoteModal) {
        remoteModal.addEventListener('click', event => {
            if (event.target === remoteModal) closeRemoteConfigModal();
        });
    }
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeRemoteConfigModal();
    });

    window.addEventListener('beforeunload', saveRestoreSelectionNow);

    updateRestoreMode();
    checkAuth();
    loadMappings();
    loadSyncHistory();
    loadSettings();
});