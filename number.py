"""
Number - ComfyUI Custom Node
정수 값 하나를 입력받아 INT와 FLOAT로 동시에 출력한다.
"""

import sys


class NambaksaNumber:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("INT", {
                    "default": 0,
                    "min": -sys.maxsize,
                    "max": sys.maxsize,
                }),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT")
    RETURN_NAMES = ("int", "float")
    FUNCTION = "convert"
    CATEGORY = "utils"

    def convert(self, value):
        print(f"[Number] {value} -> INT {value} / FLOAT {float(value)}")
        return (value, float(value))


NODE_CLASS_MAPPINGS = {
    "nambaksa_number": NambaksaNumber,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "nambaksa_number": "Number",
}
