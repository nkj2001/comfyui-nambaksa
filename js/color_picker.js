import { app } from "../../scripts/app.js";

const COLOR_WIDGETS = ["text_color", "bg_color", "stroke_color"];

let lastClientX = 200;
let lastClientY = 200;

document.addEventListener("pointerdown", (e) => {
    if (e.target?.tagName === "CANVAS") {
        lastClientX = e.clientX;
        lastClientY = e.clientY;
    }
}, true);

function openPicker(widget) {
    // 기존 피커 제거
    const old = document.getElementById("_nambaksa_picker");
    if (old) old.remove();

    const input = document.createElement("input");
    input.id = "_nambaksa_picker";
    input.type = "color";
    input.value = widget.value || "#000000";

    // 클릭 위치에 실제로 보이는 1x1 엘리먼트로 배치
    input.style.cssText = `
        position: fixed;
        left: ${lastClientX}px;
        top: ${lastClientY}px;
        width: 1px;
        height: 1px;
        padding: 0;
        border: none;
        outline: none;
        opacity: 0.01;
        cursor: pointer;
        z-index: 99999;
    `;
    document.body.appendChild(input);

    input.addEventListener("input", () => {
        widget.value = input.value;
        app.graph.setDirtyCanvas(true, true);
    });
    const cleanup = () => {
        if (document.body.contains(input)) document.body.removeChild(input);
    };
    input.addEventListener("change", () => { cleanup(); app.graph.setDirtyCanvas(true, true); });
    input.addEventListener("blur", () => setTimeout(cleanup, 500));

    // 강제로 포커스 후 클릭
    requestAnimationFrame(() => {
        input.focus();
        input.click();
    });
}

function openEyedropper(widget) {
    if (!window.EyeDropper) { alert("Chrome 95+ 필요"); return; }
    new EyeDropper().open()
        .then(r => { widget.value = r.sRGBHex; app.graph.setDirtyCanvas(true, true); })
        .catch(() => {});
}

app.registerExtension({
    name: "nambaksa.ColorPicker",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "nambaksa_text_to_image") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            if (origCreated) origCreated.apply(this, arguments);

            for (const w of (this.widgets || [])) {
                if (!COLOR_WIDGETS.includes(w.name)) continue;

                w._isColorWidget = true;

                w.computeSize = function(width) {
                    return [width, LiteGraph.NODE_WIDGET_HEIGHT];
                };

                w.draw = function(ctx, node, width, y) {
                    this.last_y = y;
                    const H = LiteGraph.NODE_WIDGET_HEIGHT;
                    const margin = 15;
                    const centerY = y + H / 2;

                    ctx.save();

                    ctx.fillStyle = "#222";
                    ctx.beginPath();
                    ctx.roundRect(margin, y, width - margin * 2, H, 3);
                    ctx.fill();

                    ctx.fillStyle = "#aaa";
                    ctx.font = "11px sans-serif";
                    ctx.textAlign = "left";
                    ctx.textBaseline = "middle";
                    ctx.fillText(this.name, margin + 6, centerY);

                    ctx.fillStyle = "#ddd";
                    ctx.textAlign = "right";
                    ctx.fillText(this.value || "#000000", width - margin - 52, centerY);

                    try { ctx.fillStyle = this.value || "#000000"; } catch(e) { ctx.fillStyle = "#000"; }
                    ctx.strokeStyle = "#888";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.roundRect(width - margin - 48, y + 3, H - 6, H - 6, 2);
                    ctx.fill();
                    ctx.stroke();

                    ctx.fillStyle = "#555";
                    ctx.beginPath();
                    ctx.roundRect(width - margin - 26, y + 3, H - 6, H - 6, 2);
                    ctx.fill();
                    ctx.stroke();
                    ctx.fillStyle = "#fff";
                    ctx.font = "12px sans-serif";
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillText("🎨", width - margin - 17, centerY);

                    ctx.restore();
                };
            }

            if (app.canvas && !app.canvas._nambaksaPatched) {
                app.canvas._nambaksaPatched = true;
                const origPrompt = app.canvas.prompt.bind(app.canvas);
                app.canvas.prompt = function(title, value, callback, event) {
                    const node = app.canvas.node_over;
                    if (node?.comfyClass === "nambaksa_text_to_image" && node.widgets) {
                        const H = LiteGraph.NODE_WIDGET_HEIGHT;
                        const localY = event ? (event.canvasY - node.pos[1]) : -1;
                        const hit = node.widgets.find(w =>
                            w._isColorWidget &&
                            w.last_y != null &&
                            localY >= w.last_y &&
                            localY <= w.last_y + H
                        );
                        if (hit) {
                            const margin = 15;
                            const width = node.size[0];
                            const localX = event ? (event.canvasX - node.pos[0]) : 0;
                            if (localX >= width - margin - 26 && localX <= width - margin - 6) {
                                openEyedropper(hit);
                            } else {
                                openPicker(hit);
                            }
                            return;
                        }
                    }
                    return origPrompt(title, value, callback, event);
                };
            }
        };
    },
});