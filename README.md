# 🎨 情绪像素 · 心情艺术品

> 写下你的心情，AI 将为你创作一幅独一无二的情绪像素画 ✨

一个基于 Streamlit + DeepSeek API 的心情艺术品生成器。输入心情文字，AI 会分析你的情绪、绘制像素画、创作诗句，并生成独一无二的情绪指纹。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🧠 **AI情绪分析** | DeepSeek API 分析8个情绪维度（快乐/悲伤/愤怒/恐惧/惊讶/厌恶/期待/信任） |
| 🎨 **情绪像素画** | 8×8 像素网格，每种情绪占据2×2区域，颜色独特 |
| 📝 **AI情绪诗** | 根据你的心情生成两句押韵诗（每句≤10字） |
| 🔐 **情绪指纹** | SHA256 哈希生成的8位唯一标识 |
| 🖼️ **情绪画廊** | 侧边栏历史记录，刷新不丢失 |
| 📤 **分享卡片** | 一键下载含像素画+诗+指纹+二维码的卡片 |

## 🚀 本地运行

### 前提条件

- Python 3.10+
- DeepSeek API Key（[免费获取](https://platform.deepseek.com/api_keys)）

### 安装步骤

```bash
# 1. 克隆项目
git clone <你的仓库地址>
cd project

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
# 复制 secrets 模板并填入你的 API Key
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 编辑 .streamlit/secrets.toml，填入 DEEPSEEK_API_KEY

# 4. 启动应用
streamlit run app.py
```

浏览器访问 `http://localhost:8501` 即可使用。

## ☁️ Streamlit Cloud 部署

### 1. 推送代码到 GitHub

```bash
git init
git add .
git commit -m "feat: 情绪像素艺术品生成器"
git branch -M main
git remote add origin <你的GitHub仓库地址>
git push -u origin main
```

### 2. 在 Streamlit Cloud 部署

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 点击 "New app"
3. 选择你的 GitHub 仓库、分支（main）、主文件路径（`app.py`）
4. 点击 "Advanced settings" → "Secrets"，填入：

```toml
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxx"
SITE_URL = "https://你的应用名.streamlit.app"
```

5. 点击 "Deploy!"

### 3. 更新部署

每次 `git push` 到 main 分支，Streamlit Cloud 会自动重新部署。

## 📁 项目结构

```
project/
├── app.py                 # 主应用（单文件）
├── requirements.txt       # Python 依赖
├── README.md              # 项目说明
└── .streamlit/
    └── secrets.toml       # API Key 配置模板
```

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| Web框架 | Streamlit |
| AI API | DeepSeek (兼容 OpenAI 接口) |
| 图像处理 | Pillow |
| 二维码 | qrcode |
| 哈希 | hashlib (SHA256) |

## ❤️ 异常处理

应用具有完善的降级机制：

- **无 API Key** → 自动使用模拟数据，功能完整可用
- **API 调用失败** → 优雅降级，应用绝不崩溃
- **空输入** → 友好提示而非报错

## 📄 开源协议

MIT License
