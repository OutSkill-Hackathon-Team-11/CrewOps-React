"""
Tests: CrewOps State Schema (test_state.py)

Validates the TypedDict schema structure, field presence,
reducer field identification, and that state initialises correctly.
No LLMs, no network, no mocking required.
"""
import sys
import os
import pytest
from typing import get_type_hints, get_args, get_origin, Annotated

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crewops.state import (
    CrewOpsState,
    REQUIRED_INPUT_FIELDS,
    ALL_STATE_FIELDS,
    LIST_FIELDS_WITH_REDUCERS,
    DICT_FIELDS_WITH_REDUCERS,
    _merge_pipeline_status,
)


class TestStateSchema:
    """Validates the TypedDict structure and field definitions."""

    def test_crewops_state_is_typeddict(self):
        """CrewOpsState must be a TypedDict, not Pydantic BaseModel."""
        # TypedDicts have __annotations__ and __required_keys__
        assert hasattr(CrewOpsState, "__annotations__")
        assert hasattr(CrewOpsState, "__required_keys__")

    def test_required_input_fields_present(self):
        """raw_logs and metadata must be in the schema."""
        for field in REQUIRED_INPUT_FIELDS:
            assert field in CrewOpsState.__annotations__, (
                f"Required input field '{field}' missing from CrewOpsState"
            )

    def test_all_expected_fields_present(self):
        """All 18 expected fields must be present."""
        expected = {
            "raw_logs", "metadata",
            "log_summary", "log_type",
            "severity", "severity_rationale", "critical_issues",
            "rag_context", "root_cause_analysis",
            "remediation_plan", "cookbook",
            "approval_required", "approval_status",
            "jira_tickets", "notifications_sent",
            "pipeline_status", "errors",
        }
        for field in expected:
            assert field in ALL_STATE_FIELDS, f"Field '{field}' missing from CrewOpsState"

    def test_total_field_count(self):
        """CrewOpsState should have exactly 17 fields."""
        # Update this test when adding new fields (it documents the intended schema)
        assert len(ALL_STATE_FIELDS) == 17, (
            f"Expected 17 fields, got {len(ALL_STATE_FIELDS)}: {ALL_STATE_FIELDS}"
        )

    def test_list_reducer_fields_identified(self):
        """All list fields with operator.add reducers must be identified."""
        expected_reducers = {
            "critical_issues",
            "rag_context",
            "jira_tickets",
            "notifications_sent",
            "errors",
        }
        assert expected_reducers == LIST_FIELDS_WITH_REDUCERS

    def test_annotated_fields_have_add_reducer(self):
        """List fields must use Annotated[list, operator.add] — not bare list."""
        import operator
        hints = get_type_hints(CrewOpsState, include_extras=True)
        for field in LIST_FIELDS_WITH_REDUCERS:
            hint = hints.get(field)
            assert hint is not None, f"Field '{field}' not found in type hints"
            origin = get_origin(hint)
            assert origin is Annotated, (
                f"Field '{field}' must be Annotated (for reducer), got {origin}"
            )
            args = get_args(hint)
            assert len(args) >= 2, f"Field '{field}' Annotated must have reducer arg"
            # Second arg is the reducer — should be operator.add
            assert args[1] is operator.add, (
                f"Field '{field}' reducer must be operator.add, got {args[1]}"
            )

    def test_non_list_fields_are_not_annotated_with_add(self):
        """Non-list scalar fields must NOT use the list reducer."""
        import operator
        hints = get_type_hints(CrewOpsState, include_extras=True)
        scalar_fields = ALL_STATE_FIELDS - LIST_FIELDS_WITH_REDUCERS
        for field in scalar_fields:
            hint = hints.get(field)
            if get_origin(hint) is Annotated:
                args = get_args(hint)
                assert args[1] is not operator.add, (
                    f"Scalar field '{field}' should NOT have operator.add reducer"
                )

    def test_state_dict_creation(self, minimal_state):
        """A valid CrewOpsState dict can be constructed with all fields."""
        # TypedDict doesn't enforce at runtime, but the structure should match
        assert set(minimal_state.keys()) >= REQUIRED_INPUT_FIELDS

    def test_reducers_accumulate_correctly(self):
        """Simulate operator.add reducer behavior: lists should be concatenated."""
        import operator
        list1 = [{"title": "Issue A"}]
        list2 = [{"title": "Issue B"}]
        merged = operator.add(list1, list2)
        assert merged == [{"title": "Issue A"}, {"title": "Issue B"}]
        assert len(merged) == 2

    def test_empty_list_reducer_is_idempotent(self):
        """Merging an empty list with operator.add should not change existing list."""
        import operator
        existing = [{"title": "Issue A"}]
        result = operator.add(existing, [])
        assert result == existing

    def test_pipeline_status_has_merge_reducer(self):
        """pipeline_status must use a dict merge reducer for parallel branch safety."""
        hints = get_type_hints(CrewOpsState, include_extras=True)
        hint = hints.get("pipeline_status")
        assert get_origin(hint) is Annotated, (
            "pipeline_status must be Annotated with a merge reducer for parallel branches"
        )
        args = get_args(hint)
        assert len(args) >= 2, "pipeline_status must have a reducer argument"
        # Reducer should be callable
        assert callable(args[1])

    def test_merge_pipeline_status_merges_dicts(self):
        """_merge_pipeline_status must correctly merge two status dicts."""
        a = {"classifier": {"status": "done"}, "severity": {"status": "done"}}
        b = {"jira": {"status": "done"}, "notification": {"status": "done"}}
        merged = _merge_pipeline_status(a, b)
        assert len(merged) == 4
        assert "classifier" in merged
        assert "jira" in merged

    def test_merge_pipeline_status_later_wins_on_collision(self):
        """Later update (b) overwrites earlier (a) on key collision."""
        a = {"classifier": {"status": "running"}}
        b = {"classifier": {"status": "done", "elapsed_s": 1.2}}
        merged = _merge_pipeline_status(a, b)
        assert merged["classifier"]["status"] == "done"

    def test_approval_required_is_bool(self):
        """approval_required must be bool for conditional routing."""
        hints = get_type_hints(CrewOpsState)
        assert hints["approval_required"] is bool
