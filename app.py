"""
============================================================
 情绪像素 · 心情艺术品
 Emotion Pixel - Mood Art Generator
============================================================

一个将心情文字转化为像素画、AI诗句和情绪指纹的Streamlit应用。
使用 DeepSeek API 进行情绪分析和诗句生成。
"""

# ============================================================
# 导入模块
# ============================================================
import streamlit as st
import hashlib
import json
import re
import io
import base64
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

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
# 标题与介绍
# ============================================================
st.title("🎨 情绪像素 · 心情艺术品")
st.markdown("写下你的心情，AI 将为你创作一幅独一无二的情绪像素画 ✨")

# ============================================================
# OpenAI 客户端初始化（用于 DeepSeek API）
# ============================================================
try:
    from openai import OpenAI
    # DeepSeek API 兼容 OpenAI 接口，只需替换 base_url
    client = OpenAI(
        api_key=st.secrets.get("DEEPSEEK_API_KEY", ""),
        base_url="https://api.deepseek.com/v1",
    )
    api_available = bool(st.secrets.get("DEEPSEEK_API_KEY", ""))
except Exception:
    client = None
    api_available = False

# ============================================================
# 常量定义
# ============================================================

# 8个情绪维度（Plutchik情绪轮）
EMOTIONS = ["快乐", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "期待", "信任"]

# 每个情绪对应的显示颜色（十六进制）
EMOTION_COLORS = {
    "快乐": "#FFD93D",  # 明黄色 — 阳光般的喜悦
    "悲伤": "#4A69BD",  # 深蓝色 — 沉静的忧伤
    "愤怒": "#E55039",  # 红色 — 燃烧的怒火
    "恐惧": "#6A0572",  # 紫色 — 神秘的不安
    "惊讶": "#F3A683",  # 暖橙色 — 灵动的惊奇
    "厌恶": "#78A178",  # 灰绿色 — 不适的排斥
    "期待": "#F19066",  # 珊瑚色 — 温暖的盼望
    "信任": "#A8E06C",  # 嫩绿色 — 安心的信赖
}

# 站点URL（用于二维码，优先从secrets读取）
SITE_URL = "https://emotion-pixel.streamlit.app"

# ============================================================
# 工具函数
# ============================================================

def get_mock_scores(user_text: str) -> dict:
    """
    生成模拟情绪分数（API降级方案）。
    基于输入文字长度和哈希来产生一些变化，避免每次返回相同结果。

    参数:
        user_text: 用户输入的心情文字

    返回:
        dict: 包含8个情绪维度的分数字典，如 {"快乐": 7, "悲伤": 2, ...}
    """
    import random
    # 用文字哈希做随机种子，相同文字产生相同结果
    seed = sum(ord(c) for c in user_text)
    rng = random.Random(seed)
    return {emotion: rng.randint(0, 10) for emotion in EMOTIONS}


def analyze_emotion(user_text: str, use_mock: bool = False) -> dict:
    """
    调用 DeepSeek API 分析用户文字中的8个情绪维度分数。

    参数:
        user_text: 用户输入的心情文字
        use_mock: 是否强制使用模拟数据

    返回:
        dict: {"快乐": int, "悲伤": int, ..., "信任": int}，每个值范围0-10
    """
    if use_mock or not api_available:
        if not api_available:
            st.warning("⚠️ 未配置 DeepSeek API Key，使用模拟数据。请在 Streamlit Cloud Secrets 中设置 DEEPSEEK_API_KEY。")
        return get_mock_scores(user_text)

    try:
        # 构建带中文情绪标签的JSON Schema提示
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
            timeout=15,  # 15秒超时
        )

        raw = response.choices[0].message.content.strip()
        scores = json.loads(raw)

        # 验证返回值包含所有情绪维度
        validated = {}
        for emotion in EMOTIONS:
            val = scores.get(emotion, 5)
            # 确保是整数且在0-10范围内
            validated[emotion] = max(0, min(10, int(val)))

        return validated

    except Exception as e:
        st.warning(f"⚠️ 情绪分析API调用失败（{str(e)[:50]}），已降级使用模拟数据。")
        return get_mock_scores(user_text)


def generate_poem(user_text: str, scores: dict, use_mock: bool = False) -> str:
    """
    调用 DeepSeek API 根据用户心情和情绪分数生成两行诗。
    要求：每行不超过10个字，末尾押韵。

    参数:
        user_text: 用户输入的心情文字
        scores: 情绪分析结果字典
        use_mock: 是否强制使用模拟数据

    返回:
        str: 两行诗句（用换行符分隔）
    """
    if use_mock or not api_available:
        return get_mock_poem(scores)

    try:
        # 找出最强烈的两个情绪
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_emotions = f"{sorted_emotions[0][0]}({sorted_emotions[0][1]}分)和{sorted_emotions[1][0]}({sorted_emotions[1][1]}分)"

        system_prompt = (
            "你是一个才华横溢的诗人。请根据用户的情绪分析结果创作两行诗。\n"
            "要求：\n"
            "1. 每行不超过10个汉字\n"
            "2. 两行的最后一个字必须押韵\n"
            "3. 诗句要优美、有诗意，体现用户的主导情绪\n"
            "4. 不要使用标点符号\n\n"
            '请严格按以下JSON格式返回：\n'
            '{"line1": "第一行诗", "line2": "第二行诗"}'
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"用户心情：{user_text}\n"
                        f"主导情绪：{top_emotions}\n"
                        f"完整情绪分数：{scores}"
                    ),
                },
            ],
            temperature=0.9,
            max_tokens=150,
            response_format={"type": "json_object"},
            timeout=15,
        )

        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        line1 = data.get("line1", "").strip()
        line2 = data.get("line2", "").strip()

        return f"{line1}\n{line2}"

    except Exception as e:
        st.warning(f"⚠️ 诗句生成API调用失败（{str(e)[:50]}），已降级使用默认诗句。")
        return get_mock_poem(scores)


def get_mock_poem(scores: dict) -> str:
    """
    根据情绪分数生成默认诗句（降级方案）。

    参数:
        scores: 情绪分数字典

    返回:
        str: 两行默认诗句
    """
    # 预设诗句库，按主导情绪分类
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
    使用 Pillow 绘制8×8情绪像素画。
    8个情绪各占2×2像素区域，根据分数决定每个2×2区域内填充多少像素。

    布局（8×8网格，每个格子25×25像素）：
      第一行：快乐(0,0) 悲伤(0,2) 愤怒(0,4) 恐惧(0,6)
      第二行：惊讶(2,0) 厌恶(2,2) 期待(2,4) 信任(2,6)

    参数:
        scores: 情绪分数字典，如 {"快乐": 7, ...}

    返回:
        PIL.Image: 200×200像素的PNG图像
    """
    pixel_size = 25      # 每个像素格子的尺寸（像素）
    grid_size = 8        # 8×8网格
    canvas_size = pixel_size * grid_size  # 200×200

    # 创建白色画布
    img = Image.new("RGB", (canvas_size, canvas_size), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # 第一行情绪（对应网格第0-1行），第二行情绪（对应网格第2-3行）
    row1_emotions = ["快乐", "悲伤", "愤怒", "恐惧"]
    row2_emotions = ["惊讶", "厌恶", "期待", "信任"]

    # 绘制每一行情绪
    for row_idx, emotion_row in enumerate([row1_emotions, row2_emotions]):
        for col_idx, emotion in enumerate(emotion_row):
            score = scores.get(emotion, 0)

            # 分数 → 填充像素数：0-3→1个, 4-7→2-3个, 8-10→4个
            if score <= 3:
                fill_count = 1
            elif score <= 7:
                fill_count = 2 + (score - 4)  # 4→2, 5→3, 6→4, 7→5 -> 用3
                fill_count = 2 if score <= 5 else 3
            else:
                fill_count = 4

            color = EMOTION_COLORS[emotion]

            # 该情绪的2×2区域起始坐标（在网格中的位置）
            base_grid_x = col_idx * 2       # 0, 2, 4, 6
            base_grid_y = row_idx * 4       # 0（第一行）或4（第二行）

            # 2×2区域的4个像素位置（左上、右上、左下、右下）
            positions = [
                (base_grid_x, base_grid_y),          # 左上
                (base_grid_x + 1, base_grid_y),      # 右上
                (base_grid_x, base_grid_y + 1),      # 左下
                (base_grid_x + 1, base_grid_y + 1),  # 右下
            ]

            # 按填充数量绘制像素
            for i in range(fill_count):
                gx, gy = positions[i]
                x1 = gx * pixel_size
                y1 = gy * pixel_size
                x2 = x1 + pixel_size
                y2 = y1 + pixel_size
                draw.rectangle([x1, y1, x2, y2], fill=color)

            # 为未填充的像素画浅灰色边框（仅限空像素）
            for i in range(fill_count, 4):
                gx, gy = positions[i]
                x1 = gx * pixel_size
                y1 = gy * pixel_size
                x2 = x1 + pixel_size - 1
                y2 = y1 + pixel_size - 1
                draw.rectangle([x1, y1, x2, y2], outline="#E0E0E0", width=1)

    return img


def generate_fingerprint(scores: dict) -> str:
    """
    生成情绪指纹：将8个分数按固定顺序拼接 → SHA256 → 取前8位。

    参数:
        scores: 情绪分数字典

    返回:
        str: 8位十六进制字符串
    """
    # 按固定顺序拼接分数
    ordered_scores = [str(scores[emotion]) for emotion in EMOTIONS]
    raw_string = "-".join(ordered_scores)

    # SHA256哈希
    sha = hashlib.sha256(raw_string.encode("utf-8"))
    return sha.hexdigest()[:8].upper()


def generate_qrcode(target_url: str) -> Image.Image:
    """
    生成指向指定URL的二维码图片。

    参数:
        target_url: 要编码的URL

    返回:
        PIL.Image: 二维码图像（方形）
    """
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # 中等纠错
        box_size=6,
        border=2,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    return qr.make_image(fill_color="#333333", back_color="#FFFFFF").convert("RGB")


def img_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    """
    将PIL图像转换为Base64编码字符串（用于会话状态存储）。

    参数:
        img: PIL图像对象
        fmt: 图像格式

    返回:
        str: Base64编码的字符串
    """
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def base64_to_img(b64_string: str) -> Image.Image:
    """
    将Base64字符串还原为PIL图像。

    参数:
        b64_string: Base64编码的图像字符串

    返回:
        PIL.Image: 图像对象
    """
    data = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(data))


def create_share_card(
    pixel_art: Image.Image,
    poem: str,
    fingerprint: str,
    qr_img: Image.Image,
) -> Image.Image:
    """
    创建分享卡片图片：包含像素画、诗句、指纹和二维码。

    卡片布局（600×400，白底）：
      ┌────────────────────────────────┐
      │  像素画(160×160)  │ 情绪诗     │
      │  (左侧居中)       │ (右上)     │
      │                   │ 情绪指纹   │
      │                   │ (右中)     │
      │  二维码(80×80)   │            │
      │  (左下角)        │            │
      └────────────────────────────────┘

    参数:
        pixel_art: 像素画PIL图像
        poem: 诗句文字
        fingerprint: 情绪指纹字符串
        qr_img: 二维码图像

    返回:
        PIL.Image: 600×400的分享卡片
    """
    card_w, card_h = 600, 400
    card = Image.new("RGB", (card_w, card_h), "#FFFFFF")
    card_draw = ImageDraw.Draw(card)

    # ---- 左侧：像素画（放大显示）----
    pixel_resized = pixel_art.resize((160, 160), Image.NEAREST)
    card.paste(pixel_resized, (40, 120))

    # ---- 右侧：诗句 + 情绪指纹 ----
    try:
        # 尝试使用中文字体
        font_poem = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 20)
        font_fingerprint = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
        font_label = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 14)
    except Exception:
        # 降级到默认字体（Pillow自带，不支持中文）
        font_poem = ImageFont.load_default()
        font_fingerprint = ImageFont.load_default()
        font_label = ImageFont.load_default()

    # 标题
    card_draw.text((240, 40), "🎨 情绪像素 · 心情艺术品", fill="#333333", font=font_label)

    # 诗句
    lines = poem.strip().split("\n")
    y_offset = 100
    for line in lines:
        card_draw.text((240, y_offset), line, fill="#444444", font=font_poem)
        y_offset += 32

    # 情绪指纹
    card_draw.text((240, 200), f"情绪指纹：{fingerprint}", fill="#888888", font=font_fingerprint)

    # ---- 底部：二维码 ----
    qr_resized = qr_img.resize((100, 100), Image.NEAREST)
    card.paste(qr_resized, (40, 290))
    card_draw.text((150, 330), "扫码体验 →", fill="#AAAAAA", font=font_label)

    # ---- 分隔线 ----
    card_draw.line([(20, 380), (580, 380)], fill="#EEEEEE", width=1)
    card_draw.text((200, 382), "用像素记录每一刻的心情 ✨", fill="#CCCCCC", font=font_label)

    return card


# ============================================================
# 初始化会话状态
# ============================================================
if "history" not in st.session_state:
    st.session_state.history = []


# ============================================================
# 主界面：心情输入
# ============================================================
user_input = st.text_area(
    "💬 今天心情如何？",
    placeholder="比如：今天阳光很好，走在路上收到了意外的礼物，心里暖暖的...",
    height=100,
    max_chars=500,
    key="mood_input",
)

# 生成按钮
col_btn, _, _, _ = st.columns([1, 1, 1, 1])
with col_btn:
    generate_clicked = st.button(
        "✨ 生成",
        type="primary",
        use_container_width=True,
    )

# ============================================================
# 处理生成逻辑
# ============================================================
if generate_clicked:
    # 验证用户输入
    if not user_input or not user_input.strip():
        st.warning("💡 请先输入你的心情文字再生成哦～")
    else:
        # 使用 spinner 展示处理进度
        with st.spinner("🎨 AI正在分析你的情绪..."):
            # 步骤1：情绪分析
            scores = analyze_emotion(user_input.strip())

        with st.spinner("🖼️ 正在绘制像素画..."):
            # 步骤2：绘制像素画
            pixel_art = draw_pixel_art(scores)

        with st.spinner("📝 AI正在创作诗句..."):
            # 步骤3：生成诗句
            poem = generate_poem(user_input.strip(), scores)

        with st.spinner("🔐 生成情绪指纹..."):
            # 步骤4：生成情绪指纹
            fingerprint = generate_fingerprint(scores)

        # ---- 保存到历史记录 ----
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input": user_input.strip(),
            "scores": scores,
            "poem": poem,
            "fingerprint": fingerprint,
            "pixel_art_b64": img_to_base64(pixel_art),
        }
        st.session_state.history.append(record)

        # 触发rerun，确保结果区域获取到最新数据
        st.rerun()


# ============================================================
# 显示最新生成结果
# ============================================================
if st.session_state.history:
    latest = st.session_state.history[-1]
    st.divider()

    st.subheader("✨ 你的情绪艺术品")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        # 显示像素画
        pixel_art_img = base64_to_img(latest["pixel_art_b64"])
        st.image(
            pixel_art_img.resize((200, 200), Image.NEAREST),
            caption="情绪像素画",
            use_container_width=True,
        )

    with col_right:
        # ---- 情绪分数条 ----
        st.markdown("**📊 情绪分析**")
        for emotion in EMOTIONS:
            score = latest["scores"][emotion]
            color_hex = EMOTION_COLORS[emotion]
            # 用彩色进度条展示分数
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;margin-bottom:4px;">
                    <span style="width:40px;font-size:13px;">{emotion}</span>
                    <div style="flex:1;background:#eee;height:14px;border-radius:7px;margin:0 8px;">
                        <div style="width:{score*10}%;background:{color_hex};height:100%;border-radius:7px;"></div>
                    </div>
                    <span style="width:24px;font-size:13px;text-align:right;">{score}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---- 情绪诗 ----
        st.markdown("**📝 AI情绪诗**")
        st.markdown(
            f"""
            <div style="background:#F8F9FA;border-left:4px solid #6C5CE7;padding:12px 16px;
                        border-radius:4px;font-size:18px;line-height:2;margin:8px 0;">
                {latest['poem'].replace(chr(10), '<br>')}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---- 情绪指纹 ----
        st.markdown("**🔐 情绪指纹**")
        st.code(latest["fingerprint"], language=None)

    # ---- 分享卡片 ----
    st.divider()
    share_col, _, _, _ = st.columns([1, 1, 1, 1])
    with share_col:
        # 生成二维码和分享卡片
        qr_url = st.secrets.get("SITE_URL", SITE_URL)
        qr_img = generate_qrcode(qr_url)
        share_card = create_share_card(
            pixel_art_img,
            latest["poem"],
            latest["fingerprint"],
            qr_img,
        )

        # 转换为字节流供下载
        card_buffer = io.BytesIO()
        share_card.save(card_buffer, format="PNG", quality=95)
        card_bytes = card_buffer.getvalue()

        st.download_button(
            label="📤 下载分享卡片",
            data=card_bytes,
            file_name=f"情绪像素_{latest['fingerprint']}.png",
            mime="image/png",
            use_container_width=True,
        )


# ============================================================
# 侧边栏：情绪画廊
# ============================================================
with st.sidebar:
    st.header("🖼️ 情绪画廊")

    # 清空历史按钮
    if st.session_state.history:
        if st.button("🗑️ 清空所有历史", use_container_width=True, type="secondary"):
            st.session_state.history = []
            st.rerun()

    st.divider()

    # 如果没有历史记录
    if not st.session_state.history:
        st.info("📭 暂无记录\n\n输入心情并点击「生成」来创建第一件艺术品吧！")
    else:
        # 按时间倒序显示（最新的在前）
        reversed_history = list(reversed(st.session_state.history))

        for idx, record in enumerate(reversed_history):
            actual_idx = len(st.session_state.history) - 1 - idx
            pixel_img = base64_to_img(record["pixel_art_b64"])

            # 每条记录用 expander 展示
            with st.expander(
                f"🎨 {record['time']} — {record['poem'].split(chr(10))[0]}...",
                expanded=(idx == 0),  # 最新一条默认展开
            ):
                # 缩略图
                st.image(
                    pixel_img.resize((120, 120), Image.NEAREST),
                    use_container_width=False,
                )

                # 完整诗句
                st.markdown(f"**诗句：**\n>{record['poem']}")

                # 指纹
                st.caption(f"指纹：{record['fingerprint']}")

                # 情绪分数摘要
                scores_text = " · ".join(
                    [f"{e}{record['scores'][e]}" for e in EMOTIONS]
                )
                st.caption(scores_text)

                # 每条记录也有下载按钮
                qr_url = st.secrets.get("SITE_URL", SITE_URL)
                qr_img = generate_qrcode(qr_url)
                share_card = create_share_card(
                    pixel_img,
                    record["poem"],
                    record["fingerprint"],
                    qr_img,
                )
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
# 页脚
# ============================================================
st.divider()
st.caption("🎨 情绪像素 · 心情艺术品 | 用像素记录每一刻的心情 | Powered by DeepSeek + Streamlit")
