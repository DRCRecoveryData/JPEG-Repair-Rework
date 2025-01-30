import os

def is_gray_pixel(r, g, b, tolerance=10):
    """Check if a pixel is gray based on RGB values."""
    return abs(r - g) <= tolerance and abs(g - b) <= tolerance

def get_crop_height_from_pillow(image_path):
    """Use Pillow to detect the crop height based on gray scanlines."""
    from PIL import Image
    with Image.open(image_path) as img:
        pixels = img.load()
        width, height = img.size

        # Find the bottom gray scanlines
        crop_height = height
        for y in range(height - 1, -1, -1):  # Start from the bottom
            is_gray_line = True
            for x in range(width):
                r, g, b = pixels[x, y]
                if not is_gray_pixel(r, g, b):
                    is_gray_line = False
                    break
            if is_gray_line:
                crop_height = y
            else:
                break
    return crop_height

def crop_jpeg_height(image_path, crop_height):
    """Crop the height of the JPEG image using raw byte manipulation."""
    with open(image_path, "rb") as f:
        data = f.read()

    # Find the Start of Frame (SOF) marker and extract the height
    sof_marker = b'\xFF\xC0'  # SOF (Start of Frame) marker
    sof_pos = data.find(sof_marker)
    if sof_pos == -1:
        raise ValueError("Start of Frame marker not found in JPEG.")

    # The height is stored in the next 2 bytes (after the SOF marker)
    original_height = (data[sof_pos + 5] << 8) + data[sof_pos + 6]

    # Update the height in the SOF marker
    new_data = data[:sof_pos + 5] + (crop_height >> 8).to_bytes(1, 'big') + (crop_height & 0xFF).to_bytes(1, 'big') + data[sof_pos + 7:]

    # Now, we need to crop the image data itself. JPEG data is compressed, so we cannot just remove raw pixels,
    # but we can slice the file's data to represent the new cropped image.

    # The file data up until the start of the image (data[sof_pos + 7:]) represents the compressed image.
    # We'll crop out the bottom scanlines from the raw data after the SOF marker.
    end_marker = b'\xFF\xD9'  # End of Image (EOI) marker
    eoi_pos = data.rfind(end_marker)
    if eoi_pos == -1:
        raise ValueError("End of Image marker not found in JPEG.")

    # Crop the data by slicing out the bottom section
    cropped_data = new_data[:eoi_pos]  # Remove the unwanted part (cropped height)
    
    # Re-append the End of Image (EOI) marker
    cropped_data += end_marker
    
    return cropped_data

def save_cropped_jpeg(cropped_data, output_path):
    """Save the cropped JPEG image to a new file."""
    with open(output_path, "wb") as f:
        f.write(cropped_data)
    print(f"JPEG saved as {output_path} with gray scanlines removed.")

def auto_correct_alignment(input_path):
    """
    Automatically crops the bottom gray scanlines and saves the result without padding.
    The cropped image is saved in the same location as the original file.
    """
    # Step 1: Use Pillow to find the crop height based on gray scanlines
    crop_height = get_crop_height_from_pillow(input_path)

    # Step 2: Crop the JPEG file's height using hex manipulation
    cropped_data = crop_jpeg_height(input_path, crop_height)

    # Step 3: Save the cropped image to a new file
    output_path = os.path.splitext(input_path)[0] + "_cropped" + os.path.splitext(input_path)[1]
    save_cropped_jpeg(cropped_data, output_path)

    print(f"Cropped image saved to {output_path}. Original file unchanged.")

# Example usage
input_path = "_NHL0591.JPG"  # Change this to your file
auto_correct_alignment(input_path)
