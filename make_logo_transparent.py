from PIL import Image

def make_transparent(input_path, output_path, threshold=240):
    """
    Reads an image, converts white / near-white pixels to transparent alpha,
    and saves the output as a transparent PNG file.
    """
    img = Image.open(input_path).convert("RGBA")
    pixels = img.load()
    width, height = img.size

    for x in range(width):
        for y in range(height):
            r, g, b, a = pixels[x, y]
            # Replace white / near-white background pixels with full transparency
            if r >= threshold and g >= threshold and b >= threshold:
                pixels[x, y] = (255, 255, 255, 0)

    img.save(output_path, "PNG")
    print(f"Successfully saved transparent logo to {output_path}")

if __name__ == "__main__":
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, "Gemini_Generated_Image_n26va3n26va3n26v.png")
    if not os.path.exists(input_file):
        input_file = os.path.join(base_dir, "logo.png")
    output_file = os.path.join(base_dir, "logo_transparent.png")
    make_transparent(input_file, output_file)
