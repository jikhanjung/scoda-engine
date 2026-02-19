#!/usr/bin/env python3
"""
Comprehensive MCP Server Tests
Tests all 7 builtin tools with realistic scenarios.
Dynamic tools (from mcp_tools.json) are tested in test_runtime.py.
"""
import json
import pytest
from contextlib import asynccontextmanager
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


@asynccontextmanager
async def create_session():
    """Create a fresh MCP client session within the calling task."""
    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "scoda_engine.mcp_server"]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.mark.asyncio
async def test_list_tools():
    """Test that all 7 builtin tools are exposed"""
    async with create_session() as session:
        result = await session.list_tools()
        tools = result.tools
        tool_names = [tool.name for tool in tools]

        builtin_expected = [
            "execute_named_query",
            "get_metadata",
            "get_provenance",
            "list_available_queries",
            "get_annotations",
            "add_annotation",
            "delete_annotation"
        ]

        # At minimum, all 7 builtins must be present
        assert len(tool_names) >= 7
        for name in builtin_expected:
            assert name in tool_names, f"Missing builtin tool: {name}"


@pytest.mark.asyncio
async def test_get_metadata():
    """Test metadata (generic — artifact_metadata only, no domain statistics)"""
    async with create_session() as session:
        result = await session.call_tool("get_metadata", {})
        metadata = json.loads(result.content[0].text)

        assert "name" in metadata
        assert "version" in metadata
        # Generic get_metadata no longer includes domain statistics
        assert "artifact_id" in metadata


@pytest.mark.asyncio
async def test_get_provenance():
    """Test data provenance information"""
    async with create_session() as session:
        result = await session.call_tool("get_provenance", {})
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0

        source = data[0]
        assert "source_type" in source
        assert "citation" in source
        assert "description" in source


@pytest.mark.asyncio
async def test_list_available_queries():
    """Test named queries list"""
    async with create_session() as session:
        result = await session.call_tool("list_available_queries", {})
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0

        query = data[0]
        assert "id" in query
        assert "name" in query
        assert "description" in query
        assert "params_json" in query


@pytest.mark.asyncio
async def test_execute_named_query():
    """Test named query execution with a parameterless query"""
    async with create_session() as session:
        list_result = await session.call_tool("list_available_queries", {})
        queries = json.loads(list_result.content[0].text)
        assert len(queries) > 0

        # Pick a query that doesn't require parameters
        no_param_queries = [q for q in queries if not q.get("params_json")]
        assert len(no_param_queries) > 0, "No parameterless queries available"
        query_name = no_param_queries[0]["name"]

        result = await session.call_tool("execute_named_query", {
            "query_name": query_name,
            "params": {}
        })
        data = json.loads(result.content[0].text)

        assert "query" in data
        assert "columns" in data
        assert "rows" in data
        assert data["query"] == query_name


@pytest.mark.asyncio
async def test_annotations_lifecycle():
    """Test annotation create/read/delete lifecycle"""
    async with create_session() as session:
        # Use execute_named_query to find a genus instead of removed search_genera
        list_result = await session.call_tool("list_available_queries", {})
        queries = json.loads(list_result.content[0].text)

        # Find a query that returns genus data
        genus_query = None
        for q in queries:
            if 'genus' in q['name'].lower() or 'genera' in q['name'].lower():
                genus_query = q['name']
                break

        if genus_query:
            query_result = await session.call_tool("execute_named_query", {
                "query_name": genus_query,
                "params": {}
            })
            query_data = json.loads(query_result.content[0].text)
            if query_data["rows"]:
                row = query_data["rows"][0]
                genus_id = row.get("id", 1)
                genus_name = row.get("name", "TestGenus")
            else:
                genus_id = 1
                genus_name = "TestGenus"
        else:
            genus_id = 1
            genus_name = "TestGenus"

        create_result = await session.call_tool("add_annotation", {
            "entity_type": "genus",
            "entity_id": genus_id,
            "entity_name": genus_name,
            "annotation_type": "note",
            "content": "Test annotation from MCP",
            "author": "test_user"
        })
        annotation = json.loads(create_result.content[0].text)

        assert "id" in annotation
        assert annotation["entity_type"] == "genus"
        assert annotation["entity_id"] == genus_id
        assert annotation["content"] == "Test annotation from MCP"
        annotation_id = annotation["id"]

        read_result = await session.call_tool("get_annotations", {
            "entity_type": "genus",
            "entity_id": genus_id
        })
        annotations = json.loads(read_result.content[0].text)

        assert isinstance(annotations, list)
        assert any(a["id"] == annotation_id for a in annotations)

        delete_result = await session.call_tool("delete_annotation", {
            "annotation_id": annotation_id
        })
        delete_data = json.loads(delete_result.content[0].text)

        assert "message" in delete_data

        verify_result = await session.call_tool("get_annotations", {
            "entity_type": "genus",
            "entity_id": genus_id
        })
        remaining = json.loads(verify_result.content[0].text)

        assert not any(a["id"] == annotation_id for a in remaining)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
