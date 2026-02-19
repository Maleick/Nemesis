"""Codex OAuth-specific OpenAI Responses model helpers."""

import os
from typing import cast

from openai._streaming import AsyncStream
from openai.types import responses
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelRequest, ModelResponse
from pydantic_ai.models import ModelRequestParameters, check_allow_model_requests
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.settings import ModelSettings

DEFAULT_CODEX_CLIENT_VERSION = "0.104.0"
DEFAULT_CODEX_INSTRUCTIONS = "Follow the provided system and user messages and use tools when needed."


class CodexOAuthResponsesModel(OpenAIResponsesModel):
    """Responses model variant for Codex OAuth backend constraints."""

    async def request(
        self,
        messages: list[ModelRequest | ModelResponse],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """
        Codex backend currently requires stream=true even for non-stream callers.
        We consume the stream and convert it into a normal ModelResponse.
        """
        check_allow_model_requests()
        response_stream = cast(
            AsyncStream[responses.ResponseStreamEvent],
            await self._responses_create(
                messages,
                True,
                cast(OpenAIResponsesModelSettings, model_settings or {}),
                model_request_parameters,
            ),
        )

        completed_response = None
        async with response_stream:
            async for event in response_stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.completed":
                    completed_response = getattr(event, "response", None)
                    break
                if event_type == "response.failed":
                    raise UnexpectedModelBehavior("Codex OAuth response failed.")
                if event_type == "response.incomplete":
                    raise UnexpectedModelBehavior("Codex OAuth response incomplete.")

        if completed_response is None:
            raise UnexpectedModelBehavior("Codex OAuth stream ended without response.completed.")

        return self._process_response(completed_response)

    async def _responses_create(
        self,
        messages: list[ModelRequest | ModelResponse],
        stream: bool,
        model_settings: OpenAIResponsesModelSettings,
        model_request_parameters: ModelRequestParameters,
    ):
        """Inject Codex backend-required request defaults."""
        patched_settings = dict(model_settings)

        raw_headers = patched_settings.get("extra_headers")
        extra_headers = dict(raw_headers) if isinstance(raw_headers, dict) else {}
        extra_headers.setdefault("version", os.getenv("CODEX_CLIENT_VERSION", DEFAULT_CODEX_CLIENT_VERSION))
        patched_settings["extra_headers"] = extra_headers

        raw_body = patched_settings.get("extra_body")
        extra_body = dict(raw_body) if isinstance(raw_body, dict) else {}
        extra_body.setdefault("store", False)

        instructions = extra_body.get("instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            extra_body["instructions"] = os.getenv("CODEX_DEFAULT_INSTRUCTIONS", DEFAULT_CODEX_INSTRUCTIONS)

        patched_settings["extra_body"] = extra_body

        return await super()._responses_create(
            messages,
            stream,
            cast(OpenAIResponsesModelSettings, patched_settings),
            model_request_parameters,
        )
