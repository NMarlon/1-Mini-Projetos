"""Testes da mesclagem do manifesto global."""

import json
import unittest

from backend.manifest import (
    ManifestReadError,
    download_manifest,
    merge_manifest,
)


def file_entry(uid, remote, rel="a.txt", **extra):
    data = {
        "mapping_uid": uid,
        "mapping_name": uid,
        "local_rel_path": rel,
        "remote_path": remote,
        "size": 1,
        "md5": "0" * 32,
        "encrypted": False,
    }
    data.update(extra)
    return data


class ManifestMergeTest(unittest.TestCase):
    def test_preserva_entradas_de_outro_computador(self):
        existing = {
            "files": [
                file_entry("uid-local", "/Backup/local/a.txt"),
                file_entry("uid-outro", "/Backup/outro/b.txt"),
            ]
        }
        merged = merge_manifest(
            existing,
            [file_entry("uid-local", "/Backup/local/a.txt")],
            [],
            {"uid-local"},
            machine_id="pc-1",
            machine_name="PC 1",
        )

        paths = [entry["remote_path"] for entry in merged["files"]]
        self.assertIn("/Backup/local/a.txt", paths)
        self.assertIn("/Backup/outro/b.txt", paths)
        self.assertEqual(merged["version"], "2.1")
        self.assertEqual(merged["machine_id"], "pc-1")
        self.assertEqual(len(merged["files"]), 2)

    def test_remove_fantasmas_do_mapeamento_local(self):
        existing = {
            "files": [
                file_entry("uid-local", "/Backup/local/antigo.txt"),
                file_entry("uid-local", "/Backup/local/novo.txt"),
            ]
        }
        merged = merge_manifest(
            existing,
            [file_entry("uid-local", "/Backup/local/novo.txt")],
            [],
            {"uid-local"},
        )

        paths = [entry["remote_path"] for entry in merged["files"]]
        self.assertEqual(paths, ["/Backup/local/novo.txt"])

    def test_preserva_mapeamento_local_nao_verificado(self):
        existing = {
            "files": [
                file_entry("uid-local", "/Backup/local/a.txt"),
            ]
        }
        merged = merge_manifest(
            existing,
            [],
            [],
            {"uid-local"},
            preserve_local_uids={"uid-local"},
        )

        self.assertEqual(len(merged["files"]), 1)
        self.assertEqual(
            merged["files"][0]["remote_path"], "/Backup/local/a.txt"
        )

    def test_deduplica_por_caminho_remoto_sem_diferenciar_maiusculas(self):
        existing = {
            "files": [
                file_entry("uid-outro", "/Backup/Outro/A.TXT"),
            ]
        }
        merged = merge_manifest(
            existing,
            [file_entry("uid-local", "/backup/outro/a.txt")],
            [],
            {"uid-local"},
        )

        self.assertEqual(len(merged["files"]), 1)
        self.assertEqual(merged["files"][0]["mapping_uid"], "uid-local")

    def test_remove_uid_desconhecido_quando_lista_global_e_informada(self):
        existing = {
            "files": [
                file_entry("uid-valido", "/Backup/valido/a.txt"),
                file_entry("uid-apagado", "/Backup/apagado/a.txt"),
            ]
        }
        merged = merge_manifest(
            existing,
            [],
            [],
            {"uid-local"},
            known_mapping_uids={"uid-local", "uid-valido"},
        )

        self.assertEqual(len(merged["files"]), 1)
        self.assertEqual(
            merged["files"][0]["remote_path"], "/Backup/valido/a.txt"
        )

    def test_manifesto_inexistente_ou_corrompido_nao_quebra(self):
        for existing in (None, {}, {"files": "invalido"}, {"files": [None]}):
            merged = merge_manifest(
                existing,
                [file_entry("uid-local", "/Backup/local/a.txt")],
                [],
                {"uid-local"},
            )
            self.assertEqual(len(merged["files"]), 1)

    def test_mescla_diretorios_e_preserva_de_outro_pc(self):
        existing = {
            "directories": [
                {"mapping_uid": "uid-outro", "remote_path": "/Backup/outro"},
            ]
        }
        merged = merge_manifest(
            existing,
            [],
            [
                {
                    "mapping_uid": "uid-local",
                    "remote_path": "/Backup/local",
                }
            ],
            {"uid-local"},
        )

        paths = [entry["remote_path"] for entry in merged["directories"]]
        self.assertEqual(paths, ["/Backup/local", "/Backup/outro"])

    def test_preserva_diretorio_local_quando_rebuild_nao_informa_pastas(self):
        existing = {
            "directories": [
                {"mapping_uid": "uid-local", "remote_path": "/Backup/local"},
            ]
        }
        merged = merge_manifest(existing, [], [], {"uid-local"})

        self.assertEqual(
            [entry["remote_path"] for entry in merged["directories"]],
            ["/Backup/local"],
        )


class FakeManifestClient:
    def __init__(self, exists=True, download_ok=True, payload=None):
        self.exists = exists
        self.download_ok = download_ok
        self.payload = payload

    async def find_remote_file(self, path):
        if not self.exists:
            return None

        class Entry:
            is_dir = False

        return Entry()

    async def download_file(self, path, local_path):
        if not self.download_ok:
            return False
        content = (
            self.payload
            if isinstance(self.payload, str)
            else json.dumps(self.payload)
        )
        with open(local_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return True


class ManifestDownloadTest(unittest.IsolatedAsyncioTestCase):
    async def test_manifesto_inexistente_retorna_none(self):
        client = FakeManifestClient(exists=False)
        self.assertIsNone(await download_manifest(client, strict=True))

    async def test_falha_de_download_com_manifesto_existente_levanta(self):
        client = FakeManifestClient(exists=True, download_ok=False)
        with self.assertRaises(ManifestReadError):
            await download_manifest(client, strict=True)
        self.assertIsNone(await download_manifest(client, strict=False))

    async def test_json_invalido_levanta_no_modo_estrito(self):
        client = FakeManifestClient(payload="{invalido")
        with self.assertRaises(ManifestReadError):
            await download_manifest(client, strict=True)
        self.assertIsNone(await download_manifest(client, strict=False))

    async def test_manifesto_valido_e_lido(self):
        client = FakeManifestClient(payload={"files": [], "version": "2.1"})
        data = await download_manifest(client, strict=True)
        self.assertEqual(data["version"], "2.1")


if __name__ == "__main__":
    unittest.main()
