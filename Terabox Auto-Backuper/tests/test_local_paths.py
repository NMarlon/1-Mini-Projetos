"""Testes da validação/criação de caminhos locais de mapeamento."""

import os
import tempfile
import unittest

from backend.local_paths import LocalPathError, validate_local_mapping_path


class LocalPathsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_aceita_pasta_inexistente_e_cria(self):
        target = os.path.join(self.root, "nova", "sub")
        result = validate_local_mapping_path(target, False, create=True)
        self.assertFalse(result.is_file)
        self.assertTrue(os.path.isdir(target))
        self.assertTrue(result.warnings)

    def test_arquivo_inexistente_cria_so_pasta_pai(self):
        target = os.path.join(self.root, "saves", "level.dat")
        result = validate_local_mapping_path(target, True, create=True)
        self.assertTrue(result.is_file)
        self.assertTrue(os.path.isdir(os.path.dirname(target)))
        self.assertFalse(os.path.exists(target))

    def test_tipo_automatico_usa_filesystem(self):
        folder = os.path.join(self.root, "pasta")
        os.makedirs(folder)
        self.assertFalse(validate_local_mapping_path(folder).is_file)

        file_path = os.path.join(self.root, "a.txt")
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write("x")
        self.assertTrue(validate_local_mapping_path(file_path).is_file)

    def test_rejeita_relativo_raiz_e_conflito_de_tipo(self):
        with self.assertRaises(LocalPathError):
            validate_local_mapping_path("pasta/relativa")

        with self.assertRaises(LocalPathError):
            validate_local_mapping_path("C:\\")

        folder = os.path.join(self.root, "pasta")
        os.makedirs(folder)
        with self.assertRaises(LocalPathError):
            validate_local_mapping_path(folder, True)

        file_path = os.path.join(self.root, "a.txt")
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write("x")
        with self.assertRaises(LocalPathError):
            validate_local_mapping_path(file_path, False)

    def test_ancestral_arquivo_bloqueia(self):
        blocker = os.path.join(self.root, "bloqueador")
        with open(blocker, "w", encoding="utf-8") as fh:
            fh.write("x")

        for is_file, target in (
            (False, os.path.join(blocker, "sub")),
            (True, os.path.join(blocker, "sub", "a.txt")),
        ):
            with self.subTest(is_file=is_file):
                with self.assertRaises(LocalPathError):
                    validate_local_mapping_path(target, is_file, create=True)


if __name__ == "__main__":
    unittest.main()
