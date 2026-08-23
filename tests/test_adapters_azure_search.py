from __future__ import annotations

import unittest

from fabric_qa.adapters.azure_search import AzureSearchKnowledgeBasePort


class FakeSearchDocumentsClient:
    def __init__(self, results: list[dict] | None = None) -> None:
        self._results = results if results is not None else []
        self.search_calls: list[tuple[str | None, str, list[str]]] = []

    def search(self, *, search_text, filter, order_by):
        self.search_calls.append((search_text, filter, order_by))
        return iter(self._results)


class TestAzureSearchKnowledgeBasePort(unittest.TestCase):
    def test_retrieve_filters_by_asset_model(self) -> None:
        client = FakeSearchDocumentsClient(results=[{"content": "guidance text", "chunk_index": 0}])
        port = AzureSearchKnowledgeBasePort(client)

        port.retrieve("CFM56-7B26")

        self.assertEqual(len(client.search_calls), 1)
        _search_text, filter_expr, _order_by = client.search_calls[0]
        self.assertEqual(filter_expr, "asset_model eq 'CFM56-7B26'")

    def test_retrieve_returns_the_single_chunk_content(self) -> None:
        client = FakeSearchDocumentsClient(results=[{"content": "EGT margin guidance", "chunk_index": 0}])
        port = AzureSearchKnowledgeBasePort(client)

        result = port.retrieve("CFM56-7B26")

        self.assertEqual(result, "EGT margin guidance")

    def test_retrieve_concatenates_multiple_chunks_in_order(self) -> None:
        client = FakeSearchDocumentsClient(
            results=[
                {"content": "second chunk", "chunk_index": 1},
                {"content": "first chunk", "chunk_index": 0},
            ]
        )
        port = AzureSearchKnowledgeBasePort(client)

        result = port.retrieve("GEnx-1B")

        self.assertEqual(result, "first chunk\n\nsecond chunk")

    def test_retrieve_raises_when_no_guidance_is_indexed_for_the_model(self) -> None:
        client = FakeSearchDocumentsClient(results=[])
        port = AzureSearchKnowledgeBasePort(client)

        with self.assertRaises(ValueError):
            port.retrieve("unknown-model")

    def test_retrieve_escapes_single_quotes_in_the_odata_filter(self) -> None:
        client = FakeSearchDocumentsClient(results=[{"content": "x", "chunk_index": 0}])
        port = AzureSearchKnowledgeBasePort(client)

        port.retrieve("weird'model")

        _search_text, filter_expr, _order_by = client.search_calls[0]
        self.assertEqual(filter_expr, "asset_model eq 'weird''model'")


if __name__ == "__main__":
    unittest.main()
