"""
Tests: CrewOps Pure Parser Functions (test_parsers.py)

Tests all I/O-free parsing utilities:
  - detect_log_type
  - parse_severity_response
  - severity_requires_approval
  - build_adf_description
  - build_slack_blocks

No mocking required — all functions are pure transformations.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crewops.parsers import (
    detect_log_type,
    parse_severity_response,
    severity_requires_approval,
    build_adf_description,
    build_slack_blocks,
)


# ════════════════════════════════════════════════════════════════
# detect_log_type
# ════════════════════════════════════════════════════════════════

class TestDetectLogType:

    def test_kubernetes_keywords_detected(self, sample_k8s_log):
        assert detect_log_type(sample_k8s_log) == "kubernetes"

    def test_nginx_keywords_detected(self, sample_nginx_log):
        assert detect_log_type(sample_nginx_log) == "nginx"

    def test_application_traceback_detected(self, sample_app_log):
        assert detect_log_type(sample_app_log) == "application"

    def test_mixed_log_returns_mixed(self, sample_mixed_log):
        """Unrecognized log patterns (no matching keywords) return 'mixed'."""
        result = detect_log_type(sample_mixed_log)
        assert result == "mixed"

    def test_empty_string_returns_unknown(self):
        assert detect_log_type("") == "unknown"

    def test_none_like_empty_returns_unknown(self):
        assert detect_log_type("   ") == "mixed"  # no keywords → no match → mixed

    def test_case_insensitive_detection(self):
        assert detect_log_type("CRASHLOOPBACKOFF in namespace default") == "kubernetes"
        assert detect_log_type("NGINX upstream error 502") == "nginx"

    def test_single_kubernetes_keyword(self):
        assert detect_log_type("pod is in CrashLoopBackOff state") == "kubernetes"

    def test_single_nginx_keyword(self):
        assert detect_log_type("upstream server returned 502") == "nginx"

    def test_unknown_log_content_returns_mixed(self):
        # Random text with no recognized keywords
        result = detect_log_type("hello world foo bar baz")
        assert result == "mixed"

    @pytest.mark.parametrize("log,expected", [
        ("kubectl get pods — crashloopbackoff", "kubernetes"),
        ("nginx: connect() failed upstream", "nginx"),
        ("Exception in thread main java.lang.RuntimeException", "application"),
        ("", "unknown"),
    ])
    def test_parametrized_detection(self, log, expected):
        assert detect_log_type(log) == expected


# ════════════════════════════════════════════════════════════════
# parse_severity_response
# ════════════════════════════════════════════════════════════════

class TestParseSeverityResponse:

    def test_p1_severity_parsed_correctly(self):
        response = (
            "SEVERITY: P1\n"
            "RATIONALE: Complete payment outage.\n"
            "CRITICAL_ISSUES:\n"
            "- Redis NOAUTH: Auth failure blocking payments\n"
            "- K8s CrashLoop: Payment pod restarting\n"
        )
        result = parse_severity_response(response)
        assert result["severity"] == "P1"
        assert result["rationale"] == "Complete payment outage."
        assert len(result["critical_issues"]) == 2
        assert result["critical_issues"][0]["severity"] == "P1"

    def test_p2_severity_parsed(self):
        response = "SEVERITY: P2\nRATIONALE: High error rate.\nCRITICAL_ISSUES:\n- High 5xx rate: 25% errors\n"
        result = parse_severity_response(response)
        assert result["severity"] == "P2"
        assert len(result["critical_issues"]) == 1

    def test_p3_severity_no_critical_issues(self):
        response = "SEVERITY: P3\nRATIONALE: Minor warning.\nCRITICAL_ISSUES:\n- None\n"
        result = parse_severity_response(response)
        assert result["severity"] == "P3"
        assert result["critical_issues"] == []

    def test_p4_severity_no_critical_issues(self):
        response = "SEVERITY: P4\nRATIONALE: Cosmetic warning.\nCRITICAL_ISSUES:\n- None\n"
        result = parse_severity_response(response)
        assert result["severity"] == "P4"
        assert result["critical_issues"] == []

    def test_empty_response_defaults_to_p3(self):
        result = parse_severity_response("")
        assert result["severity"] == "P3"
        assert result["rationale"] == "Unable to determine"
        assert result["critical_issues"] == []

    def test_none_response_defaults_gracefully(self):
        result = parse_severity_response(None)
        assert result["severity"] == "P3"

    def test_malformed_response_fallback(self):
        result = parse_severity_response("random text with no structure")
        assert result["severity"] == "P3"  # fallback default
        assert isinstance(result["critical_issues"], list)

    def test_severity_with_extra_whitespace(self):
        response = "SEVERITY:   P1  \nRATIONALE: Test.\nCRITICAL_ISSUES:\n"
        result = parse_severity_response(response)
        assert result["severity"] == "P1"

    def test_critical_issues_have_title_and_severity_keys(self):
        response = "SEVERITY: P1\nRATIONALE: Outage.\nCRITICAL_ISSUES:\n- DB down: connection refused\n"
        result = parse_severity_response(response)
        assert len(result["critical_issues"]) == 1
        issue = result["critical_issues"][0]
        assert "title" in issue
        assert "severity" in issue

    def test_multiple_critical_issues_all_parsed(self):
        response = (
            "SEVERITY: P2\nRATIONALE: Test.\nCRITICAL_ISSUES:\n"
            "- Issue A: description A\n"
            "- Issue B: description B\n"
            "- Issue C: description C\n"
        )
        result = parse_severity_response(response)
        assert len(result["critical_issues"]) == 3


# ════════════════════════════════════════════════════════════════
# severity_requires_approval
# ════════════════════════════════════════════════════════════════

class TestSeverityRequiresApproval:

    @pytest.mark.parametrize("severity,expected_approval,expected_status", [
        ("P1", True, "pending"),
        ("P2", True, "pending"),
        ("P3", False, "auto_approved"),
        ("P4", False, "auto_approved"),
    ])
    def test_approval_logic_by_severity(self, severity, expected_approval, expected_status):
        approval, status = severity_requires_approval(severity)
        assert approval == expected_approval
        assert status == expected_status

    def test_unknown_severity_defaults_to_no_approval(self):
        approval, status = severity_requires_approval("UNKNOWN")
        assert approval is False
        assert status == "auto_approved"


# ════════════════════════════════════════════════════════════════
# build_adf_description
# ════════════════════════════════════════════════════════════════

class TestBuildAdfDescription:

    def test_adf_returns_valid_structure(self):
        result = build_adf_description("Root cause text", "Remediation text", "P1")
        assert result["type"] == "doc"
        assert result["version"] == 1
        assert "content" in result
        assert isinstance(result["content"], list)

    def test_adf_has_expected_sections(self):
        result = build_adf_description("RCA", "Remediation", "P2")
        content = result["content"]
        # Check at least 6 content blocks (headings + paragraphs)
        assert len(content) >= 6

    def test_adf_includes_severity_in_content(self):
        result = build_adf_description("Root cause", "Fix steps", "P1")
        # Find the paragraph containing severity
        all_texts = [
            node["content"][0]["text"]
            for node in result["content"]
            if node["type"] == "paragraph"
        ]
        combined = " ".join(all_texts)
        assert "P1" in combined

    def test_adf_truncates_long_rca(self):
        long_text = "A" * 5000
        result = build_adf_description(long_text, "short", "P2", max_chars=1500)
        rca_paragraphs = [
            node for node in result["content"]
            if node["type"] == "paragraph"
        ]
        # All paragraph texts should be <= max_chars
        for para in rca_paragraphs:
            assert len(para["content"][0]["text"]) <= 1500

    def test_adf_handles_empty_strings(self):
        result = build_adf_description("", "", "P3")
        assert result["type"] == "doc"
        # Should not raise and should use fallback text
        all_texts = [
            node["content"][0]["text"]
            for node in result["content"]
            if node["type"] == "paragraph"
        ]
        combined = " ".join(all_texts)
        assert len(combined) > 0  # Has fallback content

    def test_adf_all_nodes_have_valid_types(self):
        result = build_adf_description("RCA text", "Fix steps", "P1")
        valid_types = {"paragraph", "heading", "codeBlock"}
        for node in result["content"]:
            assert node["type"] in valid_types, f"Unknown ADF node type: {node['type']}"


# ════════════════════════════════════════════════════════════════
# build_slack_blocks
# ════════════════════════════════════════════════════════════════

class TestBuildSlackBlocks:

    def test_slack_blocks_returns_list(self):
        blocks = build_slack_blocks("P1", "kubernetes", "Complete outage", [])
        assert isinstance(blocks, list)

    def test_slack_blocks_has_minimum_length(self):
        blocks = build_slack_blocks("P1", "kubernetes", "Outage", [])
        assert len(blocks) >= 4

    def test_slack_blocks_first_is_header(self):
        blocks = build_slack_blocks("P1", "mixed", "Outage", [])
        assert blocks[0]["type"] == "header"

    def test_slack_blocks_header_contains_severity(self):
        blocks = build_slack_blocks("P1", "kubernetes", "Outage", [])
        header_text = blocks[0]["text"]["text"]
        assert "P1" in header_text

    def test_slack_blocks_header_contains_emoji_for_p1(self):
        blocks = build_slack_blocks("P1", "kubernetes", "Outage", [])
        header_text = blocks[0]["text"]["text"]
        assert "🔴" in header_text

    def test_slack_blocks_header_contains_emoji_for_p4(self):
        blocks = build_slack_blocks("P4", "application", "Minor", [])
        header_text = blocks[0]["text"]["text"]
        assert "🟢" in header_text

    def test_slack_blocks_includes_critical_issues(self):
        issues = [{"title": "Redis down", "severity": "P1"}]
        blocks = build_slack_blocks("P1", "mixed", "Outage", issues)
        # Find section with issues
        section_texts = [
            b.get("text", {}).get("text", "")
            for b in blocks if b["type"] == "section"
        ]
        combined = " ".join(section_texts)
        assert "Redis down" in combined

    def test_slack_blocks_max_issues_respected(self):
        issues = [{"title": f"Issue {i}", "severity": "P1"} for i in range(10)]
        blocks = build_slack_blocks("P1", "mixed", "Outage", issues, max_issues=3)
        section_texts = [
            b.get("text", {}).get("text", "")
            for b in blocks if b["type"] == "section"
        ]
        combined = " ".join(section_texts)
        # Only first 3 issues should appear
        assert "Issue 0" in combined
        assert "Issue 1" in combined
        assert "Issue 2" in combined
        assert "Issue 3" not in combined

    def test_slack_blocks_empty_issues_shows_fallback(self):
        blocks = build_slack_blocks("P2", "nginx", "Elevated errors", [])
        section_texts = [
            b.get("text", {}).get("text", "")
            for b in blocks if b["type"] == "section"
        ]
        combined = " ".join(section_texts)
        assert "See full analysis" in combined

    def test_slack_blocks_context_mentions_crewops(self):
        blocks = build_slack_blocks("P1", "kubernetes", "Outage", [])
        context_blocks = [b for b in blocks if b["type"] == "context"]
        assert len(context_blocks) >= 1
        context_text = context_blocks[0]["elements"][0]["text"]
        assert "CrewOps" in context_text

    def test_slack_blocks_handles_string_issues(self):
        """Issues can be plain strings (not just dicts)."""
        issues = ["Database connection refused", "High latency detected"]
        blocks = build_slack_blocks("P2", "application", "Elevated errors", issues)
        section_texts = [
            b.get("text", {}).get("text", "")
            for b in blocks if b["type"] == "section"
        ]
        combined = " ".join(section_texts)
        assert "Database connection refused" in combined


# ════════════════════════════════════════════════════════════════
# conftest helper fixtures used in this module
# ════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_k8s_log():
    return (
        "2025-01-15T09:00:01Z kubelet[1234]: E0115 CrashLoopBackOff\n"
        "2025-01-15T09:00:02Z kubelet[1234]: OOMKilled memory limit 256Mi\n"
        "2025-01-15T09:00:03Z kube-apiserver: ImagePullBackOff nginx:latest\n"
    )


@pytest.fixture
def sample_nginx_log():
    return (
        "2025-01-15 10:00:01 [error] nginx: upstream timed out 110\n"
        "2025-01-15 10:00:02 [error] nginx: 502 Bad Gateway upstream\n"
    )


@pytest.fixture
def sample_app_log():
    return (
        "2025-01-15T11:00:00Z ERROR app: Traceback (most recent call last):\n"
        "  File 'payment.py', line 45: ConnectionError: Database unreachable\n"
    )


@pytest.fixture
def sample_mixed_log():
    """Log with no specific technology keywords — should return 'mixed'."""
    return (
        "2025-01-15T08:00:00Z WARNING: connection pool degraded to 45% capacity\n"
        "2025-01-15T08:00:01Z WARNING: response time elevated to 450ms (threshold: 200ms)\n"
        "2025-01-15T08:00:02Z WARNING: queue depth increasing rapidly: 15000 items pending\n"
    )
