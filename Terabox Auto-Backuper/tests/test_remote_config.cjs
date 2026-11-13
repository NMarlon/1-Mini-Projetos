'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const RemoteConfigUI = require('../frontend/js/remote_config.js');

test('rebase troca o prefixo preservando o restante', () => {
    assert.equal(
        RemoteConfigUI.rebasePath(
            'C:\\Users\\Marlon\\Fotos\\2024\\foto.jpg',
            'C:\\Users\\Marlon',
            'D:\\Backup'
        ),
        'D:\\Backup\\Fotos\\2024\\foto.jpg'
    );
});

test('rebase não troca pasta parecida sem fronteira', () => {
    assert.equal(
        RemoteConfigUI.rebasePath(
            'C:\\Fotos2\\arquivo.txt',
            'C:\\Fotos',
            'D:\\Fotos'
        ),
        null
    );
});

test('rebase aceita barras diferentes e maiúsculas', () => {
    assert.equal(
        RemoteConfigUI.rebasePath(
            'c:/Users/Marlon/docs/a.txt',
            'C:\\Users\\Marlon\\',
            'E:\\Documentos\\'
        ),
        'E:\\Documentos\\docs/a.txt'
    );
});

test('rebase de unidade inteira mantém a barra', () => {
    assert.equal(
        RemoteConfigUI.rebasePath('C:\\Dados\\a.txt', 'C:\\', 'D:\\'),
        'D:\\Dados\\a.txt'
    );
});

test('rebaseRows aplica somente às linhas selecionadas', () => {
    const rows = [
        { uid: 'a', local_path: 'C:\\Antigo\\a.txt' },
        { uid: 'b', local_path: 'C:\\Antigo\\b.txt' },
        { uid: 'c', local_path: 'D:\\Outro\\c.txt' }
    ];
    const updated = RemoteConfigUI.rebaseRows(
        rows,
        'C:\\Antigo',
        'E:\\Novo',
        new Set(['a', 'c'])
    );

    assert.equal(updated[0].local_path, 'E:\\Novo\\a.txt');
    assert.equal(updated[1].local_path, 'C:\\Antigo\\b.txt');
    assert.equal(updated[2].local_path, 'D:\\Outro\\c.txt');
    assert.equal(rows[0].local_path, 'C:\\Antigo\\a.txt');
});

test('defaultSelection seleciona apenas novos liberados', () => {
    const selected = RemoteConfigUI.defaultSelection([
        { uid: 'a', status: 'new', selected: true, blocked: false },
        { uid: 'b', status: 'existing', selected: false, blocked: false },
        { uid: 'c', status: 'new', selected: true, blocked: true },
        { uid: 'd', status: 'new', selected: false, blocked: false }
    ]);

    assert.deepEqual(Array.from(selected), ['a']);
});

test('selectAllUids pula conflitos e linhas com erro de caminho', () => {
    const selected = RemoteConfigUI.selectAllUids([
        { uid: 'a', blocked: false, path_error: null },
        { uid: 'b', blocked: true, path_error: null },
        { uid: 'c', blocked: false, path_error: 'caminho inválido' },
        { uid: 'd', blocked: false, path_error: null }
    ]);

    assert.deepEqual(Array.from(selected), ['a', 'd']);
});

test('selectionSummary conta novos, existentes e problemas', () => {
    const summary = RemoteConfigUI.selectionSummary(
        [
            { uid: 'a', status: 'new', blocked: false, path_error: null },
            { uid: 'b', status: 'existing', blocked: false, path_error: null },
            { uid: 'c', status: 'conflict', blocked: true, path_error: null },
            { uid: 'd', status: 'new', blocked: false, path_error: 'x' }
        ],
        new Set(['a', 'b'])
    );

    assert.deepEqual(summary, {
        total: 4,
        selected: 2,
        new: 1,
        existing: 1,
        conflicts: 1,
        blocked: 1,
        pathErrors: 1
    });
});

test('validateLocalPathHint rejeita vazio e arquivo com barra final', () => {
    assert.equal(RemoteConfigUI.validateLocalPathHint({}, ''), 'Escolha um caminho local.');
    assert.equal(
        RemoteConfigUI.validateLocalPathHint({ is_file: true }, 'C:\\a.txt\\'),
        'Para arquivo único, informe o arquivo completo.'
    );
    assert.equal(
        RemoteConfigUI.validateLocalPathHint({ is_file: true }, 'C:\\a.txt'),
        null
    );
});
