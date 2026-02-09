from __future__ import annotations

from unittest.mock import MagicMock

from mcp_server_deepresearcher.deepresearcher.utils import (
    create_mcp_tasks, filter_mcp_tools_for_deepresearcher)


def _tool(name: str) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.coroutine = MagicMock(return_value=f"task:{name}")
    return t


def test_filter_mcp_tools_keeps_only_search_and_extract_transcripts_for_youtube() -> (
    None
):
    tools = [
        _tool("mcp_search_youtube_videos"),
        _tool("search_and_extract_transcripts"),
        _tool("extract_transcripts"),
        _tool("tavily_web_search"),
    ]

    filtered = filter_mcp_tools_for_deepresearcher(tools)
    names = [t.name for t in filtered]

    assert "search_and_extract_transcripts" in names
    assert "tavily_web_search" in names
    assert "mcp_search_youtube_videos" not in names
    assert "extract_transcripts" not in names


def test_twitter_tools_use_simplified_original_topic_when_provided() -> None:
    twitter_tool = _tool("twitter_search_topic")
    apify_tool = _tool("apidojo-slash-tweet-scraper")

    long_abstract_query = "cybersecurity companies with names similar to 'Xyber' or 'Cyber Inc' and their services"
    simplified_search_query = "xyber inc"

    tasks, names = create_mcp_tasks(
        [twitter_tool, apify_tool],
        search_query=long_abstract_query,
        simplified_search_query=simplified_search_query,
    )

    assert names == ["twitter_search_topic", "apidojo-slash-tweet-scraper"]
    assert tasks == ["task:twitter_search_topic", "task:apidojo-slash-tweet-scraper"]

    twitter_tool.coroutine.assert_called_once_with(topic="xyber inc")
    apify_tool.coroutine.assert_called_once()
    kwargs = apify_tool.coroutine.call_args.kwargs
    assert kwargs["searchTerms"] == ["xyber inc"]
