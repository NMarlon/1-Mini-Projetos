"""Testes da resolução de destino do Restaurar.

Todos os testes usam pastas temporárias. Nenhum arquivo real de backup é
tocado.
"""

import os
import tempfile
import unittest

from backend.restore import (
    RestoreTargetError,
    build_restore_plan,
    resolve_restore_mapping,
    resolve_restore_target,
)


def make_mapping(
    mapping_id,
    name,
    local_path,
    remote_path,
    is_file=False,
    enabled=True,
    uid=None,
):
    return {
        "id": mapping_id,
        "uid": uid or f"uid-{mapping_id}",
        "name": name,
        "local_path": str(local_path),
        "remote_path": remote_path,
        "is_file": is_file,
        "enabled": enabled,
        "include_subfolders": not is_file,
        "encrypt": False,
    }


def make_entry(
    local_rel_path,
    remote_path,
    mapping_id,
    mapping_name,
    size=10,
    encrypted=False,
):
    return {
        "local_rel_path": local_rel_path,
        "remote_path": remote_path,
        "mapping_id": mapping_id,
        "mapping_name": mapping_name,
        "size": size,
        "encrypted": encrypted,
    }


class RestoreTargetTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = os.path.join(self._tmp.name, "original")
        os.makedirs(self.base, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_mapeamento_de_pasta_usa_local_rel_path(self):
        mapping = make_mapping(1, "saves", self.base, "/Backup/saves")
        entry = make_entry(
            "sub/0.msav", "/Backup/saves/sub/0.msav", 1, "saves"
        )

        target, is_file = resolve_restore_target(mapping, entry)

        self.assertFalse(is_file)
        self.assertEqual(
            os.path.normcase(str(target)),
            os.path.normcase(os.path.join(self.base, "sub", "0.msav")),
        )

    def test_arquivo_inexistente_vira_create(self):
        mapping = make_mapping(1, "saves", self.base, "/Backup/saves")
        entry = make_entry("sub/0.msav", "/Backup/saves/sub/0.msav", 1, "saves")

        plan = build_restore_plan(
            ["/Backup/saves/sub/0.msav"],
            {"files": [entry]},
            [mapping],
        )

        self.assertEqual(plan.summary["create"], 1)
        self.assertEqual(plan.summary["replace"], 0)
        self.assertEqual(plan.summary["errors"], 0)
        self.assertEqual(plan.targets[0].action, "create")

    def test_arquivo_existente_vira_replace_sem_apagar(self):
        target_path = os.path.join(self.base, "sub", "0.msav")
        os.makedirs(os.path.dirname(target_path))
        with open(target_path, "w", encoding="utf-8") as fh:
            fh.write("conteudo antigo")

        mapping = make_mapping(1, "saves", self.base, "/Backup/saves")
        entry = make_entry("sub/0.msav", "/Backup/saves/sub/0.msav", 1, "saves")
        plan = build_restore_plan(
            ["/Backup/saves/sub/0.msav"],
            {"files": [entry]},
            [mapping],
        )

        self.assertEqual(plan.targets[0].action, "replace")
        self.assertTrue(plan.targets[0].exists)
        self.assertEqual(plan.summary["replace"], 1)
        with open(target_path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "conteudo antigo")

    def test_mapeamento_de_arquivo_unico_usa_o_proprio_arquivo(self):
        file_path = os.path.join(self.base, "settings.bin")
        mapping = make_mapping(
            1, "Arquivo: settings.bin", file_path, "/Backup/settings.bin",
            is_file=True,
        )
        entry = make_entry("settings.bin", "/Backup/settings.bin", 1, mapping["name"])

        target, is_file = resolve_restore_target(mapping, entry)
        self.assertTrue(is_file)
        self.assertEqual(os.path.normcase(str(target)), os.path.normcase(file_path))

        # Mesmo com o arquivo apagado, o tipo persistido continua sendo arquivo.
        plan = build_restore_plan(
            ["/Backup/settings.bin"],
            {"files": [entry]},
            [mapping],
        )
        self.assertEqual(plan.targets[0].action, "create")
        self.assertTrue(plan.targets[0].mapping_is_file)

    def test_mapeamento_de_arquivo_com_nome_diferente_e_erro(self):
        file_path = os.path.join(self.base, "settings.bin")
        mapping = make_mapping(
            1, "settings.bin", file_path, "/Backup/settings.bin", is_file=True
        )
        entry = make_entry(
            "outro.bin", "/Backup/settings.bin", 1, "settings.bin"
        )

        with self.assertRaises(RestoreTargetError) as ctx:
            resolve_restore_target(mapping, entry)
        self.assertEqual(ctx.exception.code, "file_mapping_mismatch")

    def test_pasta_no_lugar_do_arquivo_e_erro(self):
        file_path = os.path.join(self.base, "settings.bin")
        os.makedirs(file_path)
        mapping = make_mapping(
            1, "settings.bin", file_path, "/Backup/settings.bin", is_file=True
        )
        entry = make_entry(
            "settings.bin", "/Backup/settings.bin", 1, "settings.bin"
        )

        with self.assertRaises(RestoreTargetError) as ctx:
            resolve_restore_target(mapping, entry)
        self.assertEqual(ctx.exception.code, "target_is_directory")

    def test_caminho_inseguro_e_erro(self):
        mapping = make_mapping(1, "saves", self.base, "/Backup/saves")
        for rel in ("../fora.txt", "a/../../fora.txt", "/absoluto.txt"):
            with self.subTest(rel=rel):
                entry = make_entry(
                    rel, "/Backup/saves/" + rel, 1, "saves"
                )
                with self.assertRaises(RestoreTargetError) as ctx:
                    resolve_restore_target(mapping, entry)
                self.assertEqual(ctx.exception.code, "unsafe_path")

    def test_mapeamento_sem_caminho_local_gera_erro(self):
        mapping = make_mapping(1, "vazio", "", "/Backup/vazio")
        entry = make_entry("0.msav", "/Backup/vazio/0.msav", 1, "vazio")

        with self.assertRaises(RestoreTargetError) as ctx:
            resolve_restore_target(mapping, entry)
        self.assertEqual(ctx.exception.code, "invalid_mapping")

    def test_mapeamento_ausente_gera_erro(self):
        entry = make_entry("0.msav", "/Backup/saves/0.msav", 99, "saves")
        plan = build_restore_plan(
            ["/Backup/saves/0.msav"], {"files": [entry]}, []
        )

        self.assertEqual(plan.summary["errors"], 1)
        self.assertEqual(plan.summary["missing_mappings"], 1)
        self.assertEqual(plan.targets[0].error_code, "mapping_not_found")

    def test_mapeamento_desativado_ainda_restaura(self):
        mapping = make_mapping(
            1, "saves", self.base, "/Backup/saves", enabled=False
        )
        entry = make_entry("0.msav", "/Backup/saves/0.msav", 1, "saves")
        plan = build_restore_plan(
            ["/Backup/saves/0.msav"], {"files": [entry]}, [mapping]
        )

        self.assertEqual(plan.targets[0].action, "create")
        self.assertEqual(plan.summary["errors"], 0)

    def test_pasta_onde_deveria_ser_arquivo_gera_erro(self):
        os.makedirs(os.path.join(self.base, "0.msav"))
        mapping = make_mapping(1, "saves", self.base, "/Backup/saves")
        entry = make_entry("0.msav", "/Backup/saves/0.msav", 1, "saves")

        with self.assertRaises(RestoreTargetError) as ctx:
            resolve_restore_target(mapping, entry)
        self.assertEqual(ctx.exception.code, "target_is_directory")

    def test_arquivo_no_meio_do_caminho_gera_erro(self):
        with open(os.path.join(self.base, "sub"), "w", encoding="utf-8") as fh:
            fh.write("sou um arquivo")
        mapping = make_mapping(1, "saves", self.base, "/Backup/saves")
        entry = make_entry("sub/0.msav", "/Backup/saves/sub/0.msav", 1, "saves")

        with self.assertRaises(RestoreTargetError) as ctx:
            resolve_restore_target(mapping, entry)
        self.assertEqual(ctx.exception.code, "parent_is_file")

    def test_dois_arquivos_para_o_mesmo_destino_geram_erro(self):
        mapping_a = make_mapping(1, "a", self.base, "/Backup/a")
        mapping_b = make_mapping(2, "b", self.base, "/Backup/b")
        entry_a = make_entry("mesmo.txt", "/Backup/a/mesmo.txt", 1, "a")
        entry_b = make_entry("mesmo.txt", "/Backup/b/mesmo.txt", 2, "b")

        plan = build_restore_plan(
            ["/Backup/a/mesmo.txt", "/Backup/b/mesmo.txt"],
            {"files": [entry_a, entry_b]},
            [mapping_a, mapping_b],
        )

        self.assertEqual(plan.summary["duplicates"], 2)
        self.assertEqual(plan.summary["errors"], 2)
        self.assertTrue(
            all(t.error_code == "duplicate_target" for t in plan.targets)
        )

    def test_plano_nao_cria_nem_altera_arquivos(self):
        mapping = make_mapping(1, "saves", self.base, "/Backup/saves")
        entry = make_entry("sub/0.msav", "/Backup/saves/sub/0.msav", 1, "saves")

        before = list(os.walk(self.base))
        build_restore_plan(
            ["/Backup/saves/sub/0.msav"], {"files": [entry]}, [mapping]
        )
        after = list(os.walk(self.base))

        self.assertEqual(before, after)


class RestoreMappingResolutionTest(unittest.TestCase):
    def test_resolve_por_id_quando_caminho_remoto_confere(self):
        mapping = make_mapping(7, "saves", "C:/tmp/saves", "/Backup/saves")
        entry = make_entry("0.msav", "/Backup/saves/0.msav", 7, "saves")

        self.assertIs(resolve_restore_mapping(entry, [mapping]), mapping)

    def test_id_trocado_cai_para_prefixo_remoto(self):
        wrong = make_mapping(1, "outro", "C:/tmp/outro", "/Outro")
        right = make_mapping(2, "saves", "C:/tmp/saves", "/Backup/saves")
        entry = make_entry("0.msav", "/Backup/saves/0.msav", 1, "saves")

        self.assertIs(
            resolve_restore_mapping(entry, [wrong, right]),
            right,
        )

    def test_uid_resolve_mesmo_com_id_de_outro_pc(self):
        wrong = make_mapping(
            1, "outro", "C:/tmp/outro", "/Outro", uid="uid-outro"
        )
        right = make_mapping(
            2, "saves", "C:/tmp/saves", "/Backup/saves", uid="uid-saves"
        )
        entry = make_entry("0.msav", "/Backup/saves/0.msav", 1, "saves")
        entry["mapping_uid"] = "uid-saves"

        self.assertIs(
            resolve_restore_mapping(entry, [wrong, right]),
            right,
        )

    def test_uid_ausente_segue_para_prefixo(self):
        right = make_mapping(
            2, "saves", "C:/tmp/saves", "/Backup/saves", uid="uid-saves"
        )
        entry = make_entry("0.msav", "/Backup/saves/0.msav", 99, "saves")
        entry["mapping_uid"] = "uid-inexistente"

        self.assertIs(resolve_restore_mapping(entry, [right]), right)

    def test_sem_id_resolve_por_nome_unico(self):
        mapping = make_mapping(2, "saves", "C:/tmp/saves", "/Backup/saves")
        entry = make_entry("0.msav", "/Outro/saves/0.msav", 99, "saves")

        self.assertIs(resolve_restore_mapping(entry, [mapping]), mapping)

    def test_nome_ambiguo_nao_resolve(self):
        a = make_mapping(1, "saves", "C:/tmp/a", "/Backup/a")
        b = make_mapping(2, "saves", "C:/tmp/b", "/Backup/b")
        entry = make_entry("0.msav", "/Outro/saves/0.msav", 99, "saves")

        self.assertIsNone(resolve_restore_mapping(entry, [a, b]))


if __name__ == "__main__":
    unittest.main()
