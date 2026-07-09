"""
============================================================
 情绪像素 · 心情艺术品
 Emotion Pixel - Mood Art Generator
============================================================

一个将心情文字转化为像素画、AI诗句和情绪指纹的Streamlit应用。
使用 DeepSeek API 进行情绪分析和诗句生成。
使用 Pollinations.ai 免费 API 生成二次元插画。
"""

# ============================================================
# 导入模块
# ============================================================
import streamlit as st
import hashlib
import json
import io
import base64
import os
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont

import random
import requests

# ============================================================
# 页面配置（必须是第一个Streamlit命令）
# ============================================================
st.set_page_config(
    page_title="情绪像素 · 心情艺术品",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="auto",
)

# ============================================================
# OpenAI 客户端初始化（用于 DeepSeek API）
# ============================================================
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=st.secrets.get("DEEPSEEK_API_KEY", ""),
        base_url="https://api.deepseek.com/v1",
    )
    api_available = bool(st.secrets.get("DEEPSEEK_API_KEY", ""))
except Exception:
    client = None
    api_available = False

# ============================================================
# 跨平台中文字体加载
# ============================================================
@st.cache_resource
def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    按优先级尝试多个平台的中文字体路径，返回可用的字体对象。
    缓存结果以避免每次生成卡片都重新查找。
    """
    candidate_paths = [
        # Windows
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux / Streamlit Cloud (Debian)
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    # 终极降级：PIL 默认字体（不支持中文但不会崩溃）
    return ImageFont.load_default()


def _load_poem_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(20)

def _load_label_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(14)

def _load_mono_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """等宽字体用于指纹显示"""
    mono_paths = [
        "C:/Windows/Fonts/consola.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for path in mono_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, 16)
    return ImageFont.load_default()


# ============================================================
# 常量定义
# ============================================================

# 8 个情绪维度（Plutchik 情绪轮）
EMOTIONS = ["快乐", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "期待", "信任"]

# 每个情绪对应的显示颜色（十六进制）
EMOTION_COLORS = {
    "快乐": "#FFD93D",
    "悲伤": "#4A69BD",
    "愤怒": "#E55039",
    "恐惧": "#6A0572",
    "惊讶": "#F3A683",
    "厌恶": "#78A178",
    "期待": "#F19066",
    "信任": "#A8E06C",
}

# 站点 URL
SITE_URL = "https://emotion-pixel.streamlit.app"

# ============================================================
# 二次元插画随机元素库
# ============================================================

EMOTION_ANIME_STYLES = {
    "快乐": {"cn": "温暖阳光,柔和光晕,治愈系",
             "en": "warm sunlight, soft glow, healing atmosphere, golden lighting"},
    "悲伤": {"cn": "细雨,静谧,淡蓝忧伤",
             "en": "gentle rain, quiet solitude, soft blue melancholy, tears"},
    "愤怒": {"cn": "戏剧性光影,烈焰红,激烈",
             "en": "dramatic lighting, intense red, storm, fierce expression"},
    "恐惧": {"cn": "迷雾,神秘紫,暗影",
             "en": "misty darkness, mysterious purple fog, shadowy, horror"},
    "惊讶": {"cn": "魔法星光,明亮爆发,奇幻",
             "en": "magical sparkle, bright burst, wonder, surprise expression"},
    "厌恶": {"cn": "灰绿色调,疏离,朦胧",
             "en": "muted green, distant haze, faded colors, disgust"},
    "期待": {"cn": "金色时光,希望曙光,珊瑚色天空",
             "en": "golden hour, hopeful sunrise, coral sky, anticipation"},
    "信任": {"cn": "宁静草地,柔嫩绿色,和谐",
             "en": "peaceful meadow, gentle green, harmony, trust"},
}

ART_STYLES = [
    "Ghibli style, hand-drawn animation, soft watercolor background",
    "90s retro anime, cel shading, grainy film texture, nostalgic",
    "cyberpunk anime, neon lights, futuristic city, holographic effects",
    "shoujo manga style, sparkly eyes, floral frames, pastel romance",
    "Makoto Shinkai style, photorealistic lighting, lens flare, vibrant sky",
    "watercolor illustration, ink wash, flowing brush strokes, poetic",
    "chibi kawaii style, cute, big head, pastel colors, adorable",
    "dark fantasy anime, gothic, intricate details, dramatic shadows",
    "ukiyo-e inspired, Japanese woodblock print style, flat colors, bold lines",
    "vaporwave aesthetic, synthwave, retro 80s, glitch effects, neon pink",
    "minimalist line art, ink sketch, black and white with single color accent",
    "pop art anime, bold halftone dots, comic panel style, vibrant",
]

SCENE_TYPES = [
    "cherry blossom garden with petals falling in spring breeze",
    "quiet classroom at sunset, golden light through windows",
    "rooftop of a tall building overlooking a neon city at night",
    "seaside cliff with waves crashing and seagulls circling",
    "ancient shrine gate in a misty bamboo forest",
    "cozy attic room filled with books, warm lamp light, rainy outside",
    "train platform at dusk, empty bench, distant mountains",
    "flower field under starry night sky with shooting stars",
    "underwater palace with glowing jellyfish and coral reefs",
    "abandoned overgrown greenhouse with sunlight streaming through glass",
    "busy festival street with lanterns, fireworks in the night sky",
    "snow-covered village with warm lights from cottage windows",
    "floating sky islands connected by rope bridges, clouds below",
    "vintage arcade room with CRT screens and neon reflections",
    "dreamlike mirror dimension with floating clocks and endless stairs",
]

CAMERA_ANGLES = [
    "close-up portrait, focusing on eyes and expression",
    "full body shot, dynamic pose, wind blowing hair and clothes",
    "medium shot, sitting casually, looking off to the side",
    "wide angle landscape, tiny character in vast scenery",
    "dutch angle, tilted camera, dramatic tension",
    "over-the-shoulder view, looking at distant scenery",
    "low angle, looking up, heroic, dramatic sky behind",
    "bird's eye view, looking down, detailed environment",
    "side profile silhouette against bright background",
    "reflection in a puddle or mirror, dreamlike double image",
]

COLOR_PALETTES = [
    "soft warm pastel colors, gentle and dreamy",
    "high saturation, vivid colors, bold and energetic",
    "monochromatic blue tones, melancholic and calm",
    "golden hour warm oranges and yellows, nostalgic",
    "muted earth tones, natural and grounded",
    "neon purple and cyan, electric and futuristic",
    "soft pink and mint green, cute and refreshing",
    "deep crimson and black, intense and dramatic",
    "cream and sepia, vintage photograph feel",
    "rainbow spectrum, magical and fantastical",
]

# ============================================================
# 工具函数
# ============================================================

def get_mock_scores(user_text: str) -> dict:
    """生成模拟情绪分数（API 降级方案）。"""
    seed = sum(ord(c) for c in user_text)
    rng = random.Random(seed)
    return {emotion: rng.randint(0, 10) for emotion in EMOTIONS}


def analyze_emotion(user_text: str, use_mock: bool = False) -> dict:
    """调用 DeepSeek API 分析 8 个情绪维度分数（0-10）。"""
    if use_mock or not api_available:
        if not api_available:
            st.warning("⚠️ 未配置 DeepSeek API Key，使用模拟数据。")
        return get_mock_scores(user_text)
    try:
        system_prompt = (
            "你是一个专业的情绪分析专家。请分析用户输入的文字，"
            "对以下8个情绪维度进行评分（0-10的整数）：\n"
            "快乐(happy)、悲伤(sad)、愤怒(anger)、恐惧(fear)、"
            "惊讶(surprise)、厌恶(disgust)、期待(anticipation)、信任(trust)\n\n"
            "请严格按以下JSON格式返回，不要包含任何其他文字：\n"
            '{"快乐": 7, "悲伤": 2, "愤怒": 1, "恐惧": 0, "惊讶": 3, "厌恶": 0, "期待": 6, "信任": 5}'
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请分析以下文字的情绪：{user_text}"},
            ],
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"},
            timeout=15,
        )
        raw = response.choices[0].message.content.strip()
        scores = json.loads(raw)
        return {e: max(0, min(10, int(scores.get(e, 5)))) for e in EMOTIONS}
    except Exception as e:
        st.warning(f"⚠️ 情绪分析API调用失败（{str(e)[:50]}），已降级使用模拟数据。")
        return get_mock_scores(user_text)


def generate_poem(user_text: str, scores: dict, use_mock: bool = False) -> str:
    """调用 DeepSeek API 生成两句押韵诗（每句 ≤10 字）。"""
    if use_mock or not api_available:
        return get_mock_poem(scores)
    try:
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_emotions = f"{sorted_emotions[0][0]}({sorted_emotions[0][1]}分)和{sorted_emotions[1][0]}({sorted_emotions[1][1]}分)"
        system_prompt = (
            "你是一个才华横溢的诗人。请根据用户的情绪分析结果创作两行诗。\n"
            "要求：\n1. 每行不超过10个汉字\n2. 两行的最后一个字必须押韵\n"
            "3. 诗句要优美、有诗意，体现用户的主导情绪\n4. 不要使用标点符号\n\n"
            '请严格按以下JSON格式返回：\n{"line1": "第一行诗", "line2": "第二行诗"}'
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户心情：{user_text}\n主导情绪：{top_emotions}\n完整情绪分数：{scores}"},
            ],
            temperature=0.9, max_tokens=150,
            response_format={"type": "json_object"}, timeout=15,
        )
        data = json.loads(response.choices[0].message.content.strip())
        return f"{data.get('line1', '').strip()}\n{data.get('line2', '').strip()}"
    except Exception as e:
        st.warning(f"⚠️ 诗句生成API调用失败（{str(e)[:50]}），已降级使用默认诗句。")
        return get_mock_poem(scores)


def get_mock_poem(scores: dict) -> str:
    """根据主导情绪返回预设诗句。"""
    top_emotion = max(scores, key=scores.get)
    poems = {
        "快乐": "阳光洒满心房暖\n笑意盈盈岁月安",
        "悲伤": "细雨如丝落窗前\n心事重重夜未眠",
        "愤怒": "烈焰翻腾胸中烧\n怒涛拍岸风雨摇",
        "恐惧": "暗影重重心微颤\n迷雾深处步履慢",
        "惊讶": "奇境乍现眼前亮\n惊叹之余心已往",
        "厌恶": "浊浪排空心渐远\n清流自在寻芳甸",
        "期待": "星辰大海梦为马\n明日花开满枝丫",
        "信任": "绿荫如盖护心安\n相知相守两不厌",
    }
    return poems.get(top_emotion, "心有万象皆成画\n情如像素亦生花")


def draw_pixel_art(scores: dict) -> Image.Image:
    """
    使用 Pillow 绘制 8×8 情绪像素画。
    8 个情绪各占 2×2 像素区域，根据分数决定填充数量。
    加入细网格线提高颜色区分度。
    """
    pixel_size = 25
    grid_size = 8
    canvas_size = pixel_size * grid_size  # 200×200
    img = Image.new("RGB", (canvas_size, canvas_size), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    row1_emotions = ["快乐", "悲伤", "愤怒", "恐惧"]
    row2_emotions = ["惊讶", "厌恶", "期待", "信任"]

    for row_idx, emotion_row in enumerate([row1_emotions, row2_emotions]):
        for col_idx, emotion in enumerate(emotion_row):
            score = scores.get(emotion, 0)
            if score <= 3:
                fill_count = 1
            elif score <= 5:
                fill_count = 2
            elif score <= 7:
                fill_count = 3
            else:
                fill_count = 4

            color = EMOTION_COLORS[emotion]
            base_grid_x = col_idx * 2
            base_grid_y = row_idx * 4

            positions = [
                (base_grid_x, base_grid_y),
                (base_grid_x + 1, base_grid_y),
                (base_grid_x, base_grid_y + 1),
                (base_grid_x + 1, base_grid_y + 1),
            ]

            for i in range(fill_count):
                gx, gy = positions[i]
                x1, y1 = gx * pixel_size, gy * pixel_size
                x2, y2 = x1 + pixel_size, y1 + pixel_size
                draw.rectangle([x1, y1, x2 - 1, y2 - 1], fill=color)

            for i in range(fill_count, 4):
                gx, gy = positions[i]
                x1, y1 = gx * pixel_size, gy * pixel_size
                x2, y2 = x1 + pixel_size - 1, y1 + pixel_size - 1
                draw.rectangle([x1, y1, x2, y2], outline="#E0E0E0", width=1)

    # ---- 细网格线：每个 2×2 情绪区块之间添加 1px 分隔线 ----
    grid_color = "#CCCCCC"
    # 竖线：每隔 2 个格子在 pixel 边界画线
    for cx in range(2, grid_size, 2):
        x = cx * pixel_size
        draw.line([(x, 0), (x, canvas_size)], fill=grid_color, width=1)
    # 横线：第 2 行开始画一条
    draw.line([(0, 4 * pixel_size), (canvas_size, 4 * pixel_size)], fill=grid_color, width=1)

    return img


def generate_fingerprint(scores: dict) -> str:
    """情绪指纹：8 个分数拼接 → SHA256 → 前 8 位。"""
    ordered_scores = [str(scores[emotion]) for emotion in EMOTIONS]
    raw_string = "-".join(ordered_scores)
    return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()[:8].upper()


def generate_anime_art(scores: dict, user_text: str) -> Image.Image:
    """
    调用 Pollinations.ai 免费 API 生成二次元插画。
    每次从随机元素库中抽取不同组合，确保每张图都独一无二。
    支持缓存——同一指纹+文字不重复请求。
    """
    # ---- 缓存检查 ----
    fingerprint = generate_fingerprint(scores)
    cache_key = f"{fingerprint}_{user_text[:30]}"
    if "anime_cache" not in st.session_state:
        st.session_state.anime_cache = {}
    if cache_key in st.session_state.anime_cache:
        return st.session_state.anime_cache[cache_key]

    try:
        seed = sum(ord(c) for c in fingerprint) + sum(ord(c) for c in user_text[:20])
        rng = random.Random(seed)
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_emotion = sorted_emotions[0][0]
        second_emotion = sorted_emotions[1][0]
        style_primary = EMOTION_ANIME_STYLES[top_emotion]
        style_secondary = EMOTION_ANIME_STYLES[second_emotion]

        prompt_parts = [
            "anime illustration, 2D, masterpiece, high quality, detailed",
            rng.choice(ART_STYLES),
            f"primary mood: {style_primary['en']}",
            f"secondary mood: {style_secondary['en']}",
            rng.choice(SCENE_TYPES),
            rng.choice(CAMERA_ANGLES),
            rng.choice(COLOR_PALETTES),
            "emotional expression, beautiful composition",
            f"atmosphere: {user_text.strip()[:80]}",
        ]
        prompt = ", ".join(prompt_parts)
        encoded_prompt = urllib.parse.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            "?width=512&height=512&nologo=true&seed=" + str(seed)
        )
        response = requests.get(url, timeout=60)
        if response.status_code == 200 and len(response.content) > 0:
            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            st.session_state.anime_cache[cache_key] = img  # 写入缓存
            return img
        raise Exception(f"HTTP {response.status_code}")
    except Exception as e:
        st.warning(f"🎨 二次元插画生成失败（{str(e)[:40]}），显示占位图。")
        return _anime_placeholder(top_emotion if "top_emotion" in dir() else "快乐")


def _anime_placeholder(emotion_name: str) -> Image.Image:
    """API 失败时的降级占位图。"""
    w, h, color = 512, 512, EMOTION_COLORS.get(emotion_name, "#CCCCCC")
    img = Image.new("RGB", (w, h), color)
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 120))
    img = img.convert("RGBA")
    img.paste(overlay, (0, 0), overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    font_big = _load_font(36)
    font_small = _load_font(18)
    draw.text((w // 2 - 100, h // 2 - 40), f"✨ {emotion_name} ✨", fill="#333333", font=font_big)
    draw.text((w // 2 - 140, h // 2 + 20), "二次元插画生成中...", fill="#666666", font=font_small)
    draw.text((w // 2 - 100, h // 2 + 55), "请稍后重试", fill="#888888", font=font_small)
    return img


def generate_qrcode(target_url: str) -> Image.Image:
    """生成指向指定 URL 的二维码图片。"""
    import qrcode
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=6, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    return qr.make_image(fill_color="#333333", back_color="#FFFFFF").convert("RGB")


def img_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    """PIL 图像 → Base64 字符串。"""
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def base64_to_img(b64_string: str) -> Image.Image:
    """Base64 字符串 → PIL 图像。"""
    return Image.open(io.BytesIO(base64.b64decode(b64_string)))


def create_share_card(
    pixel_art: Image.Image,
    anime_art: Image.Image | None,
    poem: str,
    fingerprint: str,
    qr_img: Image.Image,
) -> Image.Image:
    """创建分享卡片图片（700×420，白底）。"""
    card_w, card_h = 700, 420
    card = Image.new("RGB", (card_w, card_h), "#FFFFFF")
    card_draw = ImageDraw.Draw(card)

    card.paste(pixel_art.resize((100, 100), Image.NEAREST), (30, 130))
    if anime_art is not None:
        card.paste(anime_art.resize((100, 100), Image.LANCZOS), (140, 130))

    font_poem = _load_poem_font()
    font_mono = _load_mono_font()
    font_label = _load_label_font()

    card_draw.text((280, 40), "🎨 情绪像素 · 心情艺术品", fill="#333333", font=font_label)
    y_offset = 100
    for line in poem.strip().split("\n"):
        card_draw.text((280, y_offset), line, fill="#444444", font=font_poem)
        y_offset += 32

    card_draw.text((280, 200), f"情绪指纹：{fingerprint}", fill="#888888", font=font_mono)
    card.paste(qr_img.resize((80, 80), Image.NEAREST), (30, 300))
    card_draw.text((120, 330), "扫码体验 →", fill="#AAAAAA", font=font_label)
    card_draw.line([(20, 398), (680, 398)], fill="#EEEEEE", width=1)
    card_draw.text((220, 400), "用像素记录每一刻的心情 ✨", fill="#CCCCCC", font=font_label)
    return card


# ============================================================
# 初始化会话状态
# ============================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "anime_cache" not in st.session_state:
    st.session_state.anime_cache = {}

# ============================================================
# 标题与介绍
# ============================================================
st.title("🎨 情绪像素 · 心情艺术品")
st.markdown("写下你的心情，AI 将为你创作一幅独一无二的情绪像素画 ✨")

# ============================================================
# 主界面：心情输入（使用 form 以支持 Enter 提交）
# ============================================================
with st.form(key="mood_form", clear_on_submit=False):
    user_input = st.text_area(
        "💬 今天心情如何？",
        placeholder="比如：今天阳光很好，走在路上收到了意外的礼物，心里暖暖的...",
        height=100,
        max_chars=500,
        key="mood_input",
    )
    col_btn, col_tip, _, _ = st.columns([1, 2, 1, 1])
    with col_btn:
        submitted = st.form_submit_button(
            "✨ 生成",
            type="primary",
            use_container_width=True,
        )
    with col_tip:
        st.caption("💡 提示：按 Ctrl+Enter 也可以快速生成")

# ============================================================
# 处理生成逻辑（带进度条 + 并行 API 调用）
# ============================================================
if submitted:
    if not user_input or not user_input.strip():
        st.warning("💡 请先输入你的心情文字再生成哦～")
    else:
        text = user_input.strip()

        # 进度条 + 状态文字
        progress_bar = st.progress(0)
        status_text = st.empty()

        # ---- 步骤 1：情绪分析（必须先完成，后续依赖它）----
        status_text.text("🎨 AI正在分析你的情绪...")
        progress_bar.progress(5)
        scores = analyze_emotion(text)
        progress_bar.progress(20)

        # ---- 步骤 2：并行 —— 诗句 + 二次元插画 + 像素画 ----
        status_text.text("📝 AI正在创作诗句... 🎌 AI正在绘制二次元插画...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_poem = executor.submit(generate_poem, text, scores)
            future_anime = executor.submit(generate_anime_art, scores, text)
            # 像素画是本计算，同时执行
            future_pixel = executor.submit(draw_pixel_art, scores)

            poem = future_poem.result()
            progress_bar.progress(50)
            anime_art = future_anime.result()
            progress_bar.progress(75)
            pixel_art = future_pixel.result()

        # ---- 步骤 3：情绪指纹（瞬间完成）----
        status_text.text("🔐 生成情绪指纹...")
        fingerprint = generate_fingerprint(scores)
        progress_bar.progress(100)
        status_text.text("✅ 完成！")
        progress_bar.empty()

        # ---- 保存到历史记录 ----
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input": text,
            "scores": scores,
            "poem": poem,
            "fingerprint": fingerprint,
            "pixel_art_b64": img_to_base64(pixel_art),
            "anime_art_b64": img_to_base64(anime_art),
        }
        st.session_state.history.append(record)
        st.rerun()


# ============================================================
# 显示最新结果（或首次使用引导）
# ============================================================
if st.session_state.history:
    latest = st.session_state.history[-1]
    st.divider()
    st.subheader("✨ 你的情绪艺术品")

    col_left, col_mid, col_right = st.columns([1, 1, 2])

    with col_left:
        pixel_art_img = base64_to_img(latest["pixel_art_b64"])
        st.image(pixel_art_img.resize((200, 200), Image.NEAREST),
                 caption="🎨 情绪像素画", use_container_width=True)

    with col_mid:
        anime_b64 = latest.get("anime_art_b64", "")
        if anime_b64:
            st.image(base64_to_img(anime_b64).resize((200, 200), Image.LANCZOS),
                     caption="🎌 AI二次元插画", use_container_width=True)
        else:
            st.info("🎌 暂无插画\n\n重新生成即可获得二次元插画")

    with col_right:
        st.markdown("**📊 情绪分析**")
        for emotion in EMOTIONS:
            score = latest["scores"][emotion]
            color_hex = EMOTION_COLORS[emotion]
            st.markdown(
                f"""<div style="display:flex;align-items:center;margin-bottom:4px;">
                    <span style="width:40px;font-size:13px;">{emotion}</span>
                    <div style="flex:1;background:#eee;height:14px;border-radius:7px;margin:0 8px;">
                        <div style="width:{score*10}%;background:{color_hex};height:100%;border-radius:7px;"></div>
                    </div>
                    <span style="width:24px;font-size:13px;text-align:right;">{score}</span></div>""",
                unsafe_allow_html=True)

        st.markdown("**📝 AI情绪诗**")
        st.markdown(
            f"""<div style="background:#F8F9FA;border-left:4px solid #6C5CE7;padding:12px 16px;
                        border-radius:4px;font-size:18px;line-height:2;margin:8px 0;">
                {latest['poem'].replace(chr(10), '<br>')}</div>""",
            unsafe_allow_html=True)

        st.markdown("**🔐 情绪指纹**")
        st.code(latest["fingerprint"], language=None)

    # ---- 分享卡片 ----
    st.divider()
    share_col, _, _, _ = st.columns([1, 1, 1, 1])
    with share_col:
        anime_b64_share = latest.get("anime_art_b64", "")
        anime_img_share = base64_to_img(anime_b64_share) if anime_b64_share else None
        qr_url = st.secrets.get("SITE_URL", SITE_URL)
        share_card = create_share_card(pixel_art_img, anime_img_share,
                                       latest["poem"], latest["fingerprint"],
                                       generate_qrcode(qr_url))
        card_buffer = io.BytesIO()
        share_card.save(card_buffer, format="PNG", quality=95)
        st.download_button(
            label="📤 下载分享卡片",
            data=card_buffer.getvalue(),
            file_name=f"情绪像素_{latest['fingerprint']}.png",
            mime="image/png",
            use_container_width=True,
        )

else:
    # ---- 首次使用引导 / 空状态 ----
    st.divider()
    st.subheader("👋 欢迎来到情绪像素！")
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#F8F9FA,#E8ECEF);border-radius:12px;
                    padding:24px;margin:16px 0;">
        <h4 style="margin-top:0;">✨ 三步创作你的情绪艺术品</h4>
        <ol>
            <li><b>写下心情</b> — 在上方输入框写下你现在的心情或今天发生的事</li>
            <li><b>点击生成</b> — AI 会分析你的情绪，创作像素画 + 二次元插画 + 诗句</li>
            <li><b>分享留念</b> — 下载分享卡片，保存你的情绪指纹</li>
        </ol>
        <p style="color:#888;margin-bottom:0;">💡 试试输入：「<i>今天和好朋友一起看了日落，心里暖暖的</i>」</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 演示卡片
    st.markdown("**🎨 效果预览**")
    demo_scores = {"快乐": 8, "悲伤": 1, "愤怒": 0, "恐惧": 0, "惊讶": 3, "厌恶": 0, "期待": 5, "信任": 6}
    demo_pixel = draw_pixel_art(demo_scores)
    demo_anime = _anime_placeholder("快乐")
    demo_card = create_share_card(
        demo_pixel, demo_anime,
        "日落余晖映心间\n暖风轻拂岁月甜",
        generate_fingerprint(demo_scores),
        generate_qrcode(SITE_URL),
    )
    st.image(demo_card, caption="示例分享卡片", use_container_width=True)


# ============================================================
# 侧边栏：情绪画廊 + 导出/导入
# ============================================================
with st.sidebar:
    st.header("🖼️ 情绪画廊")

    if st.session_state.history:
        # ---- 导出历史 ----
        export_json = json.dumps(st.session_state.history, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 导出历史 (JSON)",
            data=export_json,
            file_name=f"情绪像素_历史记录_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )

        # ---- 导入历史 ----
        uploaded_file = st.file_uploader(
            "📤 导入历史",
            type=["json"],
            key="import_history",
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            try:
                imported = json.loads(uploaded_file.read().decode("utf-8"))
                if isinstance(imported, list):
                    st.session_state.history.extend(imported)
                    st.success(f"✅ 已导入 {len(imported)} 条记录！")
                    st.rerun()
                else:
                    st.error("❌ 文件格式不正确")
            except Exception as e:
                st.error(f"❌ 导入失败：{e}")

        # ---- 清空历史 ----
        if st.button("🗑️ 清空所有历史", use_container_width=True, type="secondary"):
            st.session_state.history = []
            st.session_state.anime_cache = {}
            st.rerun()

    st.divider()

    if not st.session_state.history:
        st.info("📭 暂无记录\n\n输入心情并点击「生成」来创建第一件艺术品吧！")
    else:
        reversed_history = list(reversed(st.session_state.history))
        for idx, record in enumerate(reversed_history):
            actual_idx = len(st.session_state.history) - 1 - idx
            pixel_img = base64_to_img(record["pixel_art_b64"])

            with st.expander(
                f"🎨 {record['time']} — {record['poem'].split(chr(10))[0]}...",
                expanded=(idx == 0),
            ):
                gal_left, gal_right = st.columns(2)
                with gal_left:
                    st.image(pixel_img.resize((120, 120), Image.NEAREST),
                             caption="像素画", use_container_width=False)
                with gal_right:
                    anime_b64_hist = record.get("anime_art_b64", "")
                    if anime_b64_hist:
                        st.image(base64_to_img(anime_b64_hist).resize((120, 120), Image.LANCZOS),
                                 caption="二次元", use_container_width=False)
                    else:
                        st.caption("暂无插画")

                st.markdown(f"**诗句：**\n>{record['poem']}")
                st.caption(f"指纹：{record['fingerprint']}")
                scores_text = " · ".join([f"{e}{record['scores'][e]}" for e in EMOTIONS])
                st.caption(scores_text)

                anime_hist = base64_to_img(anime_b64_hist) if anime_b64_hist else None
                qr_url = st.secrets.get("SITE_URL", SITE_URL)
                share_card = create_share_card(pixel_img, anime_hist,
                                               record["poem"], record["fingerprint"],
                                               generate_qrcode(qr_url))
                card_buffer = io.BytesIO()
                share_card.save(card_buffer, format="PNG", quality=95)
                st.download_button(
                    label="📤 下载此卡片",
                    data=card_buffer.getvalue(),
                    file_name=f"情绪像素_{record['fingerprint']}.png",
                    mime="image/png",
                    key=f"dl_{actual_idx}",
                    use_container_width=True,
                )


# ============================================================
# 页脚（增强信息）
# ============================================================
st.divider()
footer_cols = st.columns([1, 1, 1])
with footer_cols[0]:
    st.caption(f"📊 历史记录：{len(st.session_state.history)} 条")
with footer_cols[1]:
    if st.session_state.history:
        st.caption(f"🕐 最近生成：{st.session_state.history[-1]['time']}")
with footer_cols[2]:
    st.caption("[🐙 GitHub](https://github.com/2090meng/project)")
st.caption("🎨 情绪像素 · 心情艺术品 | 用像素记录每一刻的心情 | Powered by DeepSeek + Streamlit")
