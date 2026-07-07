"""
Text Generate - ComfyUI Custom Node
Supports OpenAI, Google Gemini, Anthropic, and xAI (Grok)
"""

import os
import json
import re
import time
from aiohttp import web

PROVIDERS = ["OpenAI", "Google Gemini", "Anthropic", "xAI"]

# LLM이 JSON/코드를 요청받으면 습관적으로 ```json ... ``` 코드펜스로
# 감싸서 응답하는 경우가 많다. 응답 전체가 하나의 코드펜스로만 감싸진
# 경우에만 벗겨내어(중간에 등장하는 코드블록은 건드리지 않음) 다운스트림
# 노드(JSON 파서 등)가 그대로 사용할 수 있게 한다.
_CODE_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\s*\n([\s\S]*?)\n?```")


def _strip_code_fence(text):
    if not text:
        return text
    m = _CODE_FENCE_RE.fullmatch(text.strip())
    return m.group(1).strip() if m else text

PROVIDER_MODELS = {
    "OpenAI": [
        "gpt-5.5", "gpt-5.5-pro", "gpt-5", "gpt-5.4-mini", "gpt-5.4-nano",
        "gpt-4o", "gpt-4o-mini", "o3", "o4-mini", "o1", "o1-mini",
    ],
    "Google Gemini": [
        "gemini-3.5-flash", "gemini-3.1-pro-preview", "gemini-3.1-flash",
        "gemini-3.1-flash-lite", "gemini-3-flash",
        "gemini-2.5-pro", "gemini-2.5-flash",
    ],
    "Anthropic": [
        "claude-fable-5", "claude-opus-4-8", "claude-opus-4-7",
        "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
    ],
    "xAI": [
        "grok-4.3", "grok-4.1-fast", "grok-4", "grok-4-fast",
        "grok-3", "grok-3-mini", "grok-build-0.1",
    ],
}

_KEYS_FILE = os.path.join(os.path.dirname(__file__), "api_keys.json")


def _load_keys():
    if os.path.exists(_KEYS_FILE):
        try:
            with open(_KEYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_keys(keys):
    try:
        with open(_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[TextGenerate] Failed to save API keys: {e}")


try:
    from server import PromptServer

    @PromptServer.instance.routes.get("/nambaksa/api_keys")
    async def route_get_keys(request):
        return web.json_response(_load_keys())

    @PromptServer.instance.routes.post("/nambaksa/api_keys")
    async def route_save_key(request):
        data = await request.json()
        provider = data.get("provider", "")
        key = data.get("key", "")
        if provider not in PROVIDERS:
            return web.json_response({"error": "Invalid provider"}, status=400)
        keys = _load_keys()
        if key:
            keys[provider] = key
        elif provider in keys:
            del keys[provider]
        _save_keys(keys)
        return web.json_response({"success": True})

    @PromptServer.instance.routes.get("/nambaksa/provider_models")
    async def route_provider_models(request):
        return web.json_response(PROVIDER_MODELS)

except Exception as e:
    print(f"[TextGenerate] Could not register API routes: {e}")


def _all_models():
    seen = set()
    result = []
    for models in PROVIDER_MODELS.values():
        for m in models:
            if m not in seen:
                seen.add(m)
                result.append(m)
    return result


class TextGenerate:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "안녕하세요! 자기소개를 해주세요.",
                    "dynamicPrompts": False,
                }),
                "provider": (PROVIDERS, {"default": "OpenAI"}),
                "model": (_all_models(), {"default": "gpt-4o"}),
                "api_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "max_tokens": ("INT", {
                    "default": 1024, "min": 1, "max": 65536, "step": 1,
                }),
                "temperature": ("FLOAT", {
                    "default": 0.7, "min": 0.0, "max": 2.0, "step": 0.01,
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "generate"
    CATEGORY = "text/AI"
    OUTPUT_NODE = True

    def generate(self, prompt, provider, model, api_key, max_tokens, temperature):
        key = api_key.strip() if api_key else ""
        if not key:
            stored = _load_keys()
            key = stored.get(provider, "").strip()
        if not key:
            print(f"[TextGenerate] ✖ '{provider}' API 키 없음 — 실행 중단")
            raise ValueError(
                f"[TextGenerate] '{provider}' API 키가 설정되지 않았습니다. "
                "노드에 키를 입력하고 'Save API Key'를 클릭하세요."
            )

        call_fn = {
            "OpenAI": self._call_openai,
            "Google Gemini": self._call_gemini,
            "Anthropic": self._call_anthropic,
            "xAI": self._call_xai,
        }.get(provider)
        if call_fn is None:
            raise ValueError(f"[TextGenerate] Unknown provider: {provider}")

        print(
            f"[TextGenerate] ▶ {provider}/{model} 호출 시작 "
            f"(prompt {len(prompt)}자, max_tokens={max_tokens}, temperature={temperature})"
        )
        start = time.time()

        # API는 요청한 값 그대로 딱 한 번만 호출한다. 잘렸다고 노드가
        # 임의로 max_tokens를 올려 다시 호출하면 사용자 동의 없이 API
        # 비용이 추가로 나가므로, 잘림 여부만 알려주고 값 조정은
        # 사용자가 직접 하도록 한다.
        try:
            result, truncated, usage = call_fn(prompt, model, key, max_tokens, temperature)
        except Exception as e:
            elapsed = time.time() - start
            print(f"[TextGenerate] ✖ {provider}/{model} 실패 ({elapsed:.1f}s): {e}")
            raise

        elapsed = time.time() - start
        status = " (⚠ max_tokens에 걸려 잘림)" if truncated else ""
        print(f"[TextGenerate] ✔ {provider}/{model} 완료 ({elapsed:.1f}s, 응답 {len(result)}자){status}")
        if usage:
            print(
                f"[TextGenerate] 🔢 토큰 사용량 — 입력 {usage['prompt']} / "
                f"출력 {usage['completion']} / 합계 {usage['total']}"
            )
        else:
            print("[TextGenerate] 🔢 토큰 사용량 정보를 API 응답에서 가져오지 못했습니다")

        stripped = _strip_code_fence(result)
        if stripped != result:
            print("[TextGenerate] ℹ 응답을 감싼 ```코드펜스 제거함")
        result = stripped

        if truncated:
            result += (
                f"\n\n⚠️ 응답이 max_tokens({max_tokens}) 한도에 걸려 잘렸습니다. "
                "노드의 max_tokens 값을 늘린 뒤 다시 실행해주세요."
            )

        return {"ui": {"text": [result]}, "result": (result,)}

    def _call_openai(self, prompt, model, api_key, max_tokens, temperature):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai 패키지가 필요합니다. 실행: pip install openai")

        client = OpenAI(api_key=api_key)
        reasoning_models = {"o1", "o1-mini", "o3", "o3-mini", "o4-mini"}
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if model in reasoning_models:
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature
        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        usage = None
        if response.usage:
            usage = {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            }
        return choice.message.content, choice.finish_reason == "length", usage

    def _call_gemini(self, prompt, model, api_key, max_tokens, temperature):
        # 신규 SDK (google-genai) 우선 시도
        try:
            from google import genai
            from google.genai import types as genai_types
            client = genai.Client(api_key=api_key)

            # Gemini 2.5+/3.x는 기본적으로 "thinking"이 켜져 있고, 그 토큰도
            # max_output_tokens 예산을 함께 사용한다. 이 노드는 단순 텍스트
            # 생성/포맷팅 용도이므로 thinking을 꺼서 출력 토큰이 추론에
            # 잘려나가지 않게 한다. 구형 모델 등 thinking_config를 지원하지
            # 않는 경우를 대비해 실패 시 옵션 없이 재시도한다.
            def _generate(with_thinking_off):
                kwargs = dict(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
                if with_thinking_off:
                    kwargs["thinking_config"] = genai_types.ThinkingConfig(thinking_budget=0)
                return client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(**kwargs),
                )

            try:
                response = _generate(True)
            except Exception:
                response = _generate(False)

            text = response.text or ""

            finish_reason = None
            try:
                finish_reason = response.candidates[0].finish_reason
            except Exception:
                pass
            truncated = finish_reason is not None and str(finish_reason).endswith("MAX_TOKENS")

            usage = None
            try:
                um = response.usage_metadata
                usage = {
                    "prompt": um.prompt_token_count,
                    "completion": um.candidates_token_count,
                    "total": um.total_token_count,
                }
            except Exception:
                pass

            return text, truncated, usage
        except ImportError:
            pass

        # 구 SDK (google-generativeai) 폴백
        try:
            import google.generativeai as genai_old
        except ImportError:
            raise ImportError(
                "Google GenAI SDK가 필요합니다.\n"
                "신규 SDK: pip install google-genai\n"
                "구 SDK:   pip install google-generativeai"
            )
        genai_old.configure(api_key=api_key)
        gen_cfg = genai_old.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        model_obj = genai_old.GenerativeModel(model, generation_config=gen_cfg)
        response = model_obj.generate_content(prompt)

        finish_reason = None
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            pass
        truncated = finish_reason is not None and str(finish_reason).endswith("MAX_TOKENS")

        usage = None
        try:
            um = response.usage_metadata
            usage = {
                "prompt": um.prompt_token_count,
                "completion": um.candidates_token_count,
                "total": um.total_token_count,
            }
        except Exception:
            pass

        return response.text, truncated, usage

    def _call_anthropic(self, prompt, model, api_key, max_tokens, temperature):
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic 패키지가 필요합니다. 실행: pip install anthropic")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=min(temperature, 1.0),
            messages=[{"role": "user", "content": prompt}],
        )
        usage = None
        if message.usage:
            usage = {
                "prompt": message.usage.input_tokens,
                "completion": message.usage.output_tokens,
                "total": message.usage.input_tokens + message.usage.output_tokens,
            }
        return message.content[0].text, message.stop_reason == "max_tokens", usage

    def _call_xai(self, prompt, model, api_key, max_tokens, temperature):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai 패키지가 필요합니다. 실행: pip install openai")

        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = response.choices[0]
        usage = None
        if response.usage:
            usage = {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            }
        return choice.message.content, choice.finish_reason == "length", usage


NODE_CLASS_MAPPINGS = {
    "nambaksa_text_generate": TextGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "nambaksa_text_generate": "Text Generate (AI)",
}
