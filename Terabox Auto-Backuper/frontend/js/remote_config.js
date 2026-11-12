/*
 * Helpers puros da revisão de importação da configuração remota.
 *
 * Não toca no DOM. É carregado pelo navegador (window.RemoteConfigUI) e pelos
 * testes Node (module.exports).
 */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.RemoteConfigUI = factory();
    }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    function trimTrailingSeparators(value) {
        return String(value == null ? '' : value).replace(/[\\/]+$/, '');
    }

    function compareKey(value) {
        return String(value == null ? '' : value)
            .replace(/\//g, '\\')
            .toLowerCase();
    }

    /**
     * Troca o prefixo de um caminho local, preservando o restante.
     *
     * Retorna `null` quando o caminho não começa no prefixo antigo (com
     * fronteira de pasta, para não trocar `C:\Fotos2` ao rebasear `C:\Fotos`).
     */
    function rebasePath(path, oldPrefix, newPrefix) {
        const original = String(path == null ? '' : path).trim();
        const oldRaw = String(oldPrefix == null ? '' : oldPrefix).trim();
        const newRaw = String(newPrefix == null ? '' : newPrefix).trim();
        if (!original || !oldRaw || !newRaw) return null;

        const oldTrimmed = trimTrailingSeparators(oldRaw);
        if (!oldTrimmed) return null;

        const pathKey = compareKey(original);
        const oldKey = compareKey(oldTrimmed);
        if (pathKey !== oldKey) {
            if (!pathKey.startsWith(oldKey)) return null;
            const next = pathKey.charAt(oldKey.length);
            if (next !== '\\' && next !== '/') return null;
        }

        let suffix = original.slice(oldTrimmed.length);
        const newTrimmed = trimTrailingSeparators(newRaw);
        if (!newTrimmed) return null;
        const newSeparator = newRaw.includes('\\') ? '\\' : (newRaw.includes('/') ? '/' : '\\');
        if (suffix.startsWith('/') || suffix.startsWith('\\')) {
            suffix = newSeparator + suffix.slice(1);
        }
        return newTrimmed + suffix;
    }

    /**
     * Aplica o rebase nas linhas selecionadas. Devolve uma nova lista.
     */
    function rebaseRows(rows, oldPrefix, newPrefix, selectedUids) {
        const selected = selectedUids instanceof Set
            ? selectedUids
            : (Array.isArray(selectedUids) ? new Set(selectedUids) : null);
        return (Array.isArray(rows) ? rows : []).map(row => {
            if (selected && !selected.has(row.uid)) return row;
            const updated = rebasePath(row.local_path, oldPrefix, newPrefix);
            return updated ? Object.assign({}, row, { local_path: updated }) : row;
        });
    }

    function defaultSelection(rows) {
        const selected = new Set();
        for (const row of Array.isArray(rows) ? rows : []) {
            if (row && row.uid && row.selected && !row.blocked) {
                selected.add(row.uid);
            }
        }
        return selected;
    }

    function selectionSummary(rows, selectedUids) {
        const selected = selectedUids instanceof Set
            ? selectedUids
            : new Set(selectedUids || []);
        const summary = {
            total: 0,
            selected: 0,
            new: 0,
            existing: 0,
            conflicts: 0,
            blocked: 0,
            pathErrors: 0
        };
        for (const row of Array.isArray(rows) ? rows : []) {
            if (!row) continue;
            summary.total++;
            if (selected.has(row.uid)) {
                summary.selected++;
                if (row.status === 'new') summary.new++;
                if (row.status === 'existing') summary.existing++;
            }
            if (row.status === 'conflict') summary.conflicts++;
            if (row.blocked) summary.blocked++;
            if (row.path_error) summary.pathErrors++;
        }
        return summary;
    }

    function validateLocalPathHint(row, localPath) {
        const value = String(localPath == null ? '' : localPath).trim();
        if (!value) return 'Escolha um caminho local.';
        if (row && row.is_file && /[\\/]$/.test(value)) {
            return 'Para arquivo único, informe o arquivo completo.';
        }
        return null;
    }

    function statusLabel(row) {
        if (!row) return '';
        if (row.status === 'conflict') return 'conflito';
        if (row.status === 'new') return 'novo';
        if (row.needs_update) return 'atualizar';
        return 'já existe';
    }

    return {
        rebasePath: rebasePath,
        rebaseRows: rebaseRows,
        defaultSelection: defaultSelection,
        selectionSummary: selectionSummary,
        validateLocalPathHint: validateLocalPathHint,
        statusLabel: statusLabel
    };
});
