/*
 * Helpers puros da árvore de restauração.
 *
 * Este arquivo não toca no DOM: ele só monta a árvore a partir do manifesto,
 * resolve a seleção inicial e calcula estados de pasta. Isso permite testar a
 * lógica com `node --test` sem precisar de navegador.
 */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.RestoreTree = factory();
    }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    const collator = new Intl.Collator('pt-BR', {
        numeric: true,
        sensitivity: 'base'
    });

    function normalizeRelPath(value) {
        return String(value == null ? '' : value)
            .replace(/\\/g, '/')
            .replace(/^\/+|\/+$/g, '');
    }

    function pathSegments(value) {
        return normalizeRelPath(value)
            .split('/')
            .filter(part => part && part !== '.');
    }

    function baseName(value) {
        const parts = pathSegments(value);
        return parts.length ? parts[parts.length - 1] : '';
    }

    function createDirNode(name, key, depth, parent) {
        return {
            kind: 'dir',
            name: name,
            key: key,
            depth: depth,
            parent: parent,
            dirs: new Map(),
            files: [],
            fileCount: 0,
            totalSize: 0,
            allFiles: null,
            mappingId: null,
            mappingUid: null,
            isMapping: false
        };
    }

    function getMappingKey(file) {
        if (file.mapping_uid) {
            return 'mapping-uid:' + file.mapping_uid;
        }
        if (file.mapping_id !== undefined && file.mapping_id !== null) {
            return 'mapping:' + file.mapping_id;
        }
        return 'mapping-name:' + String(file.mapping_name || 'outros');
    }

    function getMappingName(file) {
        if (file.mapping_name) return String(file.mapping_name);
        if (file.mapping_id !== undefined && file.mapping_id !== null) {
            return 'Mapeamento ' + file.mapping_id;
        }
        return 'Outros';
    }

    function buildRestoreTree(files) {
        const list = Array.isArray(files) ? files : [];
        const rootNode = createDirNode('', 'root', 0, null);

        for (const file of list) {
            if (!file) continue;

            const mKey = getMappingKey(file);
            let mapping = rootNode.dirs.get(mKey);
            if (!mapping) {
                mapping = createDirNode(getMappingName(file), mKey, 1, rootNode);
                mapping.isMapping = true;
                mapping.mappingId = file.mapping_id;
                mapping.mappingUid = file.mapping_uid || null;
                rootNode.dirs.set(mKey, mapping);
            }

            const rel = normalizeRelPath(
                file.local_rel_path || baseName(file.remote_path)
            );
            const segments = pathSegments(rel);
            let node = mapping;

            for (let i = 0; i < segments.length - 1; i++) {
                const segment = segments[i];
                let child = node.dirs.get(segment);
                if (!child) {
                    child = createDirNode(
                        segment,
                        node.key + '/' + segment,
                        node.depth + 1,
                        node
                    );
                    node.dirs.set(segment, child);
                }
                node = child;
            }

            const name = segments.length
                ? segments[segments.length - 1]
                : baseName(file.remote_path);
            node.files.push({
                kind: 'file',
                name: name || '(sem nome)',
                relPath: rel || name,
                remotePath: String(file.remote_path || rel || ''),
                size: Number(file.size) || 0,
                encrypted: Boolean(file.encrypted),
                mappingId: file.mapping_id,
                mappingUid: file.mapping_uid || null,
                mappingName: file.mapping_name,
                parent: node,
                depth: node.depth + 1
            });
        }

        computeCounts(rootNode);
        sortTree(rootNode);
        collectAllFiles(rootNode);
        return rootNode;
    }

    function computeCounts(node) {
        let count = node.files.length;
        let size = node.files.reduce(
            (total, file) => total + file.size,
            0
        );
        for (const child of node.dirs.values()) {
            computeCounts(child);
            count += child.fileCount;
            size += child.totalSize;
        }
        node.fileCount = count;
        node.totalSize = size;
    }

    function sortTree(node) {
        const entries = Array.from(node.dirs.entries());
        if (node.depth === 0) {
            entries.sort((a, b) => {
                const aId = Number(a[1].mappingId);
                const bId = Number(b[1].mappingId);
                if (Number.isFinite(aId) && Number.isFinite(bId) && aId !== bId) {
                    return aId - bId;
                }
                return collator.compare(a[1].name, b[1].name);
            });
        } else {
            entries.sort((a, b) => collator.compare(a[1].name, b[1].name));
        }
        node.dirs = new Map(entries);
        node.files.sort((a, b) => collator.compare(a.name, b.name));
        for (const child of node.dirs.values()) {
            sortTree(child);
        }
    }

    function collectAllFiles(node) {
        const all = node.files.slice();
        for (const child of node.dirs.values()) {
            collectAllFiles(child);
            for (const file of child.allFiles) {
                all.push(file);
            }
        }
        node.allFiles = all;
        return all;
    }

    function walkDirs(node, callback) {
        for (const child of node.dirs.values()) {
            callback(child);
            walkDirs(child, callback);
        }
    }

    function walkFiles(node, callback) {
        for (const file of node.files) {
            callback(file);
        }
        for (const child of node.dirs.values()) {
            walkFiles(child, callback);
        }
    }

    function parseStoredSelection(raw) {
        if (raw === null || raw === undefined) return null;
        try {
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) return null;
            return parsed.filter(item => typeof item === 'string');
        } catch (error) {
            return null;
        }
    }

    /**
     * Resolve a seleção inicial.
     *
     * - v2 ausente e v1 ausente/vazia -> todos os arquivos;
     * - v2 existente (inclusive []) -> respeita exatamente;
     * - v1 com caminhos -> migra;
     * - JSON inválido -> todos.
     */
    function resolveInitialSelection(options) {
        const opts = options || {};
        const allPaths = Array.isArray(opts.allPaths) ? opts.allPaths : [];

        const current = parseStoredSelection(opts.v2Raw);
        if (current !== null) {
            return new Set(current);
        }

        const legacy = parseStoredSelection(opts.v1Raw);
        if (legacy !== null && legacy.length > 0) {
            return new Set(legacy);
        }

        return new Set(allPaths);
    }

    function pruneSelection(selection, allPaths) {
        const allowed = allPaths instanceof Set
            ? allPaths
            : new Set(allPaths || []);
        const result = new Set();
        for (const path of selection || []) {
            if (allowed.has(path)) result.add(path);
        }
        return result;
    }

    function selectionSummary(rootNode, selection) {
        let count = 0;
        let size = 0;
        for (const file of rootNode.allFiles || []) {
            if (selection.has(file.remotePath)) {
                count++;
                size += file.size;
            }
        }
        return {
            count: count,
            total: rootNode.fileCount,
            size: size,
            totalSize: rootNode.totalSize
        };
    }

    function folderState(node, selection) {
        let count = 0;
        const files = node.allFiles || [];
        for (const file of files) {
            if (selection.has(file.remotePath)) count++;
        }
        const total = node.fileCount || 0;
        return {
            total: total,
            count: count,
            checked: total > 0 && count === total,
            indeterminate: count > 0 && count < total
        };
    }

    function applyFolderSelection(node, selection, checked) {
        for (const file of node.allFiles || []) {
            if (checked) selection.add(file.remotePath);
            else selection.delete(file.remotePath);
        }
    }

    function applyAllSelection(rootNode, selection, checked) {
        for (const file of rootNode.allFiles || []) {
            if (checked) selection.add(file.remotePath);
            else selection.delete(file.remotePath);
        }
    }

    function invertSelection(rootNode, selection) {
        for (const file of rootNode.allFiles || []) {
            if (selection.has(file.remotePath)) selection.delete(file.remotePath);
            else selection.add(file.remotePath);
        }
    }

    function collectSelectedPaths(rootNode, selection) {
        const paths = [];
        for (const file of rootNode.allFiles || []) {
            if (selection.has(file.remotePath)) paths.push(file.remotePath);
        }
        return paths;
    }

    return {
        buildRestoreTree: buildRestoreTree,
        resolveInitialSelection: resolveInitialSelection,
        pruneSelection: pruneSelection,
        selectionSummary: selectionSummary,
        folderState: folderState,
        applyFolderSelection: applyFolderSelection,
        applyAllSelection: applyAllSelection,
        invertSelection: invertSelection,
        collectSelectedPaths: collectSelectedPaths,
        walkDirs: walkDirs,
        walkFiles: walkFiles,
        normalizeRelPath: normalizeRelPath,
        pathSegments: pathSegments,
        baseName: baseName
    };
});
