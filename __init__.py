from .text_to_image_alpha import (
    NODE_CLASS_MAPPINGS as _TIA_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as _TIA_NAMES,
)

NODE_CLASS_MAPPINGS = {**_TIA_CLASSES}
NODE_DISPLAY_NAME_MAPPINGS = {**_TIA_NAMES}

try:
    from .text_generate import (
        NODE_CLASS_MAPPINGS as _TG_CLASSES,
        NODE_DISPLAY_NAME_MAPPINGS as _TG_NAMES,
    )
    NODE_CLASS_MAPPINGS.update(_TG_CLASSES)
    NODE_DISPLAY_NAME_MAPPINGS.update(_TG_NAMES)
    print(f"[nambaksa] text_generate 로드 완료: {list(_TG_CLASSES.keys())}")
except Exception as e:
    import traceback
    print(f"[nambaksa] text_generate 로드 실패: {e}")
    traceback.print_exc()

try:
    from .text_replace import (
        NODE_CLASS_MAPPINGS as _TR_CLASSES,
        NODE_DISPLAY_NAME_MAPPINGS as _TR_NAMES,
    )
    NODE_CLASS_MAPPINGS.update(_TR_CLASSES)
    NODE_DISPLAY_NAME_MAPPINGS.update(_TR_NAMES)
    print(f"[nambaksa] text_replace 로드 완료: {list(_TR_CLASSES.keys())}")
except Exception as e:
    import traceback
    print(f"[nambaksa] text_replace 로드 실패: {e}")
    traceback.print_exc()

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
