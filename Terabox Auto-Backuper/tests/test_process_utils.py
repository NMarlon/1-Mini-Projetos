"""Testes para execução silenciosa de subprocessos."""

import subprocess
import unittest
from unittest.mock import patch

from backend import process_utils


class ProcessUtilsTest(unittest.TestCase):
    @unittest.skipUnless(process_utils.IS_WINDOWS, "Teste específico do Windows")
    def test_hidden_kwargs_aplica_create_no_window(self):
        kwargs = process_utils.hidden_kwargs({})
        self.assertTrue(kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW)
        self.assertIn("startupinfo", kwargs)
        self.assertTrue(
            kwargs["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW
        )
        self.assertEqual(kwargs["startupinfo"].wShowWindow, subprocess.SW_HIDE)

    @unittest.skipUnless(process_utils.IS_WINDOWS, "Teste específico do Windows")
    def test_hidden_kwargs_preserva_flags_existentes(self):
        kwargs = process_utils.hidden_kwargs({"creationflags": 0x00000008})
        self.assertTrue(kwargs["creationflags"] & 0x00000008)
        self.assertTrue(kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW)

    @unittest.skipUnless(process_utils.IS_WINDOWS, "Teste específico do Windows")
    def test_run_hidden_repassa_flags_ao_subprocess(self):
        with patch("backend.process_utils.subprocess.run") as mock_run:
            process_utils.run_hidden(
                ["cmd", "/c", "echo", "ok"], capture_output=True, text=True
            )

        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        self.assertTrue(kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW)
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["text"])
        self.assertIn("startupinfo", kwargs)


if __name__ == "__main__":
    unittest.main()
