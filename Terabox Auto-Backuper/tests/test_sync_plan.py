"""Testes dos helpers de caminho e do planejador de sync."""

import unittest

from backend.paths import (
    is_safe_relative_path,
    join_remote,
    normalize_remote,
    remote_parent,
    sanitize_remote_path,
    sanitize_remote_relative,
)
from backend.sync_plan import RemoteEntry, decide_action


class PathsTest(unittest.TestCase):
    def test_normaliza_barras_do_windows(self):
        self.assertEqual(
            normalize_remote("\\Backup\\Minha Pasta\\"), "/Backup/Minha Pasta"
        )
        self.assertEqual(normalize_remote("Backup//x/"), "/Backup/x")
        self.assertEqual(normalize_remote("/"), "/")

    def test_join_e_parent(self):
        self.assertEqual(
            join_remote("/Backup/Marlon", "sub/arquivo.txt"),
            "/Backup/Marlon/sub/arquivo.txt",
        )
        self.assertEqual(
            remote_parent("/Backup/Marlon/sub/arquivo.txt"),
            "/Backup/Marlon/sub",
        )
        self.assertEqual(remote_parent("/arquivo.txt"), "/")

    def test_caminho_relativo_seguro(self):
        self.assertTrue(is_safe_relative_path("pasta/arquivo.txt"))
        self.assertFalse(is_safe_relative_path("../fora.txt"))
        self.assertFalse(is_safe_relative_path("/absoluto.txt"))
        self.assertFalse(is_safe_relative_path("C:/windows/arquivo.txt"))

    def test_sanitiza_emoji_mantendo_acentos(self):
        sanitized = sanitize_remote_path("/Backup/00 - 📥 Inbox/01 - 📚 Estudos")
        self.assertNotIn("📥", sanitized)
        self.assertNotIn("📚", sanitized)
        self.assertTrue(sanitized.startswith("/Backup/00 - Inbox_"))
        self.assertIn("/01 - Estudos_", sanitized)

    def test_sanitiza_nome_de_arquivo_com_extensao(self):
        sanitized = sanitize_remote_relative("foto 📸.jpg")
        self.assertTrue(sanitized.startswith("foto_"))
        self.assertTrue(sanitized.endswith(".jpg"))

    def test_sanitizacao_e_estavel_e_sem_colisao(self):
        a = sanitize_remote_relative("📁 A")
        a2 = sanitize_remote_relative("📁 A")
        b = sanitize_remote_relative("📂 A")
        self.assertEqual(a, a2)
        self.assertNotEqual(a, b)

    def test_acentos_e_ponto_e_virgula_sao_preservados(self):
        self.assertEqual(
            sanitize_remote_path("/Backup/Ação/Realidade; Verdade"),
            "/Backup/Ação/Realidade; Verdade",
        )


class DecideActionTest(unittest.TestCase):
    def test_remoto_ausente_envia(self):
        action, _ = decide_action(10, "abc", None, None)
        self.assertEqual(action, "upload")

    def test_md5_igual_ignora(self):
        remote = RemoteEntry(path="/a", size=10, md5="ABC")
        action, reason = decide_action(10, "abc", remote, None)
        self.assertEqual(action, "skip")
        self.assertIn("MD5", reason)

    def test_md5_diferente_substitui(self):
        remote = RemoteEntry(path="/a", size=10, md5="ddd")
        action, _ = decide_action(10, "abc", remote, None)
        self.assertEqual(action, "replace")

    def test_tamanho_diferente_substitui(self):
        remote = RemoteEntry(path="/a", size=20, md5="abc")
        action, _ = decide_action(10, "abc", remote, None)
        self.assertEqual(action, "replace")

    def test_sem_md5_remoto_usa_cache_do_banco(self):
        remote = RemoteEntry(path="/a", size=10, md5=None)
        action, _ = decide_action(10, "abc", remote, {"size": 10, "md5": "abc"})
        self.assertEqual(action, "skip")

    def test_hash_multipart_confere_com_o_registrado(self):
        remote = RemoteEntry(path="/a", size=10, md5="composite")
        db_row = {
            "size": 10,
            "md5": "abc",
            "remote_md5": "composite",
        }
        action, reason = decide_action(10, "abc", remote, db_row)
        self.assertEqual(action, "skip")
        self.assertIn("multipart", reason)

    def test_hash_multipart_nao_esconde_arquivo_local_alterado(self):
        remote = RemoteEntry(path="/a", size=10, md5="composite")
        db_row = {
            "size": 10,
            "md5": "abc",
            "remote_md5": "composite",
        }
        action, _ = decide_action(10, "novo", remote, db_row)
        self.assertEqual(action, "replace")

    def test_hash_multipart_diferente_substitui(self):
        remote = RemoteEntry(path="/a", size=10, md5="outro")
        db_row = {
            "size": 10,
            "md5": "abc",
            "remote_md5": "composite",
        }
        action, _ = decide_action(10, "abc", remote, db_row)
        self.assertEqual(action, "replace")

    def test_criptografado_usa_md5_do_plaintext(self):
        remote = RemoteEntry(path="/a.enc", size=999, md5="cipher")
        action, _ = decide_action(10, "plain", remote, {"size": 10, "md5": "plain"}, True)
        self.assertEqual(action, "skip")

        action, _ = decide_action(10, "novo", remote, {"size": 10, "md5": "plain"}, True)
        self.assertEqual(action, "replace")

    def test_pasta_no_lugar_de_arquivo_e_erro(self):
        remote = RemoteEntry(path="/a", is_dir=True)
        action, _ = decide_action(10, "abc", remote, None)
        self.assertEqual(action, "error")


if __name__ == "__main__":
    unittest.main()
