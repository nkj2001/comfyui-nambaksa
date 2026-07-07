"""
Text Replace - ComfyUI Custom Node
text_source 안의 특정 문자열(find)을 외부에서 연결된 값(value, 어떤 타입이든 가능)의
문자열 표현으로 치환한다. find/value 쌍은 최대 5개까지 동시에 지정 가능하다.
"""

_NUM_SLOTS = 5


class _AnyType(str):
    def __ne__(self, other):
        return False

    def __eq__(self, other):
        return True


ANY_TYPE = _AnyType("*")


class TextReplace:

    @classmethod
    def INPUT_TYPES(cls):
        optional = {}
        for i in range(1, _NUM_SLOTS + 1):
            optional[f"find{i}"] = ("STRING", {"default": ""})
            optional[f"value{i}"] = (ANY_TYPE,)
        return {
            "required": {
                "text_source": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "dynamicPrompts": False,
                }),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "replace"
    CATEGORY = "text"

    def replace(self, text_source, **kwargs):
        result = text_source
        replaced = 0
        for i in range(1, _NUM_SLOTS + 1):
            find = kwargs.get(f"find{i}") or ""
            value = kwargs.get(f"value{i}")
            if find and value is not None:
                result = result.replace(find, str(value))
                replaced += 1

        print(f"[TextReplace] {replaced}/{_NUM_SLOTS}개 쌍 치환 완료 (결과 {len(result)}자)")
        return (result,)


NODE_CLASS_MAPPINGS = {
    "nambaksa_text_replace": TextReplace,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "nambaksa_text_replace": "Text Replace",
}
