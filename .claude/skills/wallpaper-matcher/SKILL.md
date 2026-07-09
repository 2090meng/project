---
name: wallpaper-matcher
version: 1.0
description: 根据情绪关键词从 Unsplash 匹配壁纸背景
trigger: ["换壁纸", "匹配背景", "壁纸", "wallpaper", "背景"]
---

# 壁纸匹配 Skill

## 触发条件
情绪分析完成后触发，或用户说"换壁纸"、"匹配背景"、"换个壁纸"。

## 执行逻辑

### 第 1 步：获取主导情绪
从情绪分析结果中提取主导情绪和次主导情绪。

### 第 2 步：映射搜索关键词

| 情绪 | Unsplash 搜索词 |
|------|----------------|
| 快乐 | warm sunlight nature, golden hour, blooming flowers |
| 平静 | calm lake reflection, zen garden, misty mountains |
| 悲伤 | lonely bench rain, window raindrops, foggy street |
| 愤怒 | stormy sky dramatic, volcanic lightning, crashing waves |
| 期待 | sunrise horizon, open road dawn, hot air balloon sky |
| 恐惧 | deep forest fog, abandoned building, dark tunnel light |
| 厌恶 | wilted flowers, polluted river, cracked earth |
| 信任 | ancient tree roots, hands holding, stone bridge arch |

### 第 3 步：调用 Unsplash API
- Endpoint: `https://api.unsplash.com/photos/random`
- 参数: `query=<关键词>`, `orientation=landscape`, `w=1920`
- 认证: `Authorization: Client-ID <UNSPLASH_ACCESS_KEY>`
- 超时 8 秒，失败重试 1 次

### 第 4 步：返回壁纸信息
```json
{
  "url": "https://images.unsplash.com/photo-xxx?w=1920",
  "photographer": "John Doe",
  "photographer_url": "https://unsplash.com/@johndoe",
  "description": "A golden wheat field under warm sunset light",
  "emotion_match": "快乐 (92%)"
}
```

### 第 5 步：注入背景
用 CSS 注入：`body::before { background: url(...) center/cover; opacity: 0.15; }`
配合 `backdrop-filter: blur(8px)` 毛玻璃内容区。
摄影师姓名标注在页脚，符合 Unsplash 条款。

### 降级策略
- 无 Unsplash Key → 使用情绪纯色渐变 CSS
- API 超时 → 降级到渐变
- 结果为空 → 改用通用关键词 "nature landscape"
