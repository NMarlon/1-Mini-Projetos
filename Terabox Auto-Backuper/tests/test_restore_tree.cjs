'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const RestoreTree = require('../frontend/js/restore_tree.js');

const FILES = [
    {
        mapping_id: 1,
        mapping_name: 'saves',
        local_rel_path: '0.msav',
        remote_path: '/r/saves/0.msav',
        size: 100
    },
    {
        mapping_id: 1,
        mapping_name: 'saves',
        local_rel_path: 'sub/a.msav',
        remote_path: '/r/saves/sub/a.msav',
        size: 200
    },
    {
        mapping_id: 2,
        mapping_name: 'files',
        local_rel_path: 'e/00/hash1',
        remote_path: '/r/files/e/00/hash1',
        size: 300
    },
    {
        mapping_id: 2,
        mapping_name: 'files',
        local_rel_path: 'e/01/hash2',
        remote_path: '/r/files/e/01/hash2',
        size: 400
    },
    {
        mapping_id: 3,
        mapping_name: 'Arquivo: settings.bin',
        local_rel_path: 'settings.bin',
        remote_path: '/r/settings.bin',
        size: 50
    }
];

test('agrupa por mapeamento e preserva a hierarquia de pastas', () => {
    const root = RestoreTree.buildRestoreTree(FILES);

    assert.equal(root.fileCount, 5);
    assert.equal(root.totalSize, 1050);
    assert.equal(root.dirs.size, 3);
    assert.equal(root.allFiles.length, 5);

    const saves = root.dirs.get('mapping:1');
    assert.ok(saves);
    assert.equal(saves.name, 'saves');
    assert.equal(saves.fileCount, 2);
    assert.equal(saves.dirs.get('sub').fileCount, 1);

    const files = root.dirs.get('mapping:2');
    assert.ok(files);
    assert.equal(files.fileCount, 2);
    assert.equal(files.dirs.get('e').dirs.get('00').fileCount, 1);
    assert.equal(files.dirs.get('e').dirs.get('01').fileCount, 1);
});

test('todos os arquivos são selecionados quando não há seleção salva', () => {
    const allPaths = FILES.map(file => file.remote_path);
    const selected = RestoreTree.resolveInitialSelection({
        v2Raw: null,
        v1Raw: null,
        allPaths
    });

    assert.deepEqual(Array.from(selected), allPaths);
});

test('seleção vazia da v2 é explícita e permanece vazia', () => {
    const allPaths = FILES.map(file => file.remote_path);
    const selected = RestoreTree.resolveInitialSelection({
        v2Raw: '[]',
        v1Raw: null,
        allPaths
    });

    assert.equal(selected.size, 0);
});

test('seleção vazia da v1 é tratada como lixo do bug e seleciona tudo', () => {
    const allPaths = FILES.map(file => file.remote_path);
    const selected = RestoreTree.resolveInitialSelection({
        v2Raw: null,
        v1Raw: '[]',
        allPaths
    });

    assert.deepEqual(Array.from(selected), allPaths);
});

test('seleção não vazia da v1 é migrada', () => {
    const allPaths = FILES.map(file => file.remote_path);
    const selected = RestoreTree.resolveInitialSelection({
        v2Raw: null,
        v1Raw: JSON.stringify(['/r/saves/0.msav']),
        allPaths
    });

    assert.deepEqual(Array.from(selected), ['/r/saves/0.msav']);
});

test('JSON inválido volta para todos os arquivos', () => {
    const allPaths = FILES.map(file => file.remote_path);
    const selected = RestoreTree.resolveInitialSelection({
        v2Raw: 'não é json',
        v1Raw: null,
        allPaths
    });

    assert.deepEqual(Array.from(selected), allPaths);
});

test('poda caminhos que não existem mais no manifesto', () => {
    const selected = RestoreTree.pruneSelection(
        new Set(['/r/saves/0.msav', '/r/antigo.txt']),
        ['/r/saves/0.msav', '/r/saves/sub/a.msav']
    );

    assert.deepEqual(Array.from(selected), ['/r/saves/0.msav']);
});

test('checkbox de pasta seleciona e desmarca toda a subárvore', () => {
    const root = RestoreTree.buildRestoreTree(FILES);
    const saves = root.dirs.get('mapping:1');
    const selected = new Set();

    let state = RestoreTree.folderState(saves, selected);
    assert.deepEqual(state, {
        total: 2,
        count: 0,
        checked: false,
        indeterminate: false
    });

    RestoreTree.applyFolderSelection(saves, selected, true);
    assert.equal(selected.size, 2);
    state = RestoreTree.folderState(saves, selected);
    assert.equal(state.checked, true);
    assert.equal(state.indeterminate, false);

    selected.delete('/r/saves/0.msav');
    state = RestoreTree.folderState(saves, selected);
    assert.equal(state.checked, false);
    assert.equal(state.indeterminate, true);

    RestoreTree.applyFolderSelection(saves, selected, false);
    assert.equal(selected.size, 0);
});

test('selecionar todos, inverter e coletar caminhos', () => {
    const root = RestoreTree.buildRestoreTree(FILES);
    const selected = new Set();

    RestoreTree.applyAllSelection(root, selected, true);
    assert.equal(selected.size, 5);
    assert.deepEqual(RestoreTree.collectSelectedPaths(root, selected), [
        '/r/saves/0.msav',
        '/r/saves/sub/a.msav',
        '/r/files/e/00/hash1',
        '/r/files/e/01/hash2',
        '/r/settings.bin'
    ]);

    RestoreTree.invertSelection(root, selected);
    assert.equal(selected.size, 0);

    selected.add('/r/saves/0.msav');
    const summary = RestoreTree.selectionSummary(root, selected);
    assert.deepEqual(summary, {
        count: 1,
        total: 5,
        size: 100,
        totalSize: 1050
    });
});

test('normaliza barras do Windows e nomes sem mapping_id', () => {
    const root = RestoreTree.buildRestoreTree([{
        mapping_name: 'sem id',
        local_rel_path: 'a\\b\\c.txt',
        remote_path: '/r/c.txt',
        size: 10
    }]);

    const mapping = root.dirs.get('mapping-name:sem id');
    assert.ok(mapping);
    assert.equal(mapping.dirs.get('a').dirs.get('b').fileCount, 1);
    assert.equal(RestoreTree.normalizeRelPath('\\a\\b\\c.txt\\'), 'a/b/c.txt');
});
