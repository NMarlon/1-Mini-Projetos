"""Testes da validação/criação de caminhos locais de mapeamento."""

import os
import tempfile
import unittest
from unittest import mock

from backend import local_paths
from backend.local_paths import (
    LocalPathError,
    detect_foreign_profile,
    validate_local_mapping_path,
)


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

    def test_detecta_perfil_de_outro_usuario_e_sugere_rebase(self):
        detected = detect_foreign_profile(
            r"C:\Users\marlo\Documents\Minecraft\saves",
            current_user="Marlon",
        )

        self.assertIsNotNone(detected)
        self.assertEqual(detected["foreign_user"], "marlo")
        self.assertEqual(detected["current_user"], "Marlon")
        self.assertEqual(
            detected["suggested_path"],
            os.path.normpath(r"C:\Users\Marlon\Documents\Minecraft\saves"),
        )

    def test_nao_rebaseia_perfil_atual_nem_perfis_compartilhados(self):
        for path in (
            rf"C:\Users\{local_paths.current_windows_user()}\Documents",
            r"C:\Users\Public\Documents",
            r"C:\Users\Default\Documents",
        ):
            with self.subTest(path=path):
                self.assertIsNone(detect_foreign_profile(path))

    def test_nao_rebaseia_caminho_fora_de_users(self):
        self.assertIsNone(
            detect_foreign_profile(r"D:\Dados\Users\marlo\Fotos")
        )
        self.assertIsNone(detect_foreign_profile(r"C:\Fotos"))
        self.assertIsNone(detect_foreign_profile("pasta/relativa"))

    def test_nao_cria_pasta_no_perfil_de_outro_usuario(self):
        target = os.path.join(self.root, "perfil-errado", "Nova")

        def fake_detect(path, current_user=None):
            return {
                "foreign_user": "outro",
                "current_user": "atual",
                "foreign_root": r"C:\Users\outro",
                "current_root": r"C:\Users\atual",
                "suggested_path": os.path.join(self.root, "perfil-certo", "Nova"),
            }

        with mock.patch.object(
            local_paths, "detect_foreign_profile", side_effect=fake_detect
        ):
            with self.assertRaises(LocalPathError) as ctx:
                validate_local_mapping_path(target, False, create=True)

        self.assertIn("perfil", str(ctx.exception))
        self.assertFalse(os.path.exists(target))


if __name__ == "__main__":
    unittest.main()
