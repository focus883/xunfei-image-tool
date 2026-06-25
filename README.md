# 讯飞图片生成插件 (xunfei-image-tool)

让 QwenPaw Agent 调用讯飞星火图片生成大模型 API 进行 AI 文生图。

## 安装

```bash
qwenpaw plugin install /path/to/xunfei-image-tool
```

QwenPaw 会自动：
1. 复制插件到 `~/.qwenpaw/plugins/` 目录
2. 自动安装依赖（`httpx`）
3. 热加载到当前运行中的 QwenPaw，无需重启

## 配置（必需）

`xunfei_image_generate` **必须配置以下参数**：

| 字段 | 说明 |
|---|---|
| `app_id` | 从讯飞开放平台控制台创建的应用中获取的 app_id |
| `api_key` | 从讯飞开放平台控制台获取的 APIKey |
| `api_secret` | 从讯飞开放平台控制台获取的 APISecret |
| `endpoint` | API 接入点选择：`maas-api.cn-huabei-1.xf-yun.com`（图片生成大模型）或 `xingchen-api.cn-huabei-1.xf-yun.com`（Kolors） |
| `domain` | 模型 ID（modelID），可从星辰 MaaS 网页获取 |
| `default_width` | 默认图片宽度（像素），默认 768 |
| `default_height` | 默认图片高度（像素），默认 768 |

### 通过 QwenPaw Console 配置

在 QwenPaw Console → Agent Settings → Tools → `xunfei_image_generate` 中填写以上字段。

## 启用

插件安装后，Tool 默认处于**禁用**状态。需：
- **QwenPaw Console** → Agent Settings → Tools → 勾选 `xunfei_image_generate` → 保存

## 使用

```python
# 基础用法
xunfei_image_generate(prompt="一只可爱的小猫在草地上奔跑")

# 高级用法
xunfei_image_generate(
    prompt="日落时分，海边的灯塔",
    negative_prompt="模糊，低质量",
    width=1024,
    height=768,
    seed=12345,
    num_inference_steps=30,
    guidance_scale=7.5,
    scheduler="DPM++ 2M Karras"
)
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `prompt` | str | ✅ | 图片描述文字，不超过 1024 字符 |
| `negative_prompt` | str | ❌ | 负面提示词，不超过 1024 字符 |
| `width` | int | ❌ | 图片宽度（默认使用配置值） |
| `height` | int | ❌ | 图片高度（默认使用配置值） |
| `seed` | int | ❌ | 随机种子（0~INT_MAX，默认 42） |
| `num_inference_steps` | int | ❌ | 推理步数（0~50，默认 20） |
| `guidance_scale` | float | ❌ | 提示词相关度（0~20，默认 5.0） |
| `scheduler` | str | ❌ | 调度器（支持：DPM++ 2M Karras、DPM++ SDE Karras、DDIM、Euler a、Euler） |

### 返回值

成功时返回 `data:image/png;base64,...` 格式的图片 data URI，可以直接在浏览器或支持 base64 图片的客户端中显示。

失败时返回错误信息（以 ❌ 开头）。

## API 说明

- **请求地址**：`https://{endpoint}/v2.1/tti`
- **鉴权方式**：HTTP URL 签名（HMAC-SHA256）
- **请求方法**：POST
- **Content-Type**：application/json;charset=UTF-8

## 依赖

- httpx>=0.27.0

## 支持的分辨率

| 分辨率 | 图点数 |
|---|---|
| 512x512 | 6 |
| 640x360 | 6 |
| 640x480 | 6 |
| 768x768 | 8 |
| 1024x1024 | 14 |
| 720x1280 | 12 |
| 1280x720 | 12 |

> FLUX.1-dev 模型所有参数均为默认值，暂不支持更改。

## 常见问题

- **鉴权失败 (code=10003)**：检查 app_id、api_key、api_secret 是否正确
- **请求超时**：图片生成较慢时可能超时，可适当增加 timeout
- **domain 错误**：确保 domain 参数填写的是正确的模型 ID