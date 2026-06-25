"""
讯飞图片生成插件 - QwenPaw 插件入口
"""
import importlib.util
import logging
import os

logger = logging.getLogger(__name__)

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_tools_module(module_name: str, file_name: str):
    """Load a module from this plugin's directory using importlib."""
    module_path = os.path.join(_PLUGIN_DIR, file_name)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class XunfeiImagePlugin:
    """讯飞图片生成插件入口。"""

    def __init__(self):
        self._api = None

    def register(self, api):
        """注册工具。"""
        self._api = api

        # 使用 importlib 加载工具模块（避免相对导入问题）
        tools_mod = _load_tools_module("image_gen", "image_gen.py")

        api.register_tool(
            tool_name="xunfei_image_generate",
            tool_func=tools_mod.xunfei_image_generate,
            description=(
                "Generate images from text prompts using Xunfei Spark "
                "image generation API. 调用讯飞星火图片生成API，"
                "根据文字描述生成图片。返回 base64 data URI 格式的图片。"
            ),
            icon="🖼️",
            enabled=False,
        )
        logger.info("xunfei-image-tool plugin registered")


# Export plugin instance (required by QwenPaw plugin loader)
plugin = XunfeiImagePlugin()
