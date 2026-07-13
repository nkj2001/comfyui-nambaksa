import { app } from "../../scripts/app.js";

// 새로 캔버스에 올려진 노드만 최소 크기로 줄인다.
// (onConfigure에서는 처리하지 않으므로, 저장된 워크플로를 불러올 때
// 사용자가 조정해 둔 크기는 그대로 유지된다.)
app.registerExtension({
    name: "nambaksa.Number",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "nambaksa_number") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (origCreated) origCreated.apply(this, arguments);

            requestAnimationFrame(() => {
                this.setSize(this.computeSize());
                app.graph.setDirtyCanvas(true, true);
            });
        };
    },
});
