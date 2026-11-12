"""Testes dos caminhos usados pelo Restaurar."""

import unittest

from backend.paths import is_safe_relative_path, resolve_restore_relative


class RestoreRelativePathTest(unittest.TestCase):
    def test_preserva_subpastas_originais(self):
        rel = "5506831188076592432/games/com.mojang/minecraftpe/clientId.txt"
        self.assertEqual(resolve_restore_relative(rel, True), rel)

    def test_sem_preservar_usa_apenas_o_nome(self):
        rel = "pasta/subpasta/arquivo.txt"
        self.assertEqual(resolve_restore_relative(rel, False), "arquivo.txt")

    def test_normaliza_barras_do_windows(self):
        rel = r"pasta\subpasta\arquivo.txt"
        self.assertEqual(
            resolve_restore_relative(rel, True),
            "pasta/subpasta/arquivo.txt",
        )

    def test_caminhos_inseguros_viram_apenas_o_nome(self):
        cases = (
            ("../arquivo.txt", "arquivo.txt"),
            ("pasta/../../arquivo.txt", "arquivo.txt"),
            ("/etc/passwd", "passwd"),
            (r"C:\Windows\System32\arquivo.txt", "arquivo.txt"),
            ("C:/Windows/System32/arquivo.txt", "arquivo.txt"),
        )
        for rel, expected in cases:
            with self.subTest(rel=rel):
                self.assertEqual(
                    resolve_restore_relative(rel, True),
                    expected,
                )

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

    def test_estrutura_aninhada_mantem_componentes(self):
        rel = "a/b/c/d.txt"
        result = resolve_restore_relative(rel, True)
        self.assertEqual(result.split("/"), ["a", "b", "c", "d.txt"])

    def test_nunca_devolve_componente_especial(self):
        for rel in ("..", "a/..", ".", "", "a/."):
            with self.subTest(rel=rel):
                self.assertEqual(
                    resolve_restore_relative(rel, True),
                    "arquivo_restaurado",
                )


if __name__ == "__main__":
    unittest.main()
