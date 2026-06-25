"""
讯飞图片生成工具函数（含鉴权签名）

参考：https://www.xfyun.cn/doc/spark/图片生成.html
"""

import base64
import hashlib
import hmac
import json
import logging
import traceback
from datetime import datetime, timezone
from email.utils import formatdate
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# ---------- 常量 ----------
TIMEOUT_SEC = 120

SUPPORTED_SCHEDULERS = [
    "DPM++ 2M Karras",
    "DPM++ SDE Karras",
    "DDIM",
    "Euler a",
    "Euler",
]


# ========== 鉴权签名 ==========


def _build_signed_url(
    method: str,
    host: str,
    path: str,
    api_key: str,
    api_secret: str,
) -> str:
    """构建带签名的完整 URL（讯飞 HTTP 通用鉴权）。"""
    # 1. 日期（RFC1123）
    now = datetime.now(timezone.utc)
    date_str = formatdate(now.timestamp(), usegmt=True)

    # 2. 签名原串
    signature_parts = [
        f"host: {host}",
        f"date: {date_str}",
        f"{method} {path} HTTP/1.1",
    ]
    signature_str = "\n".join(signature_parts)

    # 3. HMAC-SHA256
    hmac_obj = hmac.new(
        api_secret.encode("utf-8"),
        signature_str.encode("utf-8"),
        hashlib.sha256,
    )
    signature = base64.b64encode(hmac_obj.digest()).decode("utf-8")

    # 4. Authorization
    authorization = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization_b64 = base64.b64encode(
        authorization.encode("utf-8")
    ).decode("utf-8")

    # 5. 拼接 query
    query_params = {
        "authorization": authorization_b64,
        "date": date_str,
        "host": host,
    }
    return f"https://{host}{path}?{urlencode(query_params)}"


# ========== 请求体构造 ==========


def _build_request_body(
    app_id: str,
    prompt: str,
    domain: str,
    uid: str = "",
    negative_prompt: str = "",
    width: int = 768,
    height: int = 768,
    seed: int = 42,
    num_inference_steps: int = 20,
    guidance_scale: float = 5.0,
    scheduler: str = "DPM++ 2M Karras",
) -> dict:
    """构造讯飞图片生成 API 请求体。"""
    body = {
        "header": {"app_id": app_id},
        "parameter": {
            "chat": {
                "domain": domain,
                "width": width,
                "height": height,
                "seed": seed,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "scheduler": scheduler,
            }
        },
        "payload": {
            "message": {
                "text": [{"role": "user", "content": prompt}],
            },
        },
    }
    if uid:
        body["header"]["uid"] = uid
    if negative_prompt:
        body["payload"]["negative_prompts"] = {"text": negative_prompt}
    return body


# ========== 配置校验 ==========


def _validate_config(config: dict, errors: list) -> bool:
    """检查配置是否完整。"""
    required = ["app_id", "api_key", "api_secret", "domain"]
    ok = True
    for key in required:
        if not config.get(key):
            errors.append(f"缺少配置：{key}")
            ok = False
    if not config.get("endpoint"):
        errors.append("缺少配置：endpoint（接入点）")
        ok = False
    return ok


# ========== 主工具函数 ==========


def xunfei_image_generate(
    prompt: str,
    *,
    config: dict,
    negative_prompt: str = "",
    width: int = 0,
    height: int = 0,
    seed: int = 0,
    num_inference_steps: int = 0,
    guidance_scale: float = 0.0,
    scheduler: str = "",
) -> str:
    """调用讯飞图片生成 API 生成图片。

    参数：
        prompt: 图片描述文字（必填）
        config: 插件配置字典
        negative_prompt: 负面提示词
        width: 图片宽度（0 使用配置默认值）
        height: 图片高度（0 使用配置默认值）
        seed: 随机种子（0 使用 42）
        num_inference_steps: 推理步数（0 使用 20）
        guidance_scale: 提示词相关度（0 使用 5.0）
        scheduler: 调度器名称

    返回：
        data URI 格式图片（成功）或错误信息（以 ❌ 开头）。
    """
    # ---- 校验配置 ----
    errors = []
    if not _validate_config(config, errors):
        return f"❌ 配置错误：{'；'.join(errors)}"

    app_id = config["app_id"]
    api_key = config["api_key"]
    api_secret = config["api_secret"]
    host = config["endpoint"]
    domain = config["domain"]

    # ---- 参数合并 ----
    w = width if width > 0 else config.get("default_width", 768)
    h = height if height > 0 else config.get("default_height", 768)
    s = seed if seed > 0 else 42
    steps = num_inference_steps if num_inference_steps > 0 else 20
    gs = guidance_scale if guidance_scale > 0.0 else 5.0
    sch = scheduler if scheduler else "DPM++ 2M Karras"

    if sch not in SUPPORTED_SCHEDULERS:
        return (
            f"❌ 不支持的调度器：{sch}。"
            f"支持的调度器：{', '.join(SUPPORTED_SCHEDULERS)}"
        )
    if not prompt.strip():
        return "❌ prompt 不能为空"

    # ---- 构建请求 ----
    try:
        path = "/v2.1/tti"
        signed_url = _build_signed_url("POST", host, path, api_key, api_secret)
        # patch_id: 非全量训练的模型需要传入，从 config 中读取
        patch_id = config.get("patch_id", "")
        body = _build_request_body(
            app_id=app_id,
            prompt=prompt,
            domain=domain,
            negative_prompt=negative_prompt,
            width=w,
            height=h,
            seed=s,
            num_inference_steps=steps,
            guidance_scale=gs,
            scheduler=sch,
        )
        if patch_id:
            body["header"]["patch_id"] = [patch_id]
    except Exception as e:
        return f"❌ 构建请求失败：{e}"

    # ---- 发送请求 ----
    try:
        with httpx.Client(timeout=TIMEOUT_SEC) as client:
            resp = client.post(
                signed_url,
                json=body,
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )
            result = resp.json()
    except httpx.TimeoutException:
        return "❌ 请求超时（120秒），图片生成较慢或网络异常"
    except Exception as e:
        return f"❌ 请求失败：{e}\n{traceback.format_exc()}"

    # ---- 解析响应 ----
    try:
        header = result.get("header", {})
        code = header.get("code", -1)
        sid = header.get("sid", "")

        if code != 0:
            msg = header.get("message", "未知错误")
            return f"❌ 接口返回错误 (code={code} sid={sid})：{msg}"

        payload = result.get("payload", {})
        choices = payload.get("choices", {})
        texts = choices.get("text", [])

        if not texts:
            return f"❌ 响应中无图片数据 (sid={sid})"

        img_data = texts[0].get("content", "")

        if not img_data:
            return f"❌ 图片数据为空 (sid={sid})"

        return f"data:image/png;base64,{img_data}"

    except Exception as e:
        return (
            f"❌ 解析响应失败：{e}\n"
            f"原始响应：{json.dumps(result, ensure_ascii=False)[:2000]}"
        )