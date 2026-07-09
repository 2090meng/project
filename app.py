"""
============================================================
 情绪像素 · 心情艺术品
 Emotion Pixel - Mood Art Generator
============================================================

将心情文字转化为像素画、二次元插画、AI诗句和情绪指纹的Streamlit应用。
- DeepSeek API：情绪分析、诗句生成、诗意命名、情绪散文
- Pollinations.ai：免费二次元插画
- 纯 CSS 动态渐变 + 飘落粒子动画：情绪背景
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
import time
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
    initial_sidebar_state="collapsed",
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
# 外部 API Key 检查
# ============================================================
# （Unsplash 和 GIPHY 已移除，改用纯 CSS 动态背景）

# ============================================================
# 跨平台中文字体加载
# ============================================================
@st.cache_resource
def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """跨平台加载中文字体，缓存结果。"""
    candidate_paths = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _load_poem_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(20)

def _load_label_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(14)

def _load_mono_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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

EMOTIONS = ["快乐", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "期待", "信任"]

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

SITE_URL = "https://emotion-pixel.streamlit.app"

# ============================================================
# 纯 CSS 动态背景：情绪 → 渐变 + 飘落粒子动画
# 无需任何外部 API，完全免费，永不失效
# ============================================================
WALLPAPER_GRADIENTS = {
    "快乐": "linear-gradient(135deg, #FFF8E1, #FFF3CD, #FFECB3)",
    "悲伤": "linear-gradient(135deg, #E3E8F0, #CED6E0, #A4B0BE)",
    "愤怒": "linear-gradient(135deg, #FFE0DC, #F8CECC, #E8B4B0)",
    "恐惧": "linear-gradient(135deg, #F0E6F3, #E0CCE5, #C9A8D4)",
    "惊讶": "linear-gradient(135deg, #FFF0E8, #FFE4D0, #FCD5B0)",
    "厌恶": "linear-gradient(135deg, #E8EDE4, #D4DDCE, #B8C7AE)",
    "期待": "linear-gradient(135deg, #FFF0E5, #FFE0C8, #FDD0A8)",
    "信任": "linear-gradient(135deg, #E8F5E0, #D4EDC8, #B8E0A0)",
}

# 飘落粒子颜色（对应情绪色 + 白色）
PARTICLE_COLORS = {
    "快乐": ["#FFD93D", "#FFE88A", "#FFECB3", "#FFF"],
    "悲伤": ["#4A69BD", "#7B93D4", "#CED6E0", "#FFF"],
    "愤怒": ["#E55039", "#F08070", "#F8CECC", "#FFF"],
    "恐惧": ["#6A0572", "#9B5DA8", "#E0CCE5", "#FFF"],
    "惊讶": ["#F3A683", "#F7C4AD", "#FFE4D0", "#FFF"],
    "厌恶": ["#78A178", "#A0BDA0", "#D4DDCE", "#FFF"],
    "期待": ["#F19066", "#F5B08A", "#FFE0C8", "#FFF"],
    "信任": ["#A8E06C", "#C1E98A", "#D4EDC8", "#FFF"],
}

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
# 工具函数 — 情绪分析 & 诗意命名 & 散文
# ============================================================

def get_mock_scores(user_text: str) -> dict:
    seed = sum(ord(c) for c in user_text)
    rng = random.Random(seed)
    return {emotion: rng.randint(0, 10) for emotion in EMOTIONS}


def analyze_emotion(user_text: str, use_mock: bool = False) -> dict:
    """DeepSeek API 分析 8 个情绪维度。"""
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
            temperature=0.3, max_tokens=200,
            response_format={"type": "json_object"}, timeout=15,
        )
        raw = response.choices[0].message.content.strip()
        scores = json.loads(raw)
        return {e: max(0, min(10, int(scores.get(e, 5)))) for e in EMOTIONS}
    except Exception as e:
        st.warning(f"⚠️ 情绪分析API调用失败（{str(e)[:50]}），已降级。")
        return get_mock_scores(user_text)


def generate_poem(user_text: str, scores: dict, use_mock: bool = False) -> str:
    """DeepSeek API 生成两句押韵诗（每句 ≤10 字）。"""
    if use_mock or not api_available:
        return get_mock_poem(scores)
    try:
        sorted_e = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_emotions = f"{sorted_e[0][0]}({sorted_e[0][1]}分)和{sorted_e[1][0]}({sorted_e[1][1]}分)"
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
        st.warning(f"⚠️ 诗句生成API调用失败（{str(e)[:50]}），已降级。")
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


# ============================================================
# Hero / 滚动动画 CSS 注入（全局）
# ============================================================

def inject_global_animations():
    """注入全站滚动淡入动画 + 呼吸光晕等高级 CSS。"""
    st.markdown(
        """
        <style>
        /* === 滚动淡入动画 === */
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInScale {
            from { opacity: 0; transform: scale(0.92); }
            to   { opacity: 1; transform: scale(1); }
        }
        @keyframes shimmer {
            0%   { background-position: -200% center; }
            100% { background-position: 200% center; }
        }
        @keyframes glowPulse {
            0%, 100% { box-shadow: 0 0 20px rgba(108,92,231,0.15); }
            50%      { box-shadow: 0 0 40px rgba(108,92,231,0.3); }
        }
        @keyframes floatSlow {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            33%      { transform: translateY(-10px) rotate(1deg); }
            66%      { transform: translateY(6px) rotate(-1deg); }
        }
        .animate-fade-in-up {
            animation: fadeInUp 0.8s ease forwards;
        }
        .animate-delay-1 { animation-delay: 0.15s; opacity: 0; }
        .animate-delay-2 { animation-delay: 0.3s;  opacity: 0; }
        .animate-delay-3 { animation-delay: 0.45s; opacity: 0; }
        .animate-delay-4 { animation-delay: 0.6s;  opacity: 0; }

        /* Hero 区域光晕 */
        .hero-glow {
            animation: glowPulse 3s ease-in-out infinite;
        }
        .hero-float {
            animation: floatSlow 6s ease-in-out infinite;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 情绪命名（继续）
# ============================================================


def emotion_namer(user_text: str, scores: dict, use_mock: bool = False) -> str:
    """DeepSeek API 生成诗意情绪命名（如「暖阳型·坚定温柔」）。"""
    if use_mock or not api_available:
        return _mock_emotion_name(scores)
    try:
        sorted_e = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        system_prompt = (
            "你是一位精通情绪美学的命名大师。请根据用户的情绪分析结果，"
            "创造一个诗意、独特的情绪类型名称。\n"
            "格式要求：\n"
            "1. 「自然意象词」+「型」+ · +「品质形容词+情绪形容词」\n"
            "2. 例如：「暖阳型·坚定温柔」「深海型·沉静隐忍」「极光型·好奇飞扬」\n"
            "3. 名称要独特、有诗意，避免陈词滥调\n"
            "4. 3-6个汉字\n\n"
            '请严格按JSON格式返回：\n'
            '{"name": "暖阳型·坚定温柔"}'
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",
                 "content": f"用户心情：{user_text}\n主导情绪：{sorted_e[0][0]}{sorted_e[0][1]}分\n"
                             f"次主导：{sorted_e[1][0]}{sorted_e[1][1]}分\n完整分数：{scores}"},
            ],
            temperature=0.9, max_tokens=80,
            response_format={"type": "json_object"}, timeout=15,
        )
        data = json.loads(response.choices[0].message.content.strip())
        return data.get("name", _mock_emotion_name(scores)).strip()
    except Exception:
        return _mock_emotion_name(scores)


def _mock_emotion_name(scores: dict) -> str:
    names = {
        "快乐": "暖阳型·明媚轻盈",
        "悲伤": "深海型·沉静隐忍",
        "愤怒": "烈焰型·炽热果敢",
        "恐惧": "迷雾型·敏感深邃",
        "惊讶": "极光型·好奇飞扬",
        "厌恶": "青苔型·疏离自持",
        "期待": "晨曦型·温柔守候",
        "信任": "绿荫型·坚定和畅",
    }
    return names.get(max(scores, key=scores.get), "星河型·复杂丰盈")


def emotion_prose(user_text: str, scores: dict, emotion_name: str, use_mock: bool = False) -> str:
    """DeepSeek API 生成情绪散文（80-120字）。"""
    if use_mock or not api_available:
        return _mock_prose(scores, emotion_name)
    try:
        sorted_e = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        system_prompt = (
            "你是一位情感细腻的散文作家。请根据用户的情绪数据，用文学化的语言"
            "写一段80-120字的散文，像一面镜子让读者感到被深度理解。\n"
            "要求：优美、有画面感、治愈、不评判。使用第二人称「你」。\n\n"
            '请严格按JSON格式返回：\n'
            '{"prose": "你的心像..."}'
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",
                 "content": f"用户心情：{user_text}\n情绪类型：{emotion_name}\n"
                             f"主导：{sorted_e[0][0]}{sorted_e[0][1]}分，"
                             f"次主导：{sorted_e[1][0]}{sorted_e[1][1]}分\n完整分数：{scores}"},
            ],
            temperature=0.85, max_tokens=250,
            response_format={"type": "json_object"}, timeout=20,
        )
        data = json.loads(response.choices[0].message.content.strip())
        return data.get("prose", _mock_prose(scores, emotion_name)).strip()
    except Exception:
        return _mock_prose(scores, emotion_name)


def _mock_prose(scores: dict, emotion_name: str) -> str:
    top = max(scores, key=scores.get)
    prose_map = {
        "快乐": "你的心像春日午后的阳光，暖暖地洒在每一寸肌肤上。那些细小的欢愉——风吹过发梢、鸟鸣划过天空——都在提醒你，幸福其实很简单。不必着急，让这份轻盈在心底多停留一会儿。",
        "悲伤": "你心里有一片安静的海，潮水缓缓涨落。允许自己放慢脚步，允许泪水滑落。有些情绪不需要解释，它只是提醒你——你曾经在乎过、期待过、爱过。雨过后，天总会亮。",
        "愤怒": "你胸腔里有一团火在燃烧。它不是说你不好的东西——它是你的边界被触碰、你的坚持被看见的证据。让火焰照亮你真正想要守护的东西，而不是焚毁你珍惜的一切。",
        "恐惧": "你走在迷雾里，脚下的路看不清方向。这种不确定感让人心慌，但它也让你比任何人都更能感知到细微的风吹草动。你不是胆怯，你只是比旁人更加敏感和清醒。",
        "惊讶": "你的世界今天被打翻了一盒颜料——有些颜色陌生、有些刺眼、有些让人心跳加速。不必急着归类，奇遇总是穿着未知的外衣。你眼里的光亮，正是此刻最珍贵的礼物。",
        "厌恶": "你本能地想要后退一步。这不是逃避，是你内心的雷达在告诉你——有些事物不适合你。保护自己、保持距离，是完全允许的。在后退的空间里，你能更清楚地看见什么才是真正重要的。",
        "期待": "你站在黎明的门槛上，天边泛起暖暖的霞光。未来还没有到来，但它正在来的路上。你心里那根小小的火苗——关于梦想、关于明天——请一定好好地守护它。它值得被温柔以待。",
        "信任": "你就像一棵深深扎根的树，风吹过、雨打过，依然安静地站立。这种安定感是你和世界之间最温柔的契约。相信你自己——你比想象中更值得被依靠，也更值得去依靠别人。",
    }
    return prose_map.get(top, "你的情绪像一幅未干的油画，各种颜色交融、渗透、等待被解读。不必急着定义自己——你今天的所有感受，都是这幅画上不可或缺的一笔。")


# ============================================================
# 工具函数 — 像素画、指纹、二次元插画
# ============================================================

def draw_pixel_art(scores: dict) -> Image.Image:
    """8×8 情绪像素画，含细网格线。"""
    pixel_size, grid_size = 25, 8
    canvas_size = pixel_size * grid_size
    img = Image.new("RGB", (canvas_size, canvas_size), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    row1 = ["快乐", "悲伤", "愤怒", "恐惧"]
    row2 = ["惊讶", "厌恶", "期待", "信任"]

    for row_idx, emotion_row in enumerate([row1, row2]):
        for col_idx, emotion in enumerate(emotion_row):
            score = scores.get(emotion, 0)
            if score <= 3:    fill_count = 1
            elif score <= 5:  fill_count = 2
            elif score <= 7:  fill_count = 3
            else:             fill_count = 4

            color = EMOTION_COLORS[emotion]
            base_gx, base_gy = col_idx * 2, row_idx * 4
            positions = [
                (base_gx, base_gy), (base_gx + 1, base_gy),
                (base_gx, base_gy + 1), (base_gx + 1, base_gy + 1),
            ]
            for i in range(fill_count):
                gx, gy = positions[i]
                x1, y1 = gx * pixel_size, gy * pixel_size
                draw.rectangle([x1, y1, x1 + pixel_size - 1, y1 + pixel_size - 1], fill=color)
            for i in range(fill_count, 4):
                gx, gy = positions[i]
                x1, y1 = gx * pixel_size, gy * pixel_size
                draw.rectangle([x1, y1, x1 + pixel_size - 1, y1 + pixel_size - 1],
                               outline="#E0E0E0", width=1)

    # 网格线
    for cx in range(2, grid_size, 2):
        draw.line([(cx * pixel_size, 0), (cx * pixel_size, canvas_size)], fill="#CCCCCC", width=1)
    draw.line([(0, 4 * pixel_size), (canvas_size, 4 * pixel_size)], fill="#CCCCCC", width=1)
    return img


def generate_fingerprint(scores: dict) -> str:
    ordered = [str(scores[e]) for e in EMOTIONS]
    return hashlib.sha256("-".join(ordered).encode("utf-8")).hexdigest()[:8].upper()


def generate_anime_art(scores: dict, user_text: str) -> Image.Image:
    """Pollinations.ai 免费 API。支持缓存。"""
    fingerprint = generate_fingerprint(scores)
    cache_key = f"{fingerprint}_{user_text[:30]}"
    if "anime_cache" not in st.session_state:
        st.session_state.anime_cache = {}
    if cache_key in st.session_state.anime_cache:
        return st.session_state.anime_cache[cache_key]

    try:
        seed = sum(ord(c) for c in fingerprint) + sum(ord(c) for c in user_text[:20])
        rng = random.Random(seed)
        sorted_e = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_e, sec_e = sorted_e[0][0], sorted_e[1][0]

        prompt_parts = [
            "anime illustration, 2D, masterpiece, high quality, detailed",
            rng.choice(ART_STYLES),
            f"primary mood: {EMOTION_ANIME_STYLES[top_e]['en']}",
            f"secondary mood: {EMOTION_ANIME_STYLES[sec_e]['en']}",
            rng.choice(SCENE_TYPES),
            rng.choice(CAMERA_ANGLES),
            rng.choice(COLOR_PALETTES),
            "emotional expression, beautiful composition",
            f"atmosphere: {user_text.strip()[:80]}",
        ]
        prompt = ", ".join(prompt_parts)
        url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
               f"?width=512&height=512&nologo=true&seed={seed}")
        response = requests.get(url, timeout=60)
        if response.status_code == 200 and len(response.content) > 0:
            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            st.session_state.anime_cache[cache_key] = img
            return img
        raise Exception(f"HTTP {response.status_code}")
    except Exception as e:
        st.warning(f"🎨 插画生成失败（{str(e)[:40]}）。")
        return _anime_placeholder(top_e if "top_e" in dir() else "快乐")


def _anime_placeholder(emotion_name: str) -> Image.Image:
    w, h, color = 512, 512, EMOTION_COLORS.get(emotion_name, "#CCCCCC")
    img = Image.new("RGB", (w, h), color)
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 120))
    img = img.convert("RGBA")
    img.paste(overlay, (0, 0), overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((w // 2 - 100, h // 2 - 40), f"✨ {emotion_name} ✨",
              fill="#333333", font=_load_font(36))
    draw.text((w // 2 - 140, h // 2 + 20), "二次元插画生成中...",
              fill="#666666", font=_load_font(18))
    draw.text((w // 2 - 100, h // 2 + 55), "请稍后重试",
              fill="#888888", font=_load_font(18))
    return img


# ============================================================
# 纯 CSS 动态背景注入 — 情绪渐变 + 飘落粒子动画
# 无需 API Key，完全免费，永不失效
# ============================================================

def inject_wallpaper_css(top_emotion: str):
    """向页面注入动态背景 CSS：情绪渐变 + 飘落粒子动画。"""
    gradient = WALLPAPER_GRADIENTS.get(top_emotion, WALLPAPER_GRADIENTS["快乐"])
    colors = PARTICLE_COLORS.get(top_emotion, PARTICLE_COLORS["快乐"])

    # 生成每个粒子的随机参数（位置、延迟、尺寸、颜色）
    import random
    rng = random.Random(hash(top_emotion) + 42)
    particles_css = []
    for i in range(15):
        left = rng.randint(0, 100)
        delay = rng.uniform(0, 8)
        duration = rng.uniform(6, 14)
        size = rng.randint(4, 12)
        color = colors[i % len(colors)]
        opacity = rng.uniform(0.15, 0.4)
        particles_css.append(
            f".particle-{i} {{"
            f"  left:{left}%;"
            f"  width:{size}px;height:{size}px;"
            f"  background:{color};"
            f"  opacity:{opacity:.2f};"
            f"  animation:floatParticle {duration:.1f}s ease-in infinite;"
            f"  animation-delay:{delay:.1f}s;"
            f"}}"
        )

    particles_html = "\n".join(
        [f'<div class="particle particle-{i}"></div>' for i in range(15)]
    )
    particles_css_block = "\n".join(particles_css)

    css_html = f"""
    <style>
    /* 页面基础渐变 */
    .stApp {{
        background: {gradient} !important;
        background-attachment: fixed !important;
    }}
    /* 主容器半透明毛玻璃 */
    .main .block-container {{
        background: rgba(255,255,255,0.70) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        margin-top: 0.8rem;
    }}
    /* 侧边栏 */
    section[data-testid="stSidebar"] > div {{
        background: rgba(255,255,255,0.75) !important;
        backdrop-filter: blur(6px);
    }}
    /* 飘落粒子容器 */
    .particle-container {{
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }}
    /* 粒子 */
    .particle {{
        position: absolute;
        top: -20px;
        border-radius: 50%;
        pointer-events: none;
    }}
    /* 飘落动画 */
    @keyframes floatParticle {{
        0% {{
            transform: translateY(-30px) translateX(0) rotate(0deg);
            opacity: 0;
        }}
        10% {{
            opacity: 1;
        }}
        90% {{
            opacity: 1;
        }}
        100% {{
            transform: translateY(105vh) translateX(40px) rotate(360deg);
            opacity: 0;
        }}
    }}
    /* 粒子个体样式 */
    {particles_css_block}
    </style>
    <div class="particle-container">
        {particles_html}
    </div>
    """
    st.markdown(css_html, unsafe_allow_html=True)


# ============================================================
# 工具函数 — 二维码、Base64、分享卡片
# ============================================================

def generate_qrcode(target_url: str) -> Image.Image:
    import qrcode
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=6, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    return qr.make_image(fill_color="#333333", back_color="#FFFFFF").convert("RGB")


def img_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def base64_to_img(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64)))


def create_share_card(
    pixel_art: Image.Image, anime_art: Image.Image | None,
    poem: str, fingerprint: str, emotion_name: str, qr_img: Image.Image,
) -> Image.Image:
    """分享卡片（700×420），含情绪命名。"""
    card_w, card_h = 700, 420
    card = Image.new("RGB", (card_w, card_h), "#FFFFFF")
    card_draw = ImageDraw.Draw(card)

    # 装饰性几何边框
    card_draw.rectangle([8, 8, card_w - 9, card_h - 9], outline="#E0E0E0", width=2)
    card_draw.rectangle([14, 14, card_w - 15, card_h - 15], outline="#F0F0F0", width=1)

    # 顶部渐变装饰条
    top_rect_h = 4
    for i in range(top_rect_h):
        alpha = 1.0 - i / top_rect_h
        r_val = int(0x6C * alpha) + int(0xFF * (1 - alpha))
        g_val = int(0x5C * alpha) + int(0xFF * (1 - alpha))
        b_val = int(0xE7 * alpha) + int(0xFF * (1 - alpha))
        card_draw.line([(14, 14 + i), (card_w - 15, 14 + i)],
                       fill=(r_val, g_val, b_val), width=1)

    card.paste(pixel_art.resize((90, 90), Image.NEAREST), (30, 130))
    if anime_art is not None:
        card.paste(anime_art.resize((90, 90), Image.LANCZOS), (130, 130))

    font_poem = _load_poem_font()
    font_mono = _load_mono_font()
    font_label = _load_label_font()

    # 诗意命名
    card_draw.text((250, 35), f"🔮 {emotion_name}", fill="#6C5CE7", font=font_label)
    card_draw.text((250, 60), "🎨 情绪像素 · 心情艺术品", fill="#999999", font=font_label)

    y_offset = 100
    for line in poem.strip().split("\n"):
        card_draw.text((250, y_offset), line, fill="#444444", font=font_poem)
        y_offset += 32

    card_draw.text((250, 200), f"情绪指纹：{fingerprint}", fill="#888888", font=font_mono)
    card.paste(qr_img.resize((75, 75), Image.NEAREST), (30, 300))
    card_draw.text((115, 328), "扫码体验 →", fill="#AAAAAA", font=font_label)

    card_draw.line([(20, 398), (680, 398)], fill="#EEEEEE", width=1)
    card_draw.text((200, 400), "用像素记录每一刻的心情 ✨", fill="#CCCCCC", font=font_label)
    return card


# ============================================================
# 初始化会话状态
# ============================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "anime_cache" not in st.session_state:
    st.session_state.anime_cache = {}
# reveal_stage: None=未开始, 1=字幕, 2=命盘, 3=像素画, 4=插画, 5=诗+散文, 6=完成
if "reveal_stage" not in st.session_state:
    st.session_state.reveal_stage = None
if "pending_result" not in st.session_state:
    st.session_state.pending_result = None  # 存放正在生成中的完整记录

# ============================================================
# 页面初始化：注入全局动画 + 显示 Hero 区域
# ============================================================
inject_global_animations()

# Hero 光晕图样（CSS 仅用，在输入框上方展示产品气质）
st.markdown(
    """
    <div style="text-align:center;padding:10px 0 0 0;margin-bottom:-16px;">
        <div class="hero-float" style="display:inline-block;font-size:52px;
                    filter:drop-shadow(0 4px 20px rgba(108,92,231,0.25));">
            🎨
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 顶部 Tab
# ============================================================
tab_create, tab_gallery = st.tabs(["✨ 创作", "🖼️ 画廊"])

# ============================================================
# Tab 1: 创作模式
# ============================================================
with tab_create:
    st.markdown(
        """
        <div class="animate-fade-in-up" style="text-align:center;">
            <h1 style="font-size:2.3rem;font-weight:800;margin-bottom:6px;
                       background:linear-gradient(135deg,#6C5CE7,#A29BFE,#F19066);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                🎨 情绪像素 · 心情艺术品
            </h1>
            <p style="color:#888;font-size:15px;margin-bottom:20px;">
                写下你的心情，AI 将为你创作一幅独一无二的情绪像素画 ✨
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 功能亮点条
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown(
            '<div class="animate-fade-in-up animate-delay-1" style="text-align:center;'
            'background:rgba(108,92,231,0.05);border-radius:12px;padding:14px 8px;">'
            '<div style="font-size:28px;">🧠</div>'
            '<div style="font-size:13px;font-weight:600;color:#6C5CE7;">AI 情绪解析</div>'
            '<div style="font-size:11px;color:#999;">8维深度检测</div></div>',
            unsafe_allow_html=True,
        )
    with col_f2:
        st.markdown(
            '<div class="animate-fade-in-up animate-delay-2" style="text-align:center;'
            'background:rgba(241,144,102,0.05);border-radius:12px;padding:14px 8px;">'
            '<div style="font-size:28px;">🎌</div>'
            '<div style="font-size:13px;font-weight:600;color:#F19066;">二次元插画</div>'
            '<div style="font-size:11px;color:#999;">AI 为你绘画</div></div>',
            unsafe_allow_html=True,
        )
    with col_f3:
        st.markdown(
            '<div class="animate-fade-in-up animate-delay-3" style="text-align:center;'
            'background:rgba(78,205,196,0.05);border-radius:12px;padding:14px 8px;">'
            '<div style="font-size:28px;">🔐</div>'
            '<div style="font-size:13px;font-weight:600;color:#4ECDC4;">情绪指纹</div>'
            '<div style="font-size:11px;color:#999;">独一无二签名</div></div>',
            unsafe_allow_html=True,
        )

    with st.form(key="mood_form", clear_on_submit=False):
        c1, c2, _ = st.columns([6, 1])
        with c1:
            user_input = st.text_area(
                "💬 今天心情如何？",
                placeholder="比如：今天阳光很好，走在路上收到了意外的礼物，心里暖暖的...",
                height=100, max_chars=500, key="mood_input",
                label_visibility="collapsed",
            )
        with c2:
            # 占位，让按钮和输入框顶端对齐
            st.write("")
        col_btn, col_tip, _, _ = st.columns([1, 2, 1, 1])
        with col_btn:
            submitted = st.form_submit_button("✨ 生成", type="primary", use_container_width=True)
        with col_tip:
            st.caption("💡 Ctrl+Enter 快速生成")

    # ---- 处理生成逻辑 ----
    if submitted:
        if not user_input or not user_input.strip():
            st.warning("💡 请先输入你的心情文字再生成哦～")
        else:
            text = user_input.strip()

            # 进度条
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Step 1: 情绪分析
            status_text.text("🎭 正在解析你的情绪密码…")
            progress_bar.progress(10)
            scores = analyze_emotion(text)
            top_emotion = max(scores, key=scores.get)
            progress_bar.progress(20)

            # Step 2: 并行 — 诗意命名 + 情绪诗 + 散文 + 像素画 + 插画
            status_text.text("🔮 AI正在理解你的内心世界… 🎌 正在创作艺术品…")
            with ThreadPoolExecutor(max_workers=3) as executor:
                f_name = executor.submit(emotion_namer, text, scores)
                f_poem = executor.submit(generate_poem, text, scores)
                f_prose = executor.submit(emotion_prose, text, scores, "等待中...")
                f_pixel = executor.submit(draw_pixel_art, scores)
                f_anime = executor.submit(generate_anime_art, scores, text)

                emotion_name = f_name.result()
                progress_bar.progress(40)
                poem = f_poem.result()
                pixel_art = f_pixel.result()
                progress_bar.progress(60)
                anime_art = f_anime.result()
                progress_bar.progress(80)

            fingerprint = generate_fingerprint(scores)
            # 给 prose 补上 emotion_name
            prose = emotion_prose(text, scores, emotion_name)

            progress_bar.progress(100)
            status_text.text("✅ 艺术品诞生！")
            progress_bar.empty()

            # 保存记录
            record = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "input": text,
                "scores": scores,
                "emotion_name": emotion_name,
                "poem": poem,
                "prose": prose,
                "fingerprint": fingerprint,
                "pixel_art_b64": img_to_base64(pixel_art),
                "anime_art_b64": img_to_base64(anime_art),
            }
            st.session_state.history.append(record)

            # 启动揭示动画（从 stage 1 开始）
            st.session_state.pending_result = record
            st.session_state.reveal_stage = 1
            st.rerun()

    # ---- 揭示动画 ----
    if st.session_state.reveal_stage is not None and st.session_state.pending_result:
        latest = st.session_state.pending_result
        stage = st.session_state.reveal_stage
        top_e = max(latest["scores"], key=latest["scores"].get)

        # 注入动态壁纸
        inject_wallpaper_css(top_e)

        reveal_container = st.empty()

        if stage == 1:
            # 🎭 神秘字幕
            with reveal_container.container():
                st.markdown("---")
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:40px 20px;animation:fadeIn 0.8s ease;">
                        <div style="font-size:28px;margin-bottom:12px;">🎭</div>
                        <div style="font-size:22px;color:#6C5CE7;font-weight:bold;margin-bottom:8px;">
                            情绪密码已解析
                        </div>
                        <div style="font-size:15px;color:#888;margin-bottom:20px;">
                            你的8个情绪维度已被映射为色彩与光影
                        </div>
                        <div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;max-width:400px;margin:0 auto;">
                            {''.join(f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{EMOTION_COLORS[e]};opacity:0.7;animation:pulse 1.5s infinite;animation-delay:{i*0.15}s;"></span>' for i, e in enumerate(EMOTIONS))}
                        </div>
                    </div>
                    <style>
                    @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}
                    @keyframes pulse {{ 0%,100% {{ opacity:0.5; transform:scale(1); }} 50% {{ opacity:1; transform:scale(1.6); }} }}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
            time.sleep(1.2)
            st.session_state.reveal_stage = 2
            st.rerun()

        elif stage == 2:
            # 🔮 情绪命盘 + 诗意命名
            with reveal_container.container():
                st.markdown("---")
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:24px 20px;animation:fadeIn 0.8s ease;">
                        <div style="font-size:14px;color:#888;margin-bottom:4px;">🔮 你的情绪类型</div>
                        <div style="font-size:30px;color:#6C5CE7;font-weight:bold;margin-bottom:16px;
                                    background:linear-gradient(135deg,#6C5CE7,#A29BFE);
                                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                            {latest['emotion_name']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # 情绪条
                for emotion in EMOTIONS:
                    score = latest["scores"][emotion]
                    bar_color = EMOTION_COLORS[emotion]
                    is_top = emotion == top_e
                    st.markdown(
                        f"""<div style="display:flex;align-items:center;margin-bottom:4px;animation:slideRight 0.5s ease;">
                            <span style="width:40px;font-size:13px;{'font-weight:bold;color:#6C5CE7;' if is_top else ''}">{emotion}{'⭐' if is_top else ''}</span>
                            <div style="flex:1;background:#eee;height:14px;border-radius:7px;margin:0 8px;">
                                <div style="width:{score*10}%;background:{bar_color};height:100%;border-radius:7px;
                                            transition:width 1s ease;"></div>
                            </div>
                            <span style="width:24px;font-size:13px;text-align:right;">{score}</span></div>""",
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    '<style>@keyframes slideRight{from{opacity:0;transform:translateX(-16px);}'
                    'to{opacity:1;transform:translateX(0);}}</style>',
                    unsafe_allow_html=True,
                )
            time.sleep(1.5)
            st.session_state.reveal_stage = 3
            st.rerun()

        elif stage == 3:
            # 🎨 像素画（模糊→清晰）+ 指纹
            with reveal_container.container():
                st.markdown("---")
                pixel_img = base64_to_img(latest["pixel_art_b64"])
                pixel_b64 = img_to_base64(pixel_img.resize((220, 220), Image.NEAREST))
                st.markdown(
                    f"""<div style="text-align:center;padding:20px;animation:fadeIn 0.8s ease;">
                        <div style="font-size:14px;color:#888;margin-bottom:12px;">🎨 你的情绪像素画</div>
                        <img src="data:image/png;base64,{pixel_b64}"
                             style="border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.08);"
                             alt="像素画">
                        <div style="margin-top:14px;font-size:15px;color:#666;">
                            🔐 情绪指纹：<code style="font-size:17px;letter-spacing:2px;">{latest['fingerprint']}</code>
                        </div>
                        <div style="font-size:12px;color:#aaa;margin-top:4px;">
                            全世界独一无二的情绪签名
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            time.sleep(1.5)
            st.session_state.reveal_stage = 4
            st.rerun()

        elif stage == 4:
            # 🎌 二次元插画
            with reveal_container.container():
                st.markdown("---")
                anime_b64 = latest.get("anime_art_b64", "")
                if anime_b64:
                    anime_img = base64_to_img(anime_b64)
                    anime_b64_small = img_to_base64(anime_img.resize((260, 260), Image.LANCZOS))
                    st.markdown(
                        f"""<div style="text-align:center;padding:20px;animation:fadeIn 0.8s ease;">
                            <div style="font-size:14px;color:#888;margin-bottom:12px;">🎌 AI为你绘制的二次元场景</div>
                            <img src="data:image/png;base64,{anime_b64_small}"
                                 style="border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,0.12);"
                                 alt="二次元插画">
                        </div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("🎌 二次元插画暂未就绪")
            time.sleep(1.8)
            st.session_state.reveal_stage = 5
            st.rerun()

        elif stage == 5:
            # 📝 情绪诗 + 💭 散文
            with reveal_container.container():
                st.markdown("---")
                st.markdown(
                    f"""<div style="padding:16px;animation:fadeIn 0.8s ease;">
                        <div style="font-size:14px;color:#888;margin-bottom:8px;">📝 AI情绪诗</div>
                        <div style="background:#F8F9FA;border-left:4px solid #6C5CE7;padding:12px 16px;
                                    border-radius:4px;font-size:18px;line-height:2;margin-bottom:20px;">
                            {latest['poem'].replace(chr(10), '<br>')}
                        </div>
                        <div style="font-size:14px;color:#888;margin-bottom:8px;">💭 情绪散文</div>
                        <div style="background:linear-gradient(135deg,#FFF8E1,#FFF3E0);padding:16px 20px;
                                    border-radius:8px;font-size:15px;line-height:1.9;color:#555;
                                    border:1px solid #FFE0B2;">
                            {latest['prose']}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            time.sleep(1.5)
            st.session_state.reveal_stage = 6
            st.rerun()

        elif stage == 6:
            # ✅ 完成：全部展示 + 下载按钮
            with reveal_container.container():
                st.markdown("---")
                st.subheader("✨ 你的情绪艺术品")

                col_a, col_b, col_c = st.columns([1, 1, 2])
                with col_a:
                    pixel_img = base64_to_img(latest["pixel_art_b64"])
                    st.image(pixel_img.resize((200, 200), Image.NEAREST),
                             caption="🎨 情绪像素画", use_container_width=True)
                with col_b:
                    anime_b64 = latest.get("anime_art_b64", "")
                    if anime_b64:
                        st.image(base64_to_img(anime_b64).resize((200, 200), Image.LANCZOS),
                                 caption="🎌 二次元插画", use_container_width=True)

                with col_c:
                    st.markdown(f"### 🔮 {latest['emotion_name']}")
                    for emotion in EMOTIONS:
                        score = latest["scores"][emotion]
                        st.markdown(
                            f"""<div style="display:flex;align-items:center;margin-bottom:3px;">
                                <span style="width:36px;font-size:12px;">{emotion}</span>
                                <div style="flex:1;background:#eee;height:10px;border-radius:5px;margin:0 6px;">
                                    <div style="width:{score*10}%;background:{EMOTION_COLORS[emotion]};
                                                height:100%;border-radius:5px;"></div>
                                </div>
                                <span style="width:18px;font-size:12px;">{score}</span></div>""",
                            unsafe_allow_html=True,
                        )
                    st.code(latest["fingerprint"], language=None)

                st.markdown(f"**📝 情绪诗**")
                st.markdown(
                    f"""<div style="background:#F8F9FA;border-left:4px solid #6C5CE7;padding:12px 16px;
                                border-radius:4px;font-size:18px;line-height:2;">
                        {latest['poem'].replace(chr(10), '<br>')}</div>""",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**💭 情绪散文**\n\n{latest['prose']}")

                st.divider()
                share_col, _, _, _ = st.columns([1, 1, 1, 1])
                with share_col:
                    anime_share = base64_to_img(anime_b64) if anime_b64 else None
                    qr_url = st.secrets.get("SITE_URL", SITE_URL)
                    share_card = create_share_card(
                        pixel_img, anime_share, latest["poem"], latest["fingerprint"],
                        latest["emotion_name"], generate_qrcode(qr_url),
                    )
                    buf = io.BytesIO()
                    share_card.save(buf, format="PNG", quality=95)
                    st.download_button(
                        label="📤 下载分享卡片",
                        data=buf.getvalue(),
                        file_name=f"情绪像素_{latest['fingerprint']}.png",
                        mime="image/png",
                        use_container_width=True,
                    )

                # 再来一次按钮
                if st.button("🔄 再来一次", use_container_width=True):
                    st.session_state.reveal_stage = None
                    st.session_state.pending_result = None
                    st.rerun()

    # ---- 首次使用引导 ----
    if st.session_state.reveal_stage is None and not submitted:
        if not st.session_state.history:
            st.divider()
            st.markdown(
                """
                <div style="background:linear-gradient(135deg,#F8F9FA,#E8ECEF);border-radius:12px;
                            padding:24px;margin:16px 0;">
                <h4 style="margin-top:0;">✨ 三步创作你的情绪艺术品</h4>
                <ol>
                    <li><b>写下心情</b> — 描述现在的心情或今天发生的事</li>
                    <li><b>点击生成</b> — AI 逐步揭晓你的情绪画像</li>
                    <li><b>分享留念</b> — 下载专属分享卡片</li>
                </ol>
                <p style="color:#888;margin-bottom:0;">💡 试试输入：「<i>今天和好朋友一起看了日落，心里暖暖的</i>」</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ============================================================
# Tab 2: 画廊模式
# ============================================================
with tab_gallery:
    st.title("🖼️ 情绪画廊")

    if st.session_state.history:
        col_export, col_import, col_clear, _ = st.columns([1, 1, 1, 2])
        with col_export:
            export_json = json.dumps(st.session_state.history, ensure_ascii=False, indent=2)
            st.download_button("📥 导出历史",
                               data=export_json,
                               file_name=f"情绪像素_历史_{datetime.now().strftime('%Y%m%d')}.json",
                               mime="application/json", use_container_width=True)
        with col_import:
            uploaded = st.file_uploader("📤 导入", type=["json"], key="import_hist", label_visibility="collapsed")
            if uploaded:
                try:
                    imported = json.loads(uploaded.read().decode("utf-8"))
                    if isinstance(imported, list):
                        st.session_state.history.extend(imported)
                        st.rerun()
                except Exception:
                    st.error("导入失败")
        with col_clear:
            if st.button("🗑️ 清空历史", type="secondary", use_container_width=True):
                st.session_state.history = []
                st.session_state.anime_cache = {}
                st.rerun()

        st.divider()

        reversed_history = list(reversed(st.session_state.history))
        for idx, record in enumerate(reversed_history):
            actual_idx = len(st.session_state.history) - 1 - idx
            pixel_img = base64_to_img(record["pixel_art_b64"])
            emo_name = record.get("emotion_name", "")

            with st.expander(
                f"{'🔮 ' + emo_name + ' — ' if emo_name else '🎨 '}{record['time']}",
                expanded=(idx == 0),
            ):
                gl, gm, gr = st.columns([1, 1, 2])
                with gl:
                    st.image(pixel_img.resize((140, 140), Image.NEAREST),
                             caption="像素画", use_container_width=False)
                with gm:
                    anime_b64_h = record.get("anime_art_b64", "")
                    if anime_b64_h:
                        st.image(base64_to_img(anime_b64_h).resize((140, 140), Image.LANCZOS),
                                 caption="二次元", use_container_width=False)
                with gr:
                    st.markdown(f"**🔮 {emo_name}**" if emo_name else "")
                    st.markdown(f"**诗句：**\n>{record['poem']}")
                    st.caption(f"指纹：{record['fingerprint']}")
                    st.caption(" · ".join([f"{e}{record['scores'][e]}" for e in EMOTIONS]))

                if record.get("prose"):
                    st.markdown(f"*{record['prose'][:120]}...*")

                anime_hist = base64_to_img(anime_b64_h) if anime_b64_h else None
                qr_url = st.secrets.get("SITE_URL", SITE_URL)
                share_card = create_share_card(
                    pixel_img, anime_hist, record["poem"], record["fingerprint"],
                    record.get("emotion_name", ""), generate_qrcode(qr_url),
                )
                buf = io.BytesIO()
                share_card.save(buf, format="PNG", quality=95)
                st.download_button(
                    label="📤 下载卡片", data=buf.getvalue(),
                    file_name=f"情绪像素_{record['fingerprint']}.png",
                    mime="image/png", key=f"dl_{actual_idx}",
                    use_container_width=True,
                )
    else:
        st.info("📭 暂无记录\n\n去「✨ 创作」页面生成第一件艺术品吧！")

# ============================================================
# 页脚
# ============================================================
st.divider()
fc1, fc2, fc3 = st.columns([1, 1, 1])
with fc1:
    st.caption(f"📊 记录：{len(st.session_state.history)} 条")
with fc2:
    if st.session_state.history:
        st.caption(f"🕐 最近：{st.session_state.history[-1]['time']}")
with fc3:
    st.caption("[🐙 GitHub](https://github.com/2090meng/project)")
st.caption("🎨 情绪像素 · 心情艺术品 | Powered by DeepSeek + Streamlit")
