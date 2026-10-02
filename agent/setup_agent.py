"""Create (or update) the Nova Mart agent on ElevenLabs from the files in agent/.

    WORKER_URL=https://<your-worker>.workers.dev python3 agent/setup_agent.py

Reads ELEVENLABS_API_KEY from .env and TOOL_SECRET from order-api/.dev.vars, and
never prints either value. Re-running reuses resources that already exist by name,
so it is safe to run again after editing the prompt or knowledge base.

API key permissions needed: ElevenAgents read/write, Voices read/write.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKER = os.environ.get("WORKER_URL", "https://nova-order-api.a84012807.workers.dev").rstrip("/")
API = "https://api.elevenlabs.io"

AGENT_NAME = "Nova Mart 雙語客服"
SECRET_NAME = "TOOL_SECRET"
KB_NAME = "Nova Mart return policy"
LLM = "gemini-2.5-flash"
TTS_MODEL = "eleven_v4_turbo"
# Yui (Taiwan Mandarin, cmn-TW) from the shared library; added to the account if missing.
ZH_VOICE = "kGjJqO6wdwRN9iJsoeIC"
ZH_VOICE_NAME = "Yui - Taiwan Mandarin (Nova Mart)"
# Jessica, a premade English voice every account has.
EN_VOICE = "cgSgspJ2msm6clMCkdW9"


def read_var(path, key):
    for line in (ROOT / path).read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{key} not found in {path}")


KEY = read_var(".env", "ELEVENLABS_API_KEY")


def call(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:800]}")


def find(path, list_key, name, name_of):
    for item in call("GET", path).get(list_key, []):
        if name_of(item) == name:
            return item
    return None


def ensure_zh_voice():
    mine = {v["voice_id"] for v in call("GET", "/v1/voices?show_legacy=false").get("voices", [])}
    if ZH_VOICE in mine:
        print(f"voice: reuse {ZH_VOICE}")
        return
    shared = call("GET", "/v1/shared-voices?page_size=100&language=zh&accent=taiwan%20mandarin")
    owner = next((v["public_owner_id"] for v in shared.get("voices", []) if v["voice_id"] == ZH_VOICE), None)
    if owner is None:
        sys.exit(f"voice {ZH_VOICE} not found in the shared library; pick another ZH_VOICE")
    call("POST", f"/v1/voices/add/{owner}/{ZH_VOICE}", {"new_name": ZH_VOICE_NAME})
    print(f"voice: added {ZH_VOICE}")


def secret_id():
    s = find("/v1/convai/secrets", "secrets", SECRET_NAME, lambda x: x.get("name"))
    if s:
        print(f"secret: reuse {s['secret_id']}")
        return s["secret_id"]
    value = read_var("order-api/.dev.vars", "TOOL_SECRET")
    s = call("POST", "/v1/convai/secrets", {"type": "new", "name": SECRET_NAME, "value": value})
    print(f"secret: created {s['secret_id']}")
    return s["secret_id"]


def kb_doc():
    d = find("/v1/convai/knowledge-base?page_size=100", "documents", KB_NAME, lambda x: x.get("name"))
    if not d:
        text = (ROOT / "agent/knowledge/return-policy.md").read_text()
        d = call("POST", "/v1/convai/knowledge-base/text", {"text": text, "name": KB_NAME})
        print(f"knowledge base: created {d['id']}")
    else:
        print(f"knowledge base: reuse {d['id']}")
    return {"type": "text", "name": KB_NAME, "id": d["id"], "usage_mode": "prompt"}


def tool_id(ref_file, path, sid):
    ref = json.loads((ROOT / "agent/tools" / ref_file).read_text())
    name = ref["name"]
    t = find("/v1/convai/tools", "tools", name, lambda x: x.get("tool_config", {}).get("name"))
    if t:
        print(f"tool {name}: reuse {t['id']}")
        return t["id"]
    body_props = ref["api_schema"]["request_body_schema"]["properties"]
    config = {
        "type": "webhook",
        "name": name,
        "description": ref["description"],
        "api_schema": {
            "url": WORKER + path,
            "method": "POST",
            "content_type": "application/json",
            "request_headers": {"X-Tool-Secret": {"secret_id": sid}},
            "request_body_schema": {
                "type": "object",
                "description": "Order lookup",
                "properties": {
                    k: {"type": "string", "description": v["description"]}
                    for k, v in body_props.items()
                },
                "required": ref["api_schema"]["request_body_schema"]["required"],
            },
        },
    }
    t = call("POST", "/v1/convai/tools", {"tool_config": config})
    print(f"tool {name}: created {t['id']}")
    return t["id"]


def agent(tool_ids, kb):
    prompt = (ROOT / "agent/system-prompt.md").read_text()
    lang_desc = (ROOT / "agent/language-detection-description.txt").read_text().strip()
    first_zh = "您好，這裡是 Nova Mart 客服，請問有什麼可以幫您？"
    first_en = "Hi, this is Nova Mart support. How can I help you today?"
    body = {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "language": "zh",
                "first_message": first_zh,
                "prompt": {
                    "prompt": prompt,
                    "llm": LLM,
                    "tool_ids": tool_ids,
                    "knowledge_base": [kb],
                    "built_in_tools": {
                        "language_detection": {
                            "type": "system",
                            "name": "language_detection",
                            "description": lang_desc,
                            "params": {
                                "system_tool_type": "language_detection",
                                "only_at_conversation_start": False,
                            },
                        },
                        "end_call": {
                            "type": "system",
                            "name": "end_call",
                            "description": "",
                            "params": {"system_tool_type": "end_call"},
                        },
                    },
                },
            },
            "tts": {"model_id": TTS_MODEL, "voice_id": ZH_VOICE},
            "language_presets": {
                "en": {
                    "overrides": {
                        "agent": {"language": "en", "first_message": first_en},
                        "tts": {"voice_id": EN_VOICE},
                    },
                },
            },
        },
        "platform_settings": {
            "auth": {
                "enable_auth": False,
                "allowlist": [{"hostname": WORKER.removeprefix("https://")}],
            },
        },
    }
    a = find("/v1/convai/agents?page_size=100", "agents", AGENT_NAME, lambda x: x.get("name"))
    if a:
        call("PATCH", f"/v1/convai/agents/{a['agent_id']}", body)
        print(f"agent: updated {a['agent_id']}")
        return a["agent_id"]
    a = call("POST", "/v1/convai/agents/create", body)
    print(f"agent: created {a['agent_id']}")
    return a["agent_id"]


if __name__ == "__main__":
    ensure_zh_voice()
    sid = secret_id()
    kb = kb_doc()
    tools = [
        tool_id("get_order_status.json", "/tools/order-status", sid),
        tool_id("check_return_eligibility.json", "/tools/return-eligibility", sid),
    ]
    agent_id = agent(tools, kb)
    print(json.dumps({"agent_id": agent_id, "tool_ids": tools, "kb_id": kb["id"], "secret_id": sid}))
