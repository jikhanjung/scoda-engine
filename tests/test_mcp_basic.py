#!/usr/bin/env python3
"""
Basic MCP Server Test
Tests that all 7 builtin tools are properly implemented and connected.
"""
import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def test_mcp_server():
    """Test MCP server basic functionality"""

    print("Starting MCP server test...")

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "scoda_engine.mcp_server"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            print("Session initialized")

            # List all tools
            tools_result = await session.list_tools()
            tools = tools_result.tools
            tool_names = [tool.name for tool in tools]

            print(f"\nFound {len(tool_names)} tools:")
            for i, name in enumerate(tool_names, 1):
                print(f"   {i:2d}. {name}")

            # Expected builtin tools
            expected = [
                "execute_named_query",
                "get_metadata",
                "get_provenance",
                "list_available_queries",
                "get_annotations",
                "add_annotation",
                "delete_annotation"
            ]

            # Check all expected tools are present
            missing = set(expected) - set(tool_names)

            if missing:
                print(f"\nMissing tools: {missing}")
                return False

            print(f"\nAll {len(expected)} builtin tools are present")

            # Test a few basic tool calls
            print("\nTesting tool calls...")

            # Test 1: get_metadata
            try:
                result = await session.call_tool("get_metadata", {})
                data = json.loads(result.content[0].text)
                assert "artifact_id" in data
                print("   get_metadata OK")
            except Exception as e:
                print(f"   get_metadata FAILED: {e}")
                return False

            # Test 2: get_provenance
            try:
                result = await session.call_tool("get_provenance", {})
                data = json.loads(result.content[0].text)
                assert isinstance(data, list)
                print("   get_provenance OK")
            except Exception as e:
                print(f"   get_provenance FAILED: {e}")
                return False

            # Test 3: list_available_queries
            try:
                result = await session.call_tool("list_available_queries", {})
                data = json.loads(result.content[0].text)
                assert isinstance(data, list)
                print("   list_available_queries OK")
            except Exception as e:
                print(f"   list_available_queries FAILED: {e}")
                return False

            print("\nAll tests passed!")
            return True

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    exit(0 if success else 1)
