import importlib
import traceback

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

_MODULES = [
    "text_to_image_alpha",
    "text_generate",
    "text_replace",
    "number",
    "audio_video_sync",
]

for _mod_name in _MODULES:
    try:
        _module = importlib.import_module(f".{_mod_name}", package=__name__)
        NODE_CLASS_MAPPINGS.update(_module.NODE_CLASS_MAPPINGS)
        NODE_DISPLAY_NAME_MAPPINGS.update(_module.NODE_DISPLAY_NAME_MAPPINGS)
        print(f"[nambaksa] {_mod_name} 로드 완료: {list(_module.NODE_CLASS_MAPPINGS.keys())}")
    except Exception as e:
        print(f"[nambaksa] {_mod_name} 로드 실패: {e}")
        traceback.print_exc()

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
