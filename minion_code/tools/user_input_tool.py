#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User input tool
"""

from typing import Optional, Any, Dict, List
import json
import os
import sys
from minion.tools import AsyncBaseTool
from minion.types import AgentState


class UserInputTool(AsyncBaseTool):
    """User input tool"""

    name = "user_input"
    description = (
        "Ask the user one or more questions via UI input. "
        "Supports single question or multi-question form payload."
    )
    readonly = True  # Read-only tool, does not modify system state
    needs_state = True
    inputs = {
        "question": {
            "type": "string",
            "description": "Single question to ask the user (legacy mode)",
            "nullable": True,
        },
        "default_value": {
            "type": "string",
            "description": "Default value (optional)",
            "nullable": True,
        },
        "questions_json": {
            "type": "string",
            "description": (
                "Optional multi-question payload JSON. Example: "
                '{"title":"Project Setup","message":"Please provide inputs","questions":'
                '[{"id":"name","label":"Project name","type":"text","default":"demo"},'
                '{"id":"lang","label":"Language","type":"choice","options":["python","go"],"default":"python"}]}'
            ),
            "nullable": True,
        },
    }
    output_type = "string"

    async def forward(
        self,
        question: Optional[str] = None,
        default_value: Optional[str] = None,
        questions_json: Optional[str] = None,
        *,
        state: AgentState,
    ) -> str:
        """Ask user question(s) using UI adapters when available."""
        try:
            form_payload = self._build_form_payload(
                question=question,
                default_value=default_value,
                questions_json=questions_json,
            )

            output_adapter = None
            if hasattr(state, "metadata") and isinstance(state.metadata, dict):
                output_adapter = state.metadata.get("output_adapter")

            if output_adapter is not None:
                answers = await output_adapter.form(
                    message=form_payload["message"],
                    fields=form_payload["fields"],
                    title=form_payload["title"],
                    submit_text=form_payload["submit_text"],
                )
                if answers is None:
                    return "User cancelled input"
                return self.format_for_observation(
                    {
                        "status": "ok",
                        "title": form_payload["title"],
                        "answers": answers,
                    }
                )

            allow_stdin = os.getenv("MINION_CODE_ALLOW_STDIN_USER_INPUT", "").lower() in {
                "1",
                "true",
                "yes",
            }

            if not allow_stdin:
                fallback = (
                    "Interactive user_input is disabled in this UI to avoid blocking. "
                    "Ask the user directly in your assistant response and wait for their next message."
                )
                if default_value:
                    fallback += f" Default suggestion: {default_value}"
                return fallback

            if not sys.stdin or not sys.stdin.isatty():
                fallback = (
                    "Interactive stdin is not available. "
                    "Ask the user directly in your assistant response and wait for their next message."
                )
                if default_value:
                    fallback += f" Default suggestion: {default_value}"
                return fallback

            answers: Dict[str, Any] = {}
            for field in form_payload["fields"]:
                prompt = f"Question: {field['label']}"
                if field.get("default") is not None:
                    prompt += f" (default: {field['default']})"
                if field.get("type") == "choice" and field.get("options"):
                    prompt += f" options={field['options']}"
                prompt += "\nPlease enter your answer: "

                user_response = input(prompt).strip()
                if not user_response and field.get("default") is not None:
                    user_response = str(field.get("default"))
                answers[field["id"]] = user_response

            return self.format_for_observation(
                {"status": "ok", "title": form_payload["title"], "answers": answers}
            )

        except KeyboardInterrupt:
            return "User cancelled input"
        except Exception as e:
            return f"Error getting user input: {str(e)}"

    def format_for_observation(self, output: Any) -> str:
        """Format tool output for LLM observation."""
        if isinstance(output, str):
            return output
        try:
            return json.dumps(output, ensure_ascii=False)
        except Exception:
            return str(output)

    def format_for_ui(self, title: str, message: str, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a simple JSON UI schema for UI-capable renderers."""
        return {
            "protocol": "a2ui/v1",
            "renderer": "json_form",
            "type": "form",
            "title": title,
            "message": message,
            "submit_text": "Submit",
            "fields": fields,
        }

    def _build_form_payload(
        self,
        question: Optional[str],
        default_value: Optional[str],
        questions_json: Optional[str],
    ) -> Dict[str, Any]:
        """Build normalized form payload from legacy/single and JSON multi-question inputs."""
        if questions_json:
            parsed = json.loads(questions_json)
            if isinstance(parsed, list):
                raw_questions = parsed
                title = "User Input"
                message = "Please provide the requested information."
            elif isinstance(parsed, dict):
                raw_questions = parsed.get("questions") or []
                title = str(parsed.get("title") or "User Input")
                message = str(
                    parsed.get("message") or "Please provide the requested information."
                )
            else:
                raise ValueError("questions_json must be a JSON object or array")

            fields = self._normalize_fields(raw_questions)
            if not fields:
                raise ValueError("questions_json contains no valid questions")

            return {
                "title": title,
                "message": message,
                "submit_text": "Submit",
                "fields": fields,
            }

        single_question = (question or "Please provide input").strip()
        return {
            "title": "User Input",
            "message": "Please answer the following question.",
            "submit_text": "Submit",
            "fields": [
                {
                    "id": "answer",
                    "label": single_question,
                    "type": "text",
                    "default": default_value,
                    "placeholder": "",
                    "required": True,
                }
            ],
        }

    def _normalize_fields(self, raw_questions: List[Any]) -> List[Dict[str, Any]]:
        """Normalize raw question definitions into UI field schema."""
        fields: List[Dict[str, Any]] = []

        for index, item in enumerate(raw_questions):
            if isinstance(item, str):
                fields.append(
                    {
                        "id": f"q_{index+1}",
                        "label": item,
                        "type": "text",
                        "default": None,
                        "placeholder": "",
                        "required": True,
                    }
                )
                continue

            if not isinstance(item, dict):
                continue

            field_id = str(item.get("id") or f"q_{index+1}")
            label = str(item.get("label") or item.get("question") or field_id)
            field_type = str(item.get("type") or "text").lower()
            if field_type not in {"text", "choice"}:
                field_type = "text"

            options = item.get("options") if isinstance(item.get("options"), list) else []
            field: Dict[str, Any] = {
                "id": field_id,
                "label": label,
                "type": "choice" if options else field_type,
                "default": item.get("default"),
                "placeholder": str(item.get("placeholder") or ""),
                "required": bool(item.get("required", True)),
            }
            if options:
                field["options"] = [str(opt) for opt in options]

            fields.append(field)

        return fields
