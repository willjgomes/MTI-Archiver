from PIL import Image, ImageDraw, ImageFont
import os
import math

def generate_cover(title, author, folder, filename):
    # Make title all caps
    title = title.upper()

    # Create output folder if it doesn't exist
    # Use a safe filename for output
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
    safe_author = "".join(c for c in author if c.isalnum() or c in (' ', '_')).rstrip()
    output_path = os.path.join(folder, f"{filename}-simple.png")

    # Create a blank image
    width, height = 600, 900
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw double border
    border_color = (0, 0, 0)
    border_width = 4
    margin = 10
    gap = 12 + margin  # Gap between the two borders

    # Outer border
    draw.rectangle(
        [margin, margin, width - 1 - margin, height - 1 - margin],
        outline=border_color,
        width=border_width
    )
    # Inner border
    draw.rectangle(
        [gap, gap, width - 1 - gap, height - 1 - gap],
        outline=border_color,
        width=border_width
    )

    # Load fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 48)
        font_author = ImageFont.truetype("arial.ttf", 28)
    except IOError:
        font_title = ImageFont.load_default()
        font_author = ImageFont.load_default()

    # Split title into lines that fit the image width
    max_title_width = width - 60  # 30px margin on each side
    words = title.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        test_bbox = draw.textbbox((0, 0), test_line, font=font_title)
        test_width = test_bbox[2] - test_bbox[0]
        if test_width <= max_title_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    # Calculate total height of title block
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        line_heights.append(bbox[3] - bbox[1])
    total_title_height = sum(line_heights) + (len(lines) - 1) * 20  # 20px between lines

    # Position title block in top third (adjust as needed)
    title_y = height // 4
    current_y = title_y

    # Draw each line of the title, centered
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        line_width = bbox[2] - bbox[0]
        line_x = (width - line_width) // 2
        draw.text((line_x, current_y), line, font=font_title, fill=(0, 0, 0))
        current_y += line_heights[i] + 20

    # Calculate position for author (centered, below title block)
    author_bbox = draw.textbbox((0, 0), author, font=font_author)
    author_w = author_bbox[2] - author_bbox[0]
    author_x = (width - author_w) // 2
    author_y = current_y + 40

    # Draw the author
    draw.text((author_x, author_y), author, font=font_author, fill=(0, 0, 0))

    # Draw a tilda-shaped horizontal bar (single crest) after the author name
    bar_width = width // 3
    bar_height = 10  # amplitude of the wave
    bar_x = (width - bar_width) // 2
    bar_y = author_y + (author_bbox[3] - author_bbox[1]) + 100

    points = []
     # One full sine wave cycle across the bar width
    for i in range(bar_width + 1):
        x = bar_x + i
        y = bar_y + int(bar_height * math.sin(2 * math.pi * i / bar_width))
        points.append((x, y))


    draw.line(points, fill=(0, 0, 0), width=3)

    # Save the image
    img.save(output_path)
    print(f"Cover image saved to {output_path}")



