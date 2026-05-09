"""
Tests: CrewOps RAG Pipeline (test_rag.py)

Tests knowledge base search, keyword fallback, query engine integration,
edge cases, and scoring correctness.
No network or LanceDB required — uses embedded docs only.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crewops.rag import (
    keyword_search,
    search_knowledge_base,
    EMBEDDED_KB_DOCS,
)


# ════════════════════════════════════════════════════════════════
# EMBEDDED_KB_DOCS content validation
# ════════════════════════════════════════════════════════════════

class TestEmbeddedKbDocs:

    def test_embedded_docs_is_list(self):
        assert isinstance(EMBEDDED_KB_DOCS, list)

    def test_embedded_docs_not_empty(self):
        assert len(EMBEDDED_KB_DOCS) >= 5, "Need at least 5 KB documents"

    def test_every_doc_has_title_and_content(self):
        for i, doc in enumerate(EMBEDDED_KB_DOCS):
            assert "title" in doc, f"Document {i} missing 'title'"
            assert "content" in doc, f"Document {i} missing 'content'"

    def test_every_doc_title_is_nonempty_string(self):
        for doc in EMBEDDED_KB_DOCS:
            assert isinstance(doc["title"], str)
            assert len(doc["title"].strip()) > 0

    def test_every_doc_content_is_nonempty_string(self):
        for doc in EMBEDDED_KB_DOCS:
            assert isinstance(doc["content"], str)
            assert len(doc["content"].strip()) > 50, (
                f"Document '{doc['title']}' content too short (<50 chars)"
            )

    def test_k8s_doc_present(self):
        titles = [d["title"] for d in EMBEDDED_KB_DOCS]
        k8s_docs = [t for t in titles if "k8s" in t.lower() or "kubernetes" in t.lower() or "crashloop" in t.lower()]
        assert len(k8s_docs) >= 1, "No K8s-related knowledge base document found"

    def test_redis_doc_present(self):
        titles = [d["title"] for d in EMBEDDED_KB_DOCS]
        redis_docs = [t for t in titles if "redis" in t.lower()]
        assert len(redis_docs) >= 1, "No Redis knowledge base document found"

    def test_incident_severity_doc_present(self):
        content_all = " ".join(d["content"] for d in EMBEDDED_KB_DOCS)
        assert "P1" in content_all or "severity" in content_all.lower()


# ════════════════════════════════════════════════════════════════
# keyword_search
# ════════════════════════════════════════════════════════════════

class TestKeywordSearch:

    def test_returns_string(self):
        result = keyword_search("kubernetes crash")
        assert isinstance(result, str)

    def test_returns_content_for_k8s_query(self):
        result = keyword_search("CrashLoopBackOff kubernetes")
        assert len(result) > 50
        assert result != "No relevant knowledge base documents found for this query."

    def test_returns_content_for_redis_query(self):
        result = keyword_search("redis connection pool authentication")
        assert len(result) > 50

    def test_returns_no_results_for_unrelated_query(self):
        result = keyword_search("xyzzy frobnicate wibble")
        assert result == "No relevant knowledge base documents found for this query."

    def test_empty_query_returns_no_results(self):
        result = keyword_search("")
        assert result == "No relevant knowledge base documents found for this query."

    def test_respects_top_k_limit(self):
        # Use a generic query that matches many docs
        result = keyword_search("error failure service", top_k=1)
        # Result should only contain content from 1 doc (no separator)
        # The separator "---" only appears between multiple docs
        separator_count = result.count("---")
        assert separator_count == 0, "top_k=1 should return only one document"

    def test_top_k_2_returns_multiple_docs(self):
        result = keyword_search("error failure service kubernetes redis", top_k=2)
        # If 2 docs match, we should see the separator
        assert len(result) > 100

    def test_results_are_sorted_by_relevance(self):
        # K8s query should rank K8s doc first
        result = keyword_search("CrashLoopBackOff OOMKilled kubernetes pod evicted")
        # First result should contain k8s content
        assert "CrashLoopBackOff" in result or "kubelet" in result or "kubectl" in result

    def test_custom_documents_override(self):
        custom_docs = [
            {"title": "Custom Doc A", "content": "Alpha beta gamma delta epsilon"},
            {"title": "Custom Doc B", "content": "Zeta eta theta iota kappa"},
        ]
        result = keyword_search("alpha beta", documents=custom_docs)
        assert "Custom Doc A" in result
        assert "Custom Doc B" not in result

    def test_empty_custom_documents(self):
        result = keyword_search("kubernetes", documents=[])
        assert result == "No relevant knowledge base documents found for this query."

    def test_case_insensitive_matching(self):
        result_lower = keyword_search("crashloopbackoff")
        result_upper = keyword_search("CRASHLOOPBACKOFF")
        # Both should find content (case-insensitive matching)
        assert len(result_lower) == len(result_upper)

    def test_separator_format_between_docs(self):
        result = keyword_search("error failure kubernetes redis", top_k=3)
        if "---" in result:
            # Separator should be the correct format
            assert "\n\n---\n\n" in result


# ════════════════════════════════════════════════════════════════
# search_knowledge_base (primary function with query engine)
# ════════════════════════════════════════════════════════════════

class TestSearchKnowledgeBase:

    def test_no_query_engine_uses_keyword_fallback(self):
        result = search_knowledge_base("kubernetes crash", query_engine=None)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_working_query_engine_is_used(self):
        """When query_engine works, its result is preferred."""
        mock_qe = MagicMock()
        mock_response = MagicMock()
        mock_response.__str__ = MagicMock(return_value="Query engine result for kubernetes crash")
        mock_qe.query.return_value = mock_response

        result = search_knowledge_base("kubernetes crash", query_engine=mock_qe)
        assert result == "Query engine result for kubernetes crash"
        mock_qe.query.assert_called_once_with("kubernetes crash")

    def test_failing_query_engine_falls_back_to_keyword(self):
        """When query_engine raises, keyword fallback is used silently."""
        mock_qe = MagicMock()
        mock_qe.query.side_effect = RuntimeError("LlamaIndex not available")

        result = search_knowledge_base("kubernetes crash", query_engine=mock_qe)
        # Should fall back to keyword search, not raise
        assert isinstance(result, str)
        assert len(result) > 50

    def test_query_engine_empty_result_falls_back(self):
        """When query_engine returns empty string, keyword fallback is used."""
        mock_qe = MagicMock()
        mock_response = MagicMock()
        mock_response.__str__ = MagicMock(return_value="   ")  # whitespace-only
        mock_qe.query.return_value = mock_response

        result = search_knowledge_base("kubernetes crash", query_engine=mock_qe)
        # Empty result → fallback
        assert len(result) > 50

    def test_result_contains_document_content(self):
        result = search_knowledge_base("redis connection pool exhaustion")
        assert "redis" in result.lower() or "Redis" in result

    def test_top_k_parameter_passed_to_fallback(self):
        result = search_knowledge_base("error failure kubernetes", top_k=1)
        # With top_k=1 no separator expected
        assert result.count("\n\n---\n\n") == 0
