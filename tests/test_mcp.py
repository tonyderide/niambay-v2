from daemon.mcp.client import MCPClient, MCPTool, MCPResult


def test_mcp_client_creation():
    cmd = ["npx", "@anthropic/mcp-gmail"]
    env = {"API_KEY": "test123"}
    client = MCPClient(command=cmd, env=env)
    assert client.command == cmd
    assert client.env == env
    assert client._process is None
    assert client._request_id == 0


def test_mcp_tool_dataclass():
    tool = MCPTool(
        name="send_email",
        description="Send an email",
        input_schema={"type": "object", "properties": {"to": {"type": "string"}}},
    )
    assert tool.name == "send_email"
    assert tool.description == "Send an email"
    assert "properties" in tool.input_schema


def test_mcp_result_dataclass():
    result = MCPResult(content=[{"type": "text", "text": "done"}])
    assert result.content == [{"type": "text", "text": "done"}]
    assert result.is_error is False

    error_result = MCPResult(content="something failed", is_error=True)
    assert error_result.is_error is True
