import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const PROVIDER_MODELS = {
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
};

const MIN_NODE_WIDTH = 340;
const MIN_NODE_HEIGHT = 520;

async function fetchStoredKey(provider) {
    try {
        const res = await fetch("/nambaksa/api_keys");
        if (res.ok) {
            const keys = await res.json();
            return keys[provider] || "";
        }
    } catch (_) {}
    return "";
}

async function persistKey(provider, key) {
    try {
        await fetch("/nambaksa/api_keys", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ provider, key }),
        });
    } catch (e) {
        console.error("[TextGenerate] API 키 저장 실패:", e);
    }
}

function syncModelOptions(provider, modelWidget, resetToFirst = false) {
    const models = PROVIDER_MODELS[provider] || [];
    modelWidget.options.values = models;
    if (resetToFirst || !models.includes(modelWidget.value)) {
        modelWidget.value = models[0] ?? "";
    }
    app.graph.setDirtyCanvas(true, true);
}

function setupNode(node) {
    const providerW = node.widgets?.find(w => w.name === "provider");
    const modelW    = node.widgets?.find(w => w.name === "model");
    const apiKeyW   = node.widgets?.find(w => w.name === "api_key");

    if (!providerW || !modelW || !apiKeyW) return;

    syncModelOptions(providerW.value, modelW);

    fetchStoredKey(providerW.value).then(k => {
        if (k && !apiKeyW.value) {
            apiKeyW.value = k;
            app.graph.setDirtyCanvas(true, true);
        }
    });

    const origCb = providerW.callback;
    providerW.callback = async function(value) {
        if (origCb) origCb.call(this, value);
        syncModelOptions(value, modelW, true);
        apiKeyW.value = await fetchStoredKey(value);
        app.graph.setDirtyCanvas(true, true);
    };

    // Save API Key 버튼
    let saveBtn = node.addWidget("button", "Save API Key", null, async () => {
        await persistKey(providerW.value, apiKeyW.value);
        if (saveBtn) {
            const orig = saveBtn.name;
            saveBtn.name = "✓ Saved!";
            app.graph.setDirtyCanvas(true, true);
            setTimeout(() => {
                saveBtn.name = orig;
                app.graph.setDirtyCanvas(true, true);
            }, 1500);
        }
    }, { serialize: false });

    // Clear API Key 버튼
    node.addWidget("button", "Clear API Key", null, async () => {
        apiKeyW.value = "";
        await persistKey(providerW.value, "");
        app.graph.setDirtyCanvas(true, true);
    }, { serialize: false });

    // 출력 결과 표시 textarea
    const outputEl = document.createElement("textarea");
    outputEl.readOnly = true;
    outputEl.placeholder = "결과가 여기에 표시됩니다...";
    outputEl.style.cssText = [
        "width:100%",
        "height:120px",
        "background:#1a1a1a",
        "color:#ccc",
        "border:1px solid #444",
        "border-radius:3px",
        "padding:6px",
        "font-size:12px",
        "font-family:sans-serif",
        "resize:vertical",
        "box-sizing:border-box",
        "cursor:text",
    ].join(";");

    node.addDOMWidget("output_text", "customtext", outputEl, {
        getValue: () => outputEl.value,
        setValue: (v) => { outputEl.value = v ?? ""; },
        serialize: false,
    });

    // ▶ Generate — 해당 노드만 단독 실행
    node.addWidget("button", "▶  Generate", null, async () => {
        outputEl.value = "⏳ 생성 중...";

        const promptW    = node.widgets.find(w => w.name === "prompt");
        const maxTokW    = node.widgets.find(w => w.name === "max_tokens");
        const tempW      = node.widgets.find(w => w.name === "temperature");

        const singleNodePrompt = {};
        singleNodePrompt[String(node.id)] = {
            class_type: "nambaksa_text_generate",
            inputs: {
                prompt:      promptW?.value   ?? "",
                provider:    providerW.value,
                model:       modelW.value,
                api_key:     apiKeyW.value,
                max_tokens:  maxTokW?.value   ?? 1024,
                temperature: tempW?.value     ?? 0.7,
            },
        };

        try {
            const res = await fetch("/prompt", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    client_id: api.clientId,
                    prompt: singleNodePrompt,
                }),
            });
            if (!res.ok) {
                const err = await res.json();
                outputEl.value = `❌ 오류: ${err?.error?.message ?? JSON.stringify(err)}`;
            }
        } catch (e) {
            outputEl.value = `❌ 요청 실패: ${e.message}`;
        }
    }, { serialize: false });

    // 실행 완료 이벤트 → 결과 표시
    api.addEventListener("executed", (e) => {
        if (String(e.detail?.node) !== String(node.id)) return;
        const text = e.detail?.output?.text?.[0];
        if (text !== undefined) outputEl.value = text;
    });

    // 실행 오류 이벤트
    api.addEventListener("execution_error", (e) => {
        if (String(e.detail?.node_id) !== String(node.id)) return;
        outputEl.value = `❌ ${e.detail?.exception_message ?? "알 수 없는 오류"}`;
    });

    // 위젯(버튼, 출력창 등)이 모두 추가된 뒤 노드 기본 크기를 재계산해서
    // prompt/output 텍스트박스가 노드 밖으로 넘치지 않게 함
    requestAnimationFrame(() => {
        const computed = node.computeSize();
        node.setSize([
            Math.max(node.size[0], computed[0], MIN_NODE_WIDTH),
            Math.max(computed[1], MIN_NODE_HEIGHT),
        ]);
        app.graph.setDirtyCanvas(true, true);
    });
}

app.registerExtension({
    name: "nambaksa.TextGenerate",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "nambaksa_text_generate") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            if (origCreated) origCreated.apply(this, arguments);
            setupNode(this);
        };

        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function(config) {
            if (origConfigure) origConfigure.apply(this, arguments);

            const providerW = this.widgets?.find(w => w.name === "provider");
            const modelW    = this.widgets?.find(w => w.name === "model");
            const apiKeyW   = this.widgets?.find(w => w.name === "api_key");

            if (providerW && modelW) syncModelOptions(providerW.value, modelW);

            if (providerW && apiKeyW && !apiKeyW.value) {
                fetchStoredKey(providerW.value).then(k => {
                    if (k) {
                        apiKeyW.value = k;
                        app.graph.setDirtyCanvas(true, true);
                    }
                });
            }
        };
    },
});
