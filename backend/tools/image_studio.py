import os
import uuid
import urllib.parse
from typing import Dict, Any, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_ai_image(prompt: str, width: int = 1024, height: int = 1024) -> Dict[str, Any]:
    """
    Generate an AI image using Pollinations AI (100% Free, high quality, no API key needed).
    """
    encoded_prompt = urllib.parse.quote(prompt.strip())
    seed = uuid.uuid4().int % 1000000
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true"
    
    return {
        "success": True,
        "prompt": prompt,
        "image_url": image_url,
        "markdown": f"![{prompt}]({image_url})",
        "description": f"Generated high-resolution image for prompt: '{prompt}'"
    }

def retouch_image_file(
    image_input: Any, # file path or PIL Image
    preset: str = "custom",
    glow: int = 35,
    dark_circles: int = 65,
    smooth: int = 25,
    warmth: int = 10,
    crop_aspect: Optional[str] = None,
    bw: bool = False
) -> Dict[str, Any]:
    """
    Non-destructive AI Photo Retouching & Framing Engine:
    - Multi-select capability: Combine face glow, dark circles lift, skin smoothing, warmth, and 1:1 DP cropping.
    """
    try:
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
        else:
            img = image_input.convert("RGB")

        # Apply Preset defaults only if a specific preset string is passed and custom values are not active
        if preset == "glow":
            glow = max(glow, 45)
            dark_circles = max(dark_circles, 60)
            smooth = max(smooth, 20)
            warmth = max(warmth, 15)
        elif preset == "undereye":
            dark_circles = max(dark_circles, 85)
            glow = max(glow, 25)
        elif preset == "glam":
            glow = max(glow, 60)
            dark_circles = max(dark_circles, 80)
            smooth = max(smooth, 40)
            warmth = max(warmth, 15)
        elif preset == "bw" or bw:
            bw = True

        # 1. Black & White conversion if selected
        if bw:
            img = ImageOps.grayscale(img).convert("RGB")

        # 2. Natural Face Glow & Lighting Lift (Brightness + Contrast Boost)
        if glow > 0:
            bright_factor = 1.0 + (glow / 100.0) * 0.22
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(bright_factor)
            
            contrast_factor = 1.0 + (glow / 100.0) * 0.08
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)

        # 3. Under-Eye Shadow / Dark Circles Conceal (Mid-tone gamma / shadow lift)
        if dark_circles > 0:
            lift = (dark_circles / 100.0) * 18.0
            def lift_pixel(p):
                if p < 140:
                    return min(255, int(p + lift * (1.0 - p / 140.0)))
                return p
            
            r, g, b = img.split()
            r = r.point(lift_pixel)
            g = g.point(lift_pixel)
            img = Image.merge("RGB", (r, g, b))

        # 4. Skin Texture Smoothing (Subtle blur blend)
        if smooth > 0:
            blur_radius = max(0.5, (smooth / 100.0) * 1.8)
            blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            blend_alpha = min(0.40, (smooth / 100.0) * 0.40)
            img = Image.blend(img, blurred, blend_alpha)

        # 5. Skin Tone Warmth Adjustment (skipped if B&W)
        if warmth != 0 and not bw:
            r, g, b = img.split()
            warmth_val = int(warmth * 0.6)
            r = r.point(lambda p: min(255, max(0, p + warmth_val)))
            b = b.point(lambda p: min(255, max(0, p - warmth_val)))
            img = Image.merge("RGB", (r, g, b))

        # 6. Aspect Ratio Cropping (e.g. 1:1 WhatsApp DP)
        if crop_aspect:
            w, h = img.size
            if crop_aspect == "1:1":
                target_size = min(w, h)
                left = (w - target_size) // 2
                top = (h - target_size) // 2
                img = img.crop((left, top, left + target_size, top + target_size))
            elif crop_aspect == "4:5":
                target_w = min(w, int(h * 4 / 5))
                target_h = int(target_w * 5 / 4)
                left = (w - target_w) // 2
                top = (h - target_h) // 2
                img = img.crop((left, top, left + target_w, top + target_h))
            elif crop_aspect == "16:9":
                target_h = min(h, int(w * 9 / 16))
                target_w = int(target_h * 16 / 9)
                left = (w - target_w) // 2
                top = (h - target_h) // 2
                img = img.crop((left, top, left + target_w, top + target_h))

        # Save to output file
        out_filename = f"retouched_{uuid.uuid4().hex[:10]}.jpg"
        out_path = os.path.join(UPLOAD_DIR, out_filename)
        img.save(out_path, format="JPEG", quality=95)
        
        web_url = f"/data/uploads/{out_filename}"
        download_url = f"/api/image/download/{out_filename}"

        # Generate descriptive features list
        features = []
        if glow > 0: features.append(f"Face Glow (+{glow}%)")
        if dark_circles > 0: features.append(f"Dark Circles Removed (+{dark_circles}%)")
        if smooth > 0: features.append(f"Smooth Skin (+{smooth}%)")
        if warmth != 0 and not bw: features.append(f"Natural Warmth ({warmth:+d})")
        if crop_aspect == "1:1": features.append("1:1 WhatsApp DP Crop")
        if bw: features.append("B&W Studio Style")
        details_str = ", ".join(features) if features else "Natural lighting enhanced"

        return {
            "success": True,
            "filename": out_filename,
            "url": web_url,
            "download_url": download_url,
            "preset": preset,
            "details": details_str
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
