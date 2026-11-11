"""Testes da seleção de mapeamentos usada pelo sync manual e Auto-sync."""

import unittest
from unittest.mock import AsyncMock, patch

from backend.sync_engine import SyncEngine


class GetMappingsTest(unittest.IsolatedAsyncioTestCase):
    async def test_none_retorna_todos_habilitados(self):
        engine = SyncEngine()
        with patch(
            "backend.sync_engine.database.fetch_all",
            new=AsyncMock(return_value=[{"id": 1}]),
        ) as fetch:
            result = await engine._get_mappings(None)

        self.assertEqual(result, [{"id": 1}])
        query = fetch.await_args.args[0]
        params = fetch.await_args.args[1] if len(fetch.await_args.args) > 1 else ()
        self.assertIn("enabled = 1", query)
        self.assertEqual(params, ())

    async def test_lista_vazia_nao_sincroniza_tudo(self):
        engine = SyncEngine()
        with patch(
            "backend.sync_engine.database.fetch_all", new=AsyncMock()
        ) as fetch:
            result = await engine._get_mappings([])

        self.assertEqual(result, [])
        fetch.assert_not_awaited()

    async def test_ids_explicitos_filtram_por_habilitados(self):
        engine = SyncEngine()
        with patch(
            "backend.sync_engine.database.fetch_all",
            new=AsyncMock(return_value=[]),
        ) as fetch:
            await engine._get_mappings([3, 5])

        query, params = fetch.await_args.args
        self.assertIn("id IN (?,?)", query)
        self.assertIn("enabled = 1", query)
        self.assertEqual(params, (3, 5))


if __name__ == "__main__":
    unittest.main()
