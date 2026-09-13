import os
import uuid
import urllib.parse
from typing import Dict, Any, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

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

def replace_image_background(
    image_input: Any,
    new_bg_color: str = "#ffffff",
    target_bg_color: Optional[str] = None,
    tolerance: int = 35,
    feather: int = 3,
    use_ai: bool = False
) -> Dict[str, Any]:
    """
    Image Background Changer (Passport / Portrait / Cutout):
    Replaces the image background color (e.g. blue passport background to white)
    while keeping the subject/person intact.
    Supports AI deep matting via rembg if requested/available, or smart color-distance matting with feathering.
    """
    try:
        import io
        import base64
        import numpy as np

        if isinstance(image_input, str):
            if image_input.startswith("data:image"):
                base64_data = image_input.split(",", 1)[1]
                img = Image.open(io.BytesIO(base64.b64decode(base64_data))).convert("RGBA")
            elif os.path.exists(image_input):
                img = Image.open(image_input).convert("RGBA")
            else:
                return {"success": False, "error": f"Image file not found: {image_input}"}
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("RGBA")
        else:
            return {"success": False, "error": "Invalid image input"}

        w, h = img.size
        processed_img = None

        # 1. Try deep AI cutout via rembg if requested or if general background is complex
        if use_ai:
            try:
                import rembg
                # rembg produces transparent RGBA
                no_bg = rembg.remove(img)
                if new_bg_color.lower() == "transparent":
                    processed_img = no_bg
                else:
                    hex_c = new_bg_color.lstrip("#")
                    bg_rgb = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
                    solid_bg = Image.new("RGBA", (w, h), (*bg_rgb, 255))
                    solid_bg.paste(no_bg, (0, 0), no_bg)
                    processed_img = solid_bg.convert("RGB")
            except Exception as e:
                # Fall back to smart color matting
                pass

        # 2. Smart perimeter color matting if processed_img not yet produced
        if processed_img is None:
            rgb_img = img.convert("RGB")
            arr = np.array(rgb_img).astype(np.float32)

            if not target_bg_color:
                # Sample corners & top edges (typical passport / studio backdrop area)
                corners = [
                    arr[min(5, h-1), min(5, w-1)],
                    arr[min(5, h-1), max(0, w-6)],
                    arr[max(0, h-6), min(5, w-1)],
                    arr[max(0, h-6), max(0, w-6)],
                    arr[min(5, h-1), w // 2]
                ]
                target_rgb = np.median(corners, axis=0)
            else:
                hex_c = target_bg_color.lstrip("#")
                if len(hex_c) == 3:
                    hex_c = "".join(c * 2 for c in hex_c)
                target_rgb = np.array([int(hex_c[i:i+2], 16) for i in (0, 2, 4)], dtype=np.float32)

            dist = np.sqrt(np.sum((arr - target_rgb) ** 2, axis=2))
            max_dist = np.sqrt(255**2 * 3)
            norm_dist = (dist / max_dist) * 100.0

            f_range = max(1.0, float(tolerance * 0.45))
            t_low = max(0.0, float(tolerance) - f_range)
            t_high = float(tolerance) + f_range

            alpha = np.clip((norm_dist - t_low) / (t_high - t_low), 0.0, 1.0)
            mask_img = Image.fromarray((alpha * 255).astype(np.uint8), mode="L")
            if feather > 0:
                mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=feather))

            if new_bg_color.lower() == "transparent":
                processed_img = rgb_img.convert("RGBA")
                processed_img.putalpha(mask_img)
            else:
                hex_c = new_bg_color.lstrip("#")
                if len(hex_c) == 3:
                    hex_c = "".join(c * 2 for c in hex_c)
                bg_rgb = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
                bg_layer = Image.new("RGB", (w, h), bg_rgb)
                processed_img = Image.composite(rgb_img, bg_layer, mask_img)

        # Save and return base64 / URLs
        is_transparent = (new_bg_color.lower() == "transparent")
        ext = "png" if is_transparent else "jpg"
        fmt = "PNG" if is_transparent else "JPEG"
        out_filename = f"passport_bg_{uuid.uuid4().hex[:10]}.{ext}"
        out_path = os.path.join(UPLOAD_DIR, out_filename)

        buf = io.BytesIO()
        if is_transparent:
            processed_img.save(out_path, format="PNG")
            processed_img.save(buf, format="PNG")
        else:
            processed_img.convert("RGB").save(out_path, format="JPEG", quality=95)
            processed_img.convert("RGB").save(buf, format="JPEG", quality=95)

        b64_str = f"data:image/{ext};base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        return {
            "success": True,
            "filename": out_filename,
            "url": f"/data/uploads/{out_filename}",
            "download_url": f"/api/image/download/{out_filename}",
            "data_url": b64_str,
            "new_color": new_bg_color,
            "width": w,
            "height": h
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
