"""生成骑砍英雄传Logo"""
from PIL import Image, ImageDraw, ImageFont
import os

# 颜色定义
BG_COLOR = (20, 15, 30)  # 深紫色背景
GOLD = (212, 164, 64)      # 金色
SILVER = (192, 192, 192)  # 银色
DARK_GOLD = (164, 124, 44)  # 深金色
WHITE = (255, 255, 255)
BORDER = (100, 80, 60)

def create_logo():
    # 创建大图
    width, height = 800, 300
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体
    font_paths = [
        "static/fonts/DouyinSansBold.otf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    
    font_large = None
    font_small = None
    for path in font_paths:
        if os.path.exists(path):
            try:
                font_large = ImageFont.truetype(path, 72)
                font_small = ImageFont.truetype(path, 28)
                break
            except:
                continue
    
    if not font_large:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 绘制装饰边框
    draw.rectangle([20, 20, width-20, height-20], outline=GOLD, width=3)
    draw.rectangle([30, 30, width-30, height-30], outline=DARK_GOLD, width=2)
    
    # 绘制顶部装饰线
    draw.line([(100, 60), (700, 60)], fill=GOLD, width=2)
    
    # 绘制剑图标（简化版）
    center_x = width // 2
    sword_y = 130
    
    # 剑柄
    draw.rectangle([center_x-5, sword_y+50, center_x+5, sword_y+80], fill=SILVER)
    draw.rectangle([center_x-15, sword_y+45, center_x+15, sword_y+55], fill=DARK_GOLD)  # 护手
    
    # 剑身
    draw.polygon([
        (center_x, sword_y-60),
        (center_x+20, sword_y+50),
        (center_x-20, sword_y+50)
    ], fill=SILVER)
    
    # 绘制盾牌
    shield_x = 120
    shield_y = 150
    
    # 盾牌形状
    draw.polygon([
        (shield_x, shield_y-50),
        (shield_x+60, shield_y-50),
        (shield_x+60, shield_y+20),
        (shield_x+30, shield_y+60),
        (shield_x, shield_y+20)
    ], outline=GOLD, fill=BORDER)
    
    # 盾牌十字
    draw.line([(shield_x+30, shield_y-40), (shield_x+30, shield_y+50)], fill=GOLD, width=3)
    draw.line([(shield_x, shield_y), (shield_x+60, shield_y)], fill=GOLD, width=3)
    
    # 右侧盾牌
    shield_x2 = width - 180
    draw.polygon([
        (shield_x2, shield_y-50),
        (shield_x2+60, shield_y-50),
        (shield_x2+60, shield_y+20),
        (shield_x2+30, shield_y+60),
        (shield_x2, shield_y+20)
    ], outline=GOLD, fill=BORDER)
    draw.line([(shield_x2+30, shield_y-40), (shield_x2+30, shield_y+50)], fill=GOLD, width=3)
    draw.line([(shield_x2, shield_y), (shield_x2+60, shield_y)], fill=GOLD, width=3)
    
    # 主标题
    title = "骑砍英雄传"
    bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = bbox[2] - bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 175), title, fill=GOLD, font=font_large)
    
    # 副标题
    subtitle = "Mount & Blade Chronicle"
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_small)
    sub_width = bbox2[2] - bbox2[0]
    sub_x = (width - sub_width) // 2
    draw.text((sub_x, 255), subtitle, fill=SILVER, font=font_small)
    
    # 底部装饰线
    draw.line([(100, 285), (700, 285)], fill=GOLD, width=2)
    
    # 保存
    output_path = "logo.png"
    img.save(output_path, "PNG")
    print(f"Logo已保存至: {output_path}")
    
    # 同时生成小图标版本
    small_size = (200, 75)
    small_img = img.resize(small_size, Image.Resampling.LANCZOS)
    small_img.save("logo_small.png", "PNG")
    print(f"小图标已保存至: logo_small.png")

if __name__ == "__main__":
    create_logo()
