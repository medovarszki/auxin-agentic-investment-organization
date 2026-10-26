"""agent.yaml -> ClaudeAgentOptions."""
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from claude_agent_sdk import ClaudeAgentOptions
from pydantic import BaseModel, ConfigDict

# Appended to the role prompt in CLAUDE.md, which the session loads as project memory.
SYSTEM_PROMPT = (
    "You are an agent in Auxin, an agentic investment organization running on a paper trading "
    "account. Your role, rules and procedures are in CLAUDE.md and in your skills. Use only the "
    "tools you are given. Cite a dated source for every factual claim. Your final answer is the "
    "structured output requested; nothing else is read."
)


class _Spec(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Tools(_Spec):
    allow: list[str]


class Limits(_Spec):
    max_turns: int
    max_concurrent_tasks: int = 1


class Budget(_Spec):
    per_run_usd: float | None = None  # no daily budget (Mihály, 2026-10-26)


class Messages(_Spec):
    consumes: list[str]
    produces: list[str]


class AgentDescriptor(_Spec):
    name: str
    role: str
    model: str
    skills: list[str]
    tools: Tools
    mcp_servers: list[str] = []
    messages: Messages
    limits: Limits
    budget: Budget = Budget()


def load_descriptor(path: Path) -> AgentDescriptor:
    return AgentDescriptor.model_validate(yaml.safe_load(path.read_text()))


def _env_key(server: str) -> str:
    return server.upper().replace("-", "_")


def resolve_mcp_servers(desc: AgentDescriptor, env: Mapping[str, str]) -> dict[str, dict]:
    """HTTP MCP servers whose URL is configured (AUXIN_MCP_<NAME>_URL); the rest are skipped."""
    servers = {}
    for name in desc.mcp_servers:
        url = env.get(f"AUXIN_MCP_{_env_key(name)}_URL")
        if not url:
            continue
        config: dict[str, Any] = {"type": "http", "url": url}
        token = env.get(f"AUXIN_MCP_{_env_key(name)}_TOKEN")
        if token:
            config["headers"] = {"Authorization": f"Bearer {token}"}
        servers[name] = config
    return servers


def _mcp_server_of(tool: str) -> str | None:
    if not tool.startswith("mcp__"):
        return None
    return tool.split("__")[1]


def _permission_rule(tool: str) -> str:
    """`mcp__server__*` grants the whole server, which the CLI writes as `mcp__server`."""
    return tool[: -len("__*")] if tool.endswith("__*") else tool


def require_subscription_auth(env: Mapping[str, str] | None = None) -> None:
    """Agents run on the owner's Claude subscription (CLAUDE_CODE_OAUTH_TOKEN), never on an API key.

    The CLI prefers ANTHROPIC_API_KEY when both are set, which would silently bill the API instead.
    """
    env = os.environ if env is None else env
    if env.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is set: agents must use CLAUDE_CODE_OAUTH_TOKEN (subscription quota)")
    if not env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        raise SystemExit("CLAUDE_CODE_OAUTH_TOKEN is not set (create one with `claude setup-token`)")


def build_options(
    desc: AgentDescriptor,
    workdir: Path,
    output_schema: dict,
    env: Mapping[str, str] | None = None,
) -> ClaudeAgentOptions:
    env = os.environ if env is None else env
    servers = resolve_mcp_servers(desc, env)
    allow = [t for t in desc.tools.allow if _mcp_server_of(t) in (None, *servers)]
    return ClaudeAgentOptions(
        model=desc.model,
        system_prompt=SYSTEM_PROMPT,
        tools=[t for t in allow if _mcp_server_of(t) is None],
        allowed_tools=[_permission_rule(t) for t in allow],
        permission_mode="dontAsk",
        mcp_servers=servers,
        strict_mcp_config=True,
        skills=desc.skills,
        setting_sources=["project"],
        cwd=workdir,
        max_turns=desc.limits.max_turns,
        max_budget_usd=desc.budget.per_run_usd,
        output_format={"type": "json_schema", "schema": output_schema},
    )
