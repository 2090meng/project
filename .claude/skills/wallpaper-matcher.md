# 壁纸匹配 Skill

## 触发条件
情绪分析完成后自动触发，或用户说"换壁纸"、"匹配背景"。

## 执行逻辑
1. 获取主导情绪和次主导情绪
2. 将情绪映射为 Unsplash 搜索关键词
3. 调用 Unsplash API 搜索高相关度摄影图
4. 筛选横版、浅景深、适合做背景的图片
5. 返回壁纸 URL + 摄影师信息 + 下载链接

## 情绪 → 搜索关键词映射
- **快乐**: "warm sunlight nature, golden hour, blooming flowers"
- **平静**: "calm lake reflection, zen garden, misty mountains"
- **悲伤**: "lonely bench rain, window raindrops, foggy street"
- **愤怒**: "stormy sky dramatic, volcanic lightning, crashing waves"
- **期待**: "sunrise horizon, open road dawn, hot air balloon sky"
- **恐惧**: "deep forest fog, abandoned building, dark tunnel"
- **厌恶**: "wilted flowers, polluted river, cracked earth"
- **信任**: "ancient tree roots, hands holding, stone bridge arch"

## Unsplash API 调用
- Endpoint: `https://api.unsplash.com/photos/random`
- 参数: `query`, `orientation=landscape`, `content_filter=high`
- 认证: `Authorization: Client-ID <ACCESS_KEY>`
- 优先级: 高相关度 > 高下载量 > 新近上传

## 返回格式
```json
{
  "wallpaper_url": "https://images.unsplash.com/photo-xxx?w=1920",
  "thumbnail_url": "https://images.unsplash.com/photo-xxx?w=400",
  "photographer": "John Doe",
  "photographer_url": "https://unsplash.com/@johndoe",
  "description": "A golden wheat field under warm sunset light",
  "dominant_colors": ["#F4A460", "#FFD700", "#FFF8DC"],
  "emotion_match": "快乐 (92%)"
}
```

## 降级策略
- API Key 未配置 → 返回情绪纯色渐变 CSS
- API 超时 (5s) → 重试 1 次，仍失败则降级
- 搜索结果为空 → 使用通用关键词 "nature landscape"

## 使用建议
- 壁纸作为页面 `body::before` 伪元素背景
- opacity 0.12-0.18，配合 `backdrop-filter: blur(8px)` 内容区
- 摄影师信息放在页脚，符合 Unsplash 使用条款
