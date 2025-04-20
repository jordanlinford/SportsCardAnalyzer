"""Script to create and save the optimized logo."""
from PIL import Image, ImageDraw, ImageFont
import os

def create_logo():
    """Create and save the logo with proper dimensions and format."""
    # Create the static/images directory if it doesn't exist
    os.makedirs('static/images', exist_ok=True)
    
    # Create a new image with transparency
    width = 400
    height = 100
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw the graph icon
    icon_size = 60
    icon_x = 20
    icon_y = (height - icon_size) // 2
    
    # Draw the square
    draw.rectangle(
        [icon_x, icon_y, icon_x + icon_size, icon_y + icon_size],
        outline=(0, 0, 0, 255),
        width=3
    )
    
    # Draw the graph bars
    bar_width = 10
    bar_spacing = 8
    bar_x = icon_x + 10
    
    # Bar heights
    heights = [30, 20, 40]
    for i, h in enumerate(heights):
        x = bar_x + i * (bar_width + bar_spacing)
        y = icon_y + icon_size - h - 10
        draw.rectangle(
            [x, y, x + bar_width, icon_y + icon_size - 10],
            fill=(0, 0, 0, 255)
        )
    
    # Draw the arrow
    arrow_points = [
        (bar_x, icon_y + 20),  # Start
        (bar_x + 40, icon_y + 10),  # End
        (bar_x + 35, icon_y + 5),  # Arrow head top
        (bar_x + 35, icon_y + 15)  # Arrow head bottom
    ]
    draw.line(arrow_points[:2], fill=(0, 0, 0, 255), width=3)
    draw.polygon(arrow_points[1:], fill=(0, 0, 0, 255))
    
    # Add text
    text_x = icon_x + icon_size + 20
    text_y = (height - 40) // 2
    
    # Draw "SPORTS CARD"
    draw.text(
        (text_x, text_y),
        "SPORTS CARD",
        fill=(0, 0, 0, 255),
        font=None,  # Using default font
        size=24
    )
    
    # Draw "ANALYZER"
    draw.text(
        (text_x, text_y + 25),
        "ANALYZER",
        fill=(0, 0, 0, 255),
        font=None,  # Using default font
        size=24
    )
    
    # Save the image
    img.save('static/images/logo.png', 'PNG', optimize=True, quality=95)

if __name__ == "__main__":
    create_logo() 