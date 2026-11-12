"""Testes das funções puras da configuração remota de mapeamentos."""

import os
import tempfile
import unittest

from backend.remote_config import (
    RemoteConfigEmpty,
    RemoteConfigInvalid,
    build_config,
    build_import_operations,
    build_import_plan,
    config_hash,
    normalize_config_path,
    parse_shortcut,
    validate_config,
)


def mapping(
    uid,
    name,
    local_path,
    remote_path,
    is_file=False,
    enabled=True,
    include_subfolders=None,
    encrypt=False,
):
    return {
        "id": abs(hash(uid)) % 100000,
        "uid": uid,
        "name": name,
        "local_path": str(local_path),
        "remote_path": remote_path,
        "is_file": is_file,
        "enabled": enabled,
        "include_subfolders": (
            not is_file if include_subfolders is None else include_subfolders
        ),
        "encrypt": encrypt,
    }


def entry(
    uid,
    name,
    remote_path,
    is_file=False,
    local_paths=None,
    encrypted=False,
):
    return {
        "uid": uid,
        "name": name,
        "remote_path": remote_path,
        "is_file": is_file,
        "enabled": True,
        "include_subfolders": not is_file,
        "encrypted": encrypted,
        "local_paths": local_paths or {},
    }


def config_for(entries):
    return {
        "schema": "terabox-auto-backup/remote-config",
        "schema_version": 1,
        "updated_at": "2026-11-12T10:00:00",
        "updated_by_machine": "m1",
        "machines": {
            "m1": {"name": "PC-1", "last_seen": "2026-11-12T10:00:00"}
        },
        "mappings": entries,
    }


class RemoteConfigPathTest(unittest.TestCase):
    def test_normaliza_caminho_padrao_e_customizado(self):
        self.assertEqual(
            normalize_config_path("config/backup.json"),
            "/config/backup.json",
        )
        self.assertEqual(
            normalize_config_path("/Config/Meu Backup.JSON"),
            "/Config/Meu Backup.JSON",
        )

    def test_rejeita_raiz_e_caminho_sem_json(self):
        for value in ("", "/", "/pasta", "config/backup.txt"):
            with self.subTest(value=value):
                with self.assertRaises(RemoteConfigInvalid):
                    normalize_config_path(value)

    def test_le_atalho_fixo(self):
        self.assertEqual(
            parse_shortcut(
                {
                    "schema": "terabox-auto-backup/remote-config-shortcut",
                    "config_path": "/config/backup.json",
                }
            ),
            "/config/backup.json",
        )
        self.assertEqual(
            parse_shortcut('{"config_path": "/outro/config.json"}'),
            "/outro/config.json",
        )


class RemoteConfigBuildTest(unittest.TestCase):
    def test_config_nova_tem_schema_e_caminho_da_maquina(self):
        config = build_config(
            [mapping("u1", "Fotos", r"C:\Fotos", "/Backup/Fotos")],
            "m1",
            "PC-1",
            now="2026-11-12T10:00:00",
        )

        self.assertEqual(config["schema"], "terabox-auto-backup/remote-config")
        self.assertEqual(config["schema_version"], 1)
        self.assertEqual(config["mappings"][0]["uid"], "u1")
        self.assertEqual(
            config["mappings"][0]["local_paths"], {"m1": r"C:\Fotos"}
        )
        self.assertEqual(config["machines"]["m1"]["name"], "PC-1")

    def test_merge_preserva_caminho_de_outra_maquina(self):
        first = build_config(
            [mapping("u1", "Fotos", r"C:\Fotos", "/Backup/Fotos")],
            "m1",
            "PC-1",
        )
        second = build_config(
            [mapping("u1", "Fotos", r"D:\Fotos", "/Backup/Fotos")],
            "m2",
            "PC-2",
            previous=first,
        )

        paths = second["mappings"][0]["local_paths"]
        self.assertEqual(paths, {"m1": r"C:\Fotos", "m2": r"D:\Fotos"})
        self.assertIn("m1", second["machines"])
        self.assertIn("m2", second["machines"])

    def test_remocao_remove_so_o_vinculo_da_maquina_atual(self):
        first = build_config(
            [mapping("u1", "Fotos", r"C:\Fotos", "/Backup/Fotos")],
            "m1",
            "PC-1",
        )
        second = build_config(
            [mapping("u1", "Fotos", r"D:\Fotos", "/Backup/Fotos")],
            "m2",
            "PC-2",
            previous=first,
        )

        removed = build_config(
            [], "m2", "PC-2", previous=second, force=True
        )
        self.assertEqual(
            removed["mappings"][0]["local_paths"], {"m1": r"C:\Fotos"}
        )

        only_m2 = config_for(
            [
                entry(
                    "u1",
                    "Fotos",
                    "/Backup/Fotos",
                    local_paths={"m2": r"D:\Fotos"},
                )
            ]
        )
        removed = build_config(
            [], "m2", "PC-2", previous=only_m2, force=True
        )
        self.assertEqual(removed["mappings"], [])

    def test_lista_vazia_nao_apaga_configuracao_sem_force(self):
        first = build_config(
            [mapping("u1", "Fotos", r"C:\Fotos", "/Backup/Fotos")],
            "m1",
            "PC-1",
        )
        with self.assertRaises(RemoteConfigEmpty):
            build_config([], "m1", "PC-1", previous=first)

    def test_valida_schema_uid_repetido_e_caminho_raiz(self):
        base = config_for([entry("u1", "a", "/A")])
        validate_config(base)

        duplicate = config_for([entry("u1", "a", "/A"), entry("u1", "b", "/B")])
        with self.assertRaises(RemoteConfigInvalid):
            validate_config(duplicate)

        root = config_for([entry("u1", "a", "/")])
        with self.assertRaises(RemoteConfigInvalid):
            validate_config(root)

        wrong_schema = dict(base)
        wrong_schema["schema"] = "outra-coisa"
        with self.assertRaises(RemoteConfigInvalid):
            validate_config(wrong_schema)

    def test_hash_ignora_campos_volateis(self):
        one = config_for([entry("u1", "a", "/A", local_paths={"m1": "C:/a"})])
        two = {
            **one,
            "updated_at": "2027-01-01T00:00:00",
            "updated_by_machine": "m2",
            "machines": {
                "m1": {"name": "PC-1", "last_seen": "2027-01-01T00:00:00"}
            },
        }

        self.assertNotEqual(config_hash(one), config_hash(two))
        self.assertEqual(
            config_hash(one, ignore_volatile=True),
            config_hash(two, ignore_volatile=True),
        )


class RemoteConfigImportPlanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_novo_mapeamento_sugere_caminho_de_outra_maquina(self):
        config = config_for(
            [
                entry(
                    "u1",
                    "Fotos",
                    "/Backup/Fotos",
                    local_paths={"m1": r"C:\Fotos"},
                )
            ]
        )
        plan = build_import_plan(config, [], "m2")

        row = plan["mappings"][0]
        self.assertEqual(plan["summary"]["new"], 1)
        self.assertEqual(row["status"], "new")
        self.assertEqual(row["local_path"], r"C:\Fotos")
        self.assertEqual(row["suggestion_source"], "other_machine")
        self.assertTrue(row["selected"])
        self.assertEqual(row["other_machines"][0]["machine_name"], "PC-1")

    def test_existente_por_uid_nao_e_selecionado_por_padrao(self):
        local_path = os.path.join(self.root, "Fotos")
        os.makedirs(local_path)
        config = config_for(
            [
                entry(
                    "u1",
                    "Fotos",
                    "/Backup/Fotos",
                    local_paths={"m1": local_path},
                )
            ]
        )
        local = [mapping("u1", "Fotos", local_path, "/Backup/Fotos")]
        plan = build_import_plan(config, local, "m1")

        row = plan["mappings"][0]
        self.assertEqual(row["status"], "existing")
        self.assertEqual(row["match_reason"], "uid")
        self.assertFalse(row["needs_update"])
        self.assertFalse(row["selected"])

    def test_existente_por_fingerprint_quando_uid_mudou(self):
        local_path = os.path.join(self.root, "Fotos")
        os.makedirs(local_path)
        config = config_for(
            [
                entry(
                    "remoto-1",
                    "Fotos",
                    "/Backup/Fotos",
                    local_paths={"m1": local_path},
                )
            ]
        )
        local = [mapping("local-antigo", "Fotos", local_path, "/Backup/Fotos")]
        plan = build_import_plan(config, local, "m1")

        row = plan["mappings"][0]
        self.assertEqual(row["status"], "existing")
        self.assertEqual(row["match_reason"], "fingerprint")

    def test_arquivo_unico_com_pai_inexistente_gera_aviso_nao_erro(self):
        target = os.path.join(self.root, "documentos", "contrato.pdf")
        config = config_for(
            [
                entry(
                    "u1",
                    "Contrato",
                    "/Backup/contrato.pdf",
                    is_file=True,
                    local_paths={"m1": target},
                )
            ]
        )
        plan = build_import_plan(config, [], "m2")

        row = plan["mappings"][0]
        self.assertIsNone(row["path_error"])
        self.assertTrue(any("pasta pai" in w.lower() for w in row["warnings"]))
        self.assertTrue(row["selected"])

    def test_pasta_no_lugar_de_arquivo_unico_gera_erro(self):
        target = os.path.join(self.root, "contrato.pdf")
        os.makedirs(target)
        config = config_for(
            [
                entry(
                    "u1",
                    "Contrato",
                    "/Backup/contrato.pdf",
                    is_file=True,
                    local_paths={"m1": target},
                )
            ]
        )
        plan = build_import_plan(config, [], "m2")

        row = plan["mappings"][0]
        self.assertIsNotNone(row["path_error"])
        self.assertFalse(row["selected"])
        self.assertEqual(plan["summary"]["with_path_error"], 1)

    def test_conflito_quando_dois_mapeamentos_usam_o_mesmo_remoto(self):
        a = os.path.join(self.root, "a")
        b = os.path.join(self.root, "b")
        os.makedirs(a)
        os.makedirs(b)
        config = config_for([entry("u1", "Fotos", "/Backup/Fotos")])
        local = [
            mapping("x1", "a", a, "/Backup/Fotos"),
            mapping("x2", "b", b, "/Backup/Fotos"),
        ]
        plan = build_import_plan(config, local, "m1")

        row = plan["mappings"][0]
        self.assertEqual(row["status"], "conflict")
        self.assertTrue(row["blocked"])
        self.assertFalse(row["selected"])

    def test_ancestral_arquivo_bloqueia_pasta_e_arquivo(self):
        blocker = os.path.join(self.root, "bloqueador")
        with open(blocker, "w", encoding="utf-8") as fh:
            fh.write("sou um arquivo")

        for is_file, target in (
            (False, os.path.join(blocker, "sub")),
            (True, os.path.join(blocker, "sub", "arquivo.txt")),
        ):
            with self.subTest(is_file=is_file):
                config = config_for(
                    [
                        entry(
                            "u1",
                            "Item",
                            "/Backup/Item" if is_file else "/Backup/Pasta",
                            is_file=is_file,
                            local_paths={"m1": target},
                        )
                    ]
                )
                plan = build_import_plan(config, [], "m2")
                row = plan["mappings"][0]
                self.assertIsNotNone(row["path_error"])
                self.assertFalse(row["selected"])

    def test_criptografia_sem_chave_gera_aviso(self):
        config = config_for(
            [
                entry(
                    "u1",
                    "Secreto",
                    "/Backup/Secreto",
                    encrypted=True,
                    local_paths={"m1": os.path.join(self.root, "Secreto")},
                )
            ]
        )
        plan = build_import_plan(
            config, [], "m2", encryption_key_available=False
        )
        self.assertTrue(
            any("chave" in w.lower() for w in plan["mappings"][0]["warnings"])
        )


class RemoteConfigOperationsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_cria_atualiza_e_ignora_sem_mudanca(self):
        folder = os.path.join(self.root, "Fotos")
        os.makedirs(folder)
        config = config_for(
            [entry("u1", "Fotos", "/Backup/Fotos", local_paths={"m1": folder})]
        )
        selection = [{"uid": "u1", "local_path": folder}]

        create = build_import_operations(config, [], selection)
        self.assertEqual(len(create["create"]), 1)
        self.assertEqual(create["create"][0]["uid"], "u1")

        local = [mapping("u1", "Fotos", folder, "/Backup/Fotos")]
        skipped = build_import_operations(config, local, selection)
        self.assertEqual(skipped["create"], [])
        self.assertEqual(skipped["update"], [])
        self.assertEqual(len(skipped["skipped"]), 1)

        other = os.path.join(self.root, "FotosNovas")
        os.makedirs(other)
        update = build_import_operations(
            config, local, [{"uid": "u1", "local_path": other}]
        )
        self.assertEqual(len(update["update"]), 1)
        self.assertEqual(update["update"][0]["local_path"], other)

    def test_nao_cria_duplicado_do_mesmo_remoto(self):
        a = os.path.join(self.root, "a")
        b = os.path.join(self.root, "b")
        os.makedirs(a)
        os.makedirs(b)
        config = config_for([entry("u1", "Fotos", "/Backup/Fotos")])
        local = [mapping("x1", "a", a, "/Backup/Fotos")]
        result = build_import_operations(
            config, local, [{"uid": "u1", "local_path": b}]
        )
        # O mapeamento existente é reconhecido por fingerprint e atualizado,
        # em vez de criar uma segunda entrada para o mesmo caminho remoto.
        self.assertEqual(result["create"], [])
        self.assertEqual(len(result["update"]), 1)
        self.assertEqual(result["update"][0]["uid"], "u1")

    def test_dois_mapeamentos_locais_iguais_geram_conflito(self):
        a = os.path.join(self.root, "a")
        b = os.path.join(self.root, "b")
        c = os.path.join(self.root, "c")
        os.makedirs(a)
        os.makedirs(b)
        os.makedirs(c)
        config = config_for([entry("u1", "Fotos", "/Backup/Fotos")])
        local = [
            mapping("x1", "a", a, "/Backup/Fotos"),
            mapping("x2", "b", b, "/Backup/Fotos"),
        ]
        result = build_import_operations(
            config, local, [{"uid": "u1", "local_path": c}]
        )
        self.assertEqual(result["create"], [])
        self.assertEqual(len(result["errors"]), 1)

    def test_importacao_de_arquivo_unico_aceita_arquivo_inexistente(self):
        target = os.path.join(self.root, "docs", "contrato.pdf")
        config = config_for(
            [entry("u1", "Contrato", "/Backup/contrato.pdf", is_file=True)]
        )
        result = build_import_operations(
            config, [], [{"uid": "u1", "local_path": target}]
        )
        self.assertEqual(len(result["create"]), 1)
        self.assertTrue(result["create"][0]["is_file"])
        self.assertEqual(result["create"][0]["include_subfolders"], False)


if __name__ == "__main__":
    unittest.main()
