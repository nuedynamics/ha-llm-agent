"""A tiny OpenAI-compatible server with scripted replies, for end-to-end tests.

Standard library only. Replies depend on the last user message:
  "switch on"  -> call_service input_boolean.turn_on, then a confirmation
  "write file" -> write_file (risky, needs approval), then a confirmation
  "long story" -> a reply cut off at the length limit
  "new dashboard" -> save_dashboard for the main dashboard (risky, shows a preview)
  anything else -> a plain text reply
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys

SWITCH = "input_boolean.e2e_switch"


def tool_call(name: str, args: dict) -> list[dict]:
    return [
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": f"call_{name}",
                                "function": {"name": name, "arguments": ""},
                            }
                        ]
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [{"index": 0, "function": {"arguments": json.dumps(args)}}]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
    ]


def text(words: str) -> list[dict]:
    parts = words.split(" ")
    chunks = [
        {"choices": [{"delta": {"content": p + (" " if i < len(parts) - 1 else "")}}]}
        for i, p in enumerate(parts)
    ]
    chunks[-1]["choices"][0]["finish_reason"] = "stop"
    return chunks


def reply(messages: list[dict]) -> list[dict]:
    last = messages[-1]
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if isinstance(user, list):  # a message with photos
        seen = sum(1 for part in user if part.get("type") == "image_url")
        return text(f"I can see {seen} photo.")
    if last["role"] == "tool":
        if "denied" in last["content"]:
            return text("OK, I did not do that.")
        if "write file" in user:
            return text("I wrote **e2e_note.txt** for you.")
        return text("Done, the test switch is on.")
    if "switch on" in user:
        return tool_call(
            "call_service",
            {"domain": "input_boolean", "service": "turn_on", "target": {"entity_id": SWITCH}},
        )
    if "write file" in user:
        return tool_call(
            "write_file", {"path": "e2e_note.txt", "content": "hello from the e2e test\n"}
        )
    if "new dashboard" in user:
        cards = [
            {"type": "entities", "title": "E2E preview", "entities": [SWITCH]},
            {"type": "iframe", "url": "https://example.invalid/"},
        ]
        return tool_call("save_dashboard", {"config": {"views": [{"title": "Home", "cards": cards}]}})
    if user.endswith("long story"):
        chunks = text("Once upon a time")
        chunks[-1]["choices"][0]["finish_reason"] = "length"
        return chunks
    return text("Hello from the stub model.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # quiet
        pass

    def do_GET(self) -> None:
        if self.path.endswith("/models"):
            self._json({"data": [{"id": "stub-model", "object": "model"}]})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
        if not self.path.endswith("/chat/completions"):
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()
        for chunk in reply(body["messages"]):
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        usage = {
            "choices": [],
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 40,
                "prompt_tokens_details": {"cached_tokens": 1000},
            },
        }
        self.wfile.write(f"data: {json.dumps(usage)}\n\ndata: [DONE]\n\n".encode())

    def _json(self, data: dict) -> None:
        raw = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18089
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    ThreadingHTTPServer((host, port), Handler).serve_forever()
