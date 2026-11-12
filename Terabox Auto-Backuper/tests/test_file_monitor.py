"""Testes do alvo de vigilância do file monitor."""

import os
import tempfile
import unittest
from pathlib import Path

from backend.file_monitor import resolve_watch_target


class ResolveWatchTargetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pasta_existente_e_recursiva(self):
        folder = self.root / "pasta"
        folder.mkdir()
        self.assertEqual(resolve_watch_target(str(folder)), (str(folder), True))

    def test_arquivo_existente_vigia_pasta_pai(self):
        target = self.root / "a.txt"
        target.write_text("x", encoding="utf-8")
        self.assertEqual(
            resolve_watch_target(str(target)), (str(self.root), False)
        )

    def test_caminho_inexistente_vigia_ancestral_existente(self):
        missing = self.root / "nova" / "sub" / "nivel.dat"
        watch = resolve_watch_target(str(missing))
        self.assertIsNotNone(watch)
        self.assertTrue(os.path.isdir(watch[0]))
        self.assertTrue(
            os.path.commonpath([watch[0], str(missing)]) == watch[0]
        )

    def test_raiz_da_unidade_nao_e_recursiva(self):
        drive = os.path.splitdrive(os.path.abspath(self.root))[0] + os.sep
        watch = resolve_watch_target(drive)
        self.assertEqual(watch, (drive, False))


if __name__ == "__main__":
    unittest.main()
