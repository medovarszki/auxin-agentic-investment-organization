from pathlib import Path

from auxin_runtime.descriptor import build_options, load_descriptor

ROOT = Path(__file__).resolve().parents[3]
MS = load_descriptor(ROOT / "agents/market-sentiment/agent.yaml")
SCHEMA = {"type": "object"}


def test_without_mcp_urls_only_builtin_tools_remain():
    options = build_options(MS, Path("/agent"), SCHEMA, env={})
    assert options.mcp_servers == {}
    assert options.tools == ["WebSearch", "WebFetch"]
    assert options.allowed_tools == ["WebSearch", "WebFetch"]


def test_configured_mcp_server_brings_its_tools_and_token():
    env = {"AUXIN_MCP_IBKR_URL": "http://mcp-ibkr:8000/mcp", "AUXIN_MCP_IBKR_TOKEN": "t"}
    options = build_options(MS, Path("/agent"), SCHEMA, env=env)
    assert options.mcp_servers == {
        "ibkr": {"type": "http", "url": "http://mcp-ibkr:8000/mcp", "headers": {"Authorization": "Bearer t"}}
    }
    assert "mcp__ibkr__get_price" in options.allowed_tools
    assert "mcp__ibkr__get_price" not in options.tools  # tools= is the built-in set only
    assert not any(t.startswith("mcp__knowledge-base") for t in options.allowed_tools)


def test_wildcard_grants_whole_server():
    research = load_descriptor(ROOT / "agents/research/agent.yaml")
    env = {"AUXIN_MCP_KNOWLEDGE_BASE_URL": "http://kb:8000/mcp"}
    options = build_options(research, Path("/agent"), SCHEMA, env=env)
    assert "mcp__knowledge-base" in options.allowed_tools


def test_limits_and_isolation():
    options = build_options(MS, Path("/agent"), SCHEMA, env={})
    assert options.model == "claude-opus-5-5"
    assert options.permission_mode == "dontAsk"
    assert options.strict_mcp_config is True
    assert options.setting_sources == ["project"]
    assert options.skills == ["market-scan", "narrative-and-sentiment", "idea-generation"]
    assert options.max_turns == 40
    assert options.max_budget_usd == 2
    assert options.output_format == {"type": "json_schema", "schema": SCHEMA}
