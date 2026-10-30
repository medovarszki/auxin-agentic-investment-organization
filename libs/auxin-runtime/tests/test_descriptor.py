from pathlib import Path

from auxin_runtime.descriptor import build_options, load_descriptor

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = load_descriptor(ROOT / "agents/research/agent.yaml")
SCHEMA = {"type": "object"}


def test_without_mcp_urls_only_builtin_tools_remain():
    options = build_options(RESEARCH, Path("/agent"), SCHEMA, env={})
    assert options.mcp_servers == {}
    assert options.tools == ["WebSearch", "WebFetch"]
    assert options.allowed_tools == ["WebSearch", "WebFetch"]


def test_configured_mcp_server_brings_its_tools_and_token():
    env = {"AUXIN_MCP_IBKR_URL": "http://mcp-ibkr:8000/mcp", "AUXIN_MCP_IBKR_TOKEN": "t"}
    options = build_options(RESEARCH, Path("/agent"), SCHEMA, env=env)
    assert options.mcp_servers == {
        "ibkr": {"type": "http", "url": "http://mcp-ibkr:8000/mcp", "headers": {"Authorization": "Bearer t"}}
    }
    assert "mcp__ibkr__get_price" in options.allowed_tools
    assert "mcp__ibkr__get_price" not in options.tools  # tools= is the built-in set only
    assert not any(t.startswith("mcp__knowledge-base") for t in options.allowed_tools)


def test_wildcard_grants_whole_server():
    env = {"AUXIN_MCP_KNOWLEDGE_BASE_URL": "http://kb:8000/mcp"}
    options = build_options(RESEARCH, Path("/agent"), SCHEMA, env=env)
    assert "mcp__knowledge-base" in options.allowed_tools


def test_limits_and_isolation():
    options = build_options(RESEARCH, Path("/agent"), SCHEMA, env={})
    assert options.model == "claude-sonnet-5-5"
    assert options.permission_mode == "dontAsk"
    assert options.strict_mcp_config is True
    assert options.setting_sources == ["project"]
    assert options.skills == ["market-scan", "narrative-and-sentiment", "idea-generation", "position-review", "lesson"]
    assert options.max_turns == 80
    assert options.max_budget_usd is None
    assert options.output_format == {"type": "json_schema", "schema": SCHEMA}
