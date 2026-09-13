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
    preset: str = "glow",
    glow: int = 35,
    dark_circles: int = 65,
    smooth: int = 25,
    warmth: int = 10,
    crop_aspect: Optional[str] = None
) -> Dict[str, Any]:
    """
    Non-destructive AI Photo Retouching & Framing Engine:
    - Face Glow & Lighting Lift
    - Dark Circles & Under-Eye Shadow Concealer
    - Skin Texture Smoothing
    - Skin Tone Warmth Adjustment
    - Preset Cropping (WhatsApp DP 1:1, IG Portrait 4:5, etc.)
    """
    try:
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
        else:
            img = image_input.convert("RGB")

        # Apply Preset defaults if requested
        if preset == "glow":
            glow, dark_circles, smooth, warmth = 45, 60, 20, 15
        elif preset == "undereye":
            glow, dark_circles, smooth, warmth = 25, 90, 15, 5
        elif preset == "glam":
            glow, dark_circles, smooth, warmth = 60, 80, 45, 20
        elif preset == "bw":
            img = ImageOps.grayscale(img).convert("RGB")
            glow, dark_circles, smooth, warmth = 0, 0, 0, 0
        elif preset == "sharp":
            img = img.filter(ImageFilter.SHARPEN)

        # 1. Natural Face Glow & Lighting Lift (Brightness + Contrast Boost)
        if glow > 0:
            bright_factor = 1.0 + (glow / 100.0) * 0.22
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(bright_factor)
            
            contrast_factor = 1.0 + (glow / 100.0) * 0.08
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)

        # 2. Under-Eye Shadow / Dark Circles Conceal (Mid-tone gamma / shadow lift)
        if dark_circles > 0:
            # Lifting darker midtones without blowing highlights
            lift = (dark_circles / 100.0) * 18.0
            def lift_pixel(p):
                # Gentle S-curve lift for shadows
                if p < 140:
                    return min(255, int(p + lift * (1.0 - p / 140.0)))
                return p
            
            # Apply to green and red channels for flattering skin lift
            r, g, b = img.split()
            r = r.point(lift_pixel)
            g = g.point(lift_pixel)
            img = Image.merge("RGB", (r, g, b))

        # 3. Skin Texture Smoothing (Subtle blur blend)
        if smooth > 0:
            blur_radius = max(0.5, (smooth / 100.0) * 1.8)
            blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            # Blend original with smoothed to maintain sharp facial features
            blend_alpha = min(0.40, (smooth / 100.0) * 0.40)
            img = Image.blend(img, blurred, blend_alpha)

        # 4. Skin Tone Warmth Adjustment
        if warmth != 0:
            r, g, b = img.split()
            warmth_val = int(warmth * 0.6)
            r = r.point(lambda p: min(255, max(0, p + warmth_val)))
            b = b.point(lambda p: min(255, max(0, p - warmth_val)))
            img = Image.merge("RGB", (r, g, b))

        # 5. Aspect Ratio Cropping
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
        return {
            "success": True,
            "filename": out_filename,
            "url": web_url,
            "preset": preset,
            "details": f"Retouched with glow={glow}%, dark_circles_lift={dark_circles}%, smooth={smooth}%, warmth={warmth}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
