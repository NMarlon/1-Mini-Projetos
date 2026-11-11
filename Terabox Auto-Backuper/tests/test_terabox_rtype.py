"""Testes dos parâmetros rtype enviados à API do Terabox."""

import unittest
from unittest.mock import AsyncMock

from backend.terabox_client import TeraboxClient


def _fake_client(response=None):
    client = TeraboxClient.__new__(TeraboxClient)
    client.jstoken = "token"
    client._request_json = AsyncMock(return_value=(response or {"errno": 0}, ""))
    return client


class RtypeTest(unittest.IsolatedAsyncioTestCase):
    async def test_pasta_usa_rtype_zero(self):
        client = _fake_client()
        await client.create_directory("\\Backup\\Minha Pasta\\")
        _, kwargs = client._request_json.call_args
        self.assertEqual(kwargs["params"]["rtype"], "0")
        self.assertEqual(kwargs["data"]["path"], "/Backup/Minha Pasta")

    async def test_arquivo_novo_usa_rtype_zero(self):
        client = _fake_client()
        await client.create_file("/Backup/a.txt", "up", 10, '["md5"]')
        _, kwargs = client._request_json.call_args
        self.assertEqual(kwargs["params"]["rtype"], "0")
        self.assertEqual(kwargs["data"]["target_path"], "/Backup/")

    async def test_substituicao_usa_rtype_tres(self):
        client = _fake_client()
        await client.create_file("/Backup/a.txt", "up", 10, '["md5"]', overwrite=True)
        _, kwargs = client._request_json.call_args
        self.assertEqual(kwargs["params"]["rtype"], "3")

    async def test_precreate_usa_target_path_posix(self):
        client = _fake_client({"uploadid": "up", "errno": 0})
        result = await client.precreate_file("/Backup/Sub/a.txt", '["md5"]')
        self.assertTrue(result["ok"])
        _, kwargs = client._request_json.call_args
        self.assertEqual(kwargs["data"]["target_path"], "/Backup/Sub/")


if __name__ == "__main__":
    unittest.main()
