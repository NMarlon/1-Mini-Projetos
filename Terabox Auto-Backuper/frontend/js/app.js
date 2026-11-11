// Terabox Auto-Backuper - Frontend

const API = '/api';

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
        const list = document.getElementById('mappings-list');
        list.innerHTML = '';
        if (data.length === 0) {
            list.innerHTML = '<p>Nenhum mapeamento configurado.</p>';
            return;
        }
        data.forEach(m => {
            const div = document.createElement('div');
            div.className = 'mapping-item';
            div.innerHTML = `
                <div class="info">
                    <strong>${escapeHtml(m.name)}</strong> ${m.is_file ? '📄' : '📁'}<br>
                    <small>${escapeHtml(m.local_path)} → ${escapeHtml(m.remote_path)}</small><br>
                    <small>${m.is_file ? 'Arquivo' : 'Pasta'} | Subpastas: ${m.include_subfolders ? 'Sim' : 'Não'} | Criptografia: ${m.encrypt ? 'Sim' : 'Não'} | ${m.enabled ? 'Ativo' : 'Inativo'}</small>
                </div>
                <div class="actions">
                    <button onclick="deleteMapping(${m.id})">🗑️</button>
                </div>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error(e);
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
    box.textContent = '🔍 Gerando prévia... (nenhum arquivo será enviado)';
    try {
        const res = await fetch(API + '/sync/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{}'
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
            startSync();
        }
    } catch (e) {
        box.textContent = '❌ Erro ao gerar prévia: ' + e.message;
    }
}

async function startSync() {
    try {
        const res = await fetch(API + '/sync/start', { method: 'POST' });
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
async function loadManifest() {
    try {
        const res = await fetch(API + '/restore/manifest');
        const data = await res.json();
        const div = document.getElementById('manifest-list');
        div.innerHTML = '';
        if (!data.files || data.files.length === 0) {
            div.innerHTML = '<p>Nenhum arquivo no manifesto.</p>';
            return;
        }
        data.files.forEach(f => {
            const label = document.createElement('label');
            const enc = f.encrypted ? ' 🔒' : '';
            const map = f.mapping_name ? ` [${escapeHtml(f.mapping_name)}]` : '';
            label.innerHTML = `<input type="checkbox" value="${escapeHtml(f.remote_path)}"> ${escapeHtml(f.local_rel_path)}${enc}${map} (${formatBytes(f.size)})`;
            div.appendChild(label);
            div.appendChild(document.createElement('br'));
        });
        document.getElementById('restore-actions').style.display = 'block';
    } catch (e) {
        alert('Erro ao carregar manifesto: ' + e.message);
    }
}

async function startRestore() {
    const checkboxes = document.querySelectorAll('#manifest-list input[type="checkbox"]:checked');
    const files = Array.from(checkboxes).map(cb => cb.value);
    const dest = document.getElementById('restore-dest').value;
    if (files.length === 0) { alert('Selecione ao menos um arquivo.'); return; }
    if (!dest) { alert('Informe a pasta de destino.'); return; }
    try {
        const res = await fetch(API + '/restore/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                files,
                destination: dest,
                preserve_structure: document.getElementById('restore-structure').checked
            })
        });
        const data = await res.json();
        const ok = data.results.filter(r => r.success).length;
        let msg = 'Restauração concluída: ' + ok + '/' + data.results.length;
        const failures = data.results.filter(r => !r.success);
        if (failures.length) {
            msg += '\n\nFalhas:\n' + failures.slice(0, 20).map(r =>
                `${r.remote_path}: ${r.error || 'erro desconhecido'}`).join('\n');
        }
        alert(msg);
    } catch (e) {
        alert('Erro: ' + e.message);
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
        autostart: document.getElementById('s-autostart').checked
    };
    try {
        const res = await fetch(API + '/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
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
        input.placeholder = oldValue ? '' : (inputId === 'm-local' ? 'C:\\minha\\pasta' : 'C:\\restore');
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
    checkAuth();
    loadMappings();
    loadSyncHistory();
    loadSettings();
});