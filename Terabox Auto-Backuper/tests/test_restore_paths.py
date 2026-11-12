"""Testes dos caminhos usados pelo Restaurar."""

import unittest

from backend.paths import is_safe_relative_path


class RestoreRelativePathTest(unittest.TestCase):
    def test_is_safe_relative_path_rejeita_absolutos_e_traversal(self):
        for rel in (
            "",
            "/etc/passwd",
            r"C:\Windows\System32\arquivo.txt",
            "../arquivo.txt",
            "pasta/../../arquivo.txt",
        ):
            with self.subTest(rel=rel):
                self.assertFalse(is_safe_relative_path(rel))

    def test_is_safe_relative_path_aceita_caminho_aninhado(self):
        self.assertTrue(
            is_safe_relative_path(
                "5506831188076592432/games/com.mojang/clientId.txt"
            )
        )


if __name__ == "__main__":
    unittest.main()
