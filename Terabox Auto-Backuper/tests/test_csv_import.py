"""Testes da importação de lista CSV."""

import os
import tempfile
import unittest
from pathlib import Path

from backend.csv_import import parse_mapping_csv


class CsvImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.file = self.root / "arquivo.txt"
        self.file.write_text("conteudo", encoding="utf-8")
        self.folder = self.root / "pasta"
        self.folder.mkdir()
        (self.folder / "sub").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_aceita_ponto_e_virgula(self):
        text = f"{self.folder}; /Backup/Pasta\n{self.file}; /Backup/Arquivos"
        entries, errors = parse_mapping_csv(text)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 2)
        self.assertFalse(entries[0].source_is_file)
        self.assertTrue(entries[1].source_is_file)
        self.assertEqual(entries[0].destination, "/Backup/Pasta")
        self.assertEqual(entries[1].destination, "/Backup/Arquivos")

    def test_ignora_vazias_e_comentarios(self):
        text = f"\n# comentario\n{self.folder}; /Backup/Pasta\n\n"
        entries, errors = parse_mapping_csv(text)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 1)

    def test_reports_origem_inexistente(self):
        text = f"{self.root / 'nao_existe'}; /Backup/Pasta"
        entries, errors = parse_mapping_csv(text)
        self.assertEqual(entries, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("não encontrada", errors[0]["error"])

    def test_reports_destino_raiz(self):
        text = f"{self.folder}; /"
        entries, errors = parse_mapping_csv(text)
        self.assertEqual(entries, [])
        self.assertEqual(len(errors), 1)

    def test_reports_duplicado_na_lista(self):
        text = f"{self.folder}; /Backup/Pasta\n{self.folder}; /Backup/Pasta"
        entries, errors = parse_mapping_csv(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("duplicado", errors[0]["error"])

    def test_ignora_cabecalho(self):
        text = f"origem; destino\n{self.folder}; /Backup/Pasta"
        entries, errors = parse_mapping_csv(text)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 1)

    def test_aceita_origem_entre_aspas_com_ponto_e_virgula(self):
        weird = self.root / "a;b.txt"
        weird.write_text("x", encoding="utf-8")
        text = f'"{weird}"; /Backup/Pasta'
        entries, errors = parse_mapping_csv(text)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].source, str(weird))


if __name__ == "__main__":
    unittest.main()
