"""GitHub Copilot Pro+ chat provider.

Routes through the OpenAI-compatible chat completions endpoint at
https://api.githubcopilot.com/chat/completions using a Copilot bearer token.

Supported models (as of this build, requires Copilot Pro+):
    claude-opus-4.7, claude-sonnet-4.6, claude-sonnet-4.5,
    claude-opus-4.5, claude-haiku-4.5,
    gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex, gpt-5.2, gpt-4.1,
    grok-code-fast-1, gemini-3.1-pro-preview, gemini-2.5-pro

Environment:
    GITHUB_COPILOT_TOKEN     bearer token for api.githubcopilot.com
    GITHUB_COPILOT_ENDPOINT  override endpoint (default: official URL)
"""
from __future__ import annotations
from providers.oai_compat import OpenAICompatibleProvider
from config.settings import get_settings


class GitHubCopilotProvider(OpenAICompatibleProvider):
    name = "github_copilot"

    def __init__(self) -> None:
        s = get_settings()
        self.api_key = s.github_copilot_token
        self.endpoint = s.github_copilot_endpoint or "https://api.githubcopilot.com/chat/completions"
        # Copilot servers expect these — without them the API frequently returns 400.
        self.extra_headers = {
            "Editor-Version": "vscode/1.95.0",
            "Editor-Plugin-Version": "copilot-chat/0.22.0",
            "Copilot-Integration-Id": "vscode-chat",
            "OpenAI-Intent": "conversation-panel",
        }
        # Default model is the strongest reasoning model.
        self.model_map = {
            "fast":     "claude-haiku-4.5",
            "smart":    "claude-opus-4.7",
            "creative": "gpt-5.5",
        }
