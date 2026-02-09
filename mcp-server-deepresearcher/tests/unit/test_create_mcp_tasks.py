from __future__ import annotations

from unittest.mock import MagicMock

from mcp_server_deepresearcher.deepresearcher.utils import create_mcp_tasks


def test_create_mcp_tasks_arxiv_search_uses_top_level_args_when_available() -> None:
    tool = MagicMock()
    tool.name = "arxiv_search"
    tool.coroutine = MagicMock(return_value="task")

    class ArgsSchema:
        # Simulate pydantic v2 schema (class attribute)
        model_fields = {"query": object(), "max_results": object()}

    tool.args_schema = ArgsSchema

    tasks, task_names = create_mcp_tasks([tool], search_query="llm 2024")

    tool.coroutine.assert_called_once_with(query="llm 2024", max_results=3)
    assert tasks == ["task"]
    assert task_names == ["arxiv_search"]


def test_create_mcp_tasks_arxiv_search_keeps_request_wrapper_if_tool_expects_it() -> (
    None
):
    tool = MagicMock()
    tool.name = "arxiv_search"
    tool.coroutine = MagicMock(return_value="task")

    class ArgsSchema:
        # Simulate a wrapper-style tool schema
        model_fields = {"request": object()}

    tool.args_schema = ArgsSchema

    tasks, task_names = create_mcp_tasks([tool], search_query="llm 2024")

    tool.coroutine.assert_called_once_with(
        request={"query": "llm 2024", "max_results": 3}
    )
    assert tasks == ["task"]
    assert task_names == ["arxiv_search"]
