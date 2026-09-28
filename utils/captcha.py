import base64
import io
import os
import re
import logging
from datetime import datetime

import ddddocr
import numpy as np
from PIL import Image
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)

_ocr = ddddocr.DdddOcr(show_ad=False)
_ocr_beta = ddddocr.DdddOcr(show_ad=False, beta=True)

SAMPLE_DIR = "captcha_samples"

# ========== 映射表 ==========

_DIGIT_MAP = {
    "O": "0", "o": "0", "D": "0", "Q": "0", "C": "0", "U": "0",
    "I": "1", "l": "1", "i": "1", "|": "1", "!": "1", "j": "1",
    "Z": "2", "z": "2",
    "J": "3",
    "A": "4", "h": "4", "y": "4",
    "S": "5", "s": "5", "$": "5",
    "G": "6", "b": "6",
    "T": "7", "?": "7", "？": "7",
    "B": "8", "&": "8",
    "g": "9", "q": "9", "e": "9",
}

_OP_MAP = {
    # 加号
    "+": "+", "t": "+", "T": "+", "十": "+", "4": "+", "f": "+", "F": "+", "7": "+",
    "人": "+", "入": "+", "†": "+", "‡": "+",
    # 减号
    "-": "-", "_": "-", "一": "-", "—": "-", "~": "-", "=": "-", "a": "-", "二": "-",
    # 乘号
    "*": "*", "x": "*", "X": "*", "×": "*", "＊": "*", "メ": "*", "米": "*",
    # 除号
    "/": "/", "\\": "/", "l": "/", "I": "/", "|": "/", "丿": "/", "／": "/", "1": "/",
}


def _to_half(s: str) -> str:
    table = {
        "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
        "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
        "＋": "+", "－": "-", "×": "*", "÷": "/",
        "＊": "*", "／": "/", "＝": "=", "？": "?",
    }
    return "".join(table.get(c, c) for c in s)


def _to_digit(s: str) -> str:
    if not s:
        return ""
    for ch in s:
        if ch.isdigit():
            return ch
    for ch in s:
        if ch in _DIGIT_MAP:
            return _DIGIT_MAP[ch]
    return ""


def _to_operator(s: str) -> str:
    if not s:
        return ""
    if s in _OP_MAP:
        return _OP_MAP[s]
    for ch in s:
        if ch in _OP_MAP:
            return _OP_MAP[ch]
    return ""


def _extract_dod(s: str) -> str:
    """从左到右扫描提取 [数字][运算符][数字]，允许跳过噪声字符"""
    if not s:
        return ""
    s = _to_half(s)

    d1 = op = d2 = ""
    state = 0
    for ch in s:
        if state == 0:
            d = _to_digit(ch)
            if d:
                d1 = d
                state = 1
        elif state == 1:
            o = _to_operator(ch)
            if o:
                op = o
                state = 2
        elif state == 2:
            d = _to_digit(ch)
            if d:
                d2 = d
                break

    if d1 and op and d2:
        return f"{d1}{op}{d2}"
    return ""


def _calc(expr: str) -> str:
    if not expr:
        return ""
    if not re.fullmatch(r"[0-9+\-*/]+", expr):
        return ""
    expr = re.sub(r"\b0+(\d+)", r"\1", expr)
    try:
        r = eval(expr, {"__builtins__": {}}, {})
    except Exception as e:
        logger.warning("求值失败: %s (%s)", expr, e)
        return ""
    if isinstance(r, float):
        r = int(r) if r.is_integer() else round(r, 2)
    return str(r)


# ========== 图片处理 ==========

def _decode(img_element: WebElement) -> bytes:
    src = img_element.get_attribute("src") or ""
    if src.startswith("data:image"):
        try:
            return base64.b64decode(src.split(",", 1)[1])
        except Exception as e:
            logger.warning("base64 解码失败: %s", e)
    return img_element.screenshot_as_png


def _strip_border(img: Image.Image) -> Image.Image:
    w, h = img.size
    if w > 20 and h > 20:
        return img.crop((int(w * 0.02), int(h * 0.06), int(w * 0.98), int(h * 0.94)))
    return img


def _extract_blue(img: Image.Image) -> Image.Image:
    """蓝色字符 -> 黑，其他 -> 白"""
    arr = np.array(img.convert("RGB")).astype(int)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mask = (b - r > 40) & (b > 80)
    out = np.ones_like(arr) * 255
    out[mask] = [0, 0, 0]
    return Image.fromarray(out.astype("uint8"))


def _img_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# ========== 主入口 ==========

def recognize(img_element: WebElement) -> str:
    raw = _decode(img_element)
    orig = Image.open(io.BytesIO(raw))
    try:
        orig.seek(0)
    except Exception:
        pass
    orig = _strip_border(orig.convert("RGB"))

    os.makedirs(SAMPLE_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    orig.save(os.path.join(SAMPLE_DIR, f"captcha_{ts}.png"))

    blue = _extract_blue(orig)
    blue_inv = Image.fromarray(255 - np.array(blue))

    candidates = []
    for scale in (3, 4):
        w, h = orig.size
        candidates.append((f"原图x{scale}", orig.resize((w * scale, h * scale), Image.Resampling.LANCZOS)))
        w, h = blue.size
        candidates.append((f"蓝色x{scale}", blue.resize((w * scale, h * scale), Image.Resampling.LANCZOS)))
        candidates.append((f"蓝色反色x{scale}", blue_inv.resize((w * scale, h * scale), Image.Resampling.LANCZOS)))

    for prep_name, im in candidates:
        png = _img_bytes(im)
        for model_name, ocr in (("default", _ocr), ("beta", _ocr_beta)):
            try:
                raw_result = ocr.classification(png)
                s = raw_result.strip() if isinstance(raw_result, str) else ""
            except Exception:
                continue
            if not s:
                continue
            logger.info("[%s|%s] OCR: %r", prep_name, model_name, s)
            expr = _extract_dod(s)
            if not expr:
                continue
            ans = _calc(expr)
            if ans:
                logger.info("[%s|%s] ✅ %s = %s", prep_name, model_name, expr, ans)
                return ans

    logger.warning("❌ 所有预处理 + 模型组合都没识别成功")
    return ""