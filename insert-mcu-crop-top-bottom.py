from PIL import Image
import numpy as np
import os
import subprocess

def is_gray_pixel(r, g, b, tolerance=10):
    """Check if a pixel is gray based on RGB values."""
    return abs(r - g) <= tolerance and abs(g - b) <= tolerance

def get_crop_height_from_pillow(image_path):
    """Use Pillow to detect the crop height based on gray scanlines."""
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
                crop_height = y  # Update crop height when gray line is found
            else:
                break
    return crop_height

def find_previous_mcu_block(image_path, gray_threshold=128, mcu_size=16):
    """
    Detects the last scanline that contains both MCU data and gray pixels.
    Returns the last MCU block before the gray region.
    """
    img = Image.open(image_path).convert('L')  # Convert to grayscale
    img_array = np.array(img)

    height, width = img_array.shape
    width_mcu = width // mcu_size

    # Start from the bottom and move up to find the last meaningful scanline
    last_valid_scanline = None
    for y in range(height - 1, -1, -1):  # Scan from bottom to top
        row = img_array[y, :]

        # Check if the scanline contains at least one non-gray MCU (has real image data)
        if np.any(row < gray_threshold):  # Has at least one non-gray pixel
            last_valid_scanline = y
            break  # Stop at the first valid scanline

    if last_valid_scanline is None:
        return None, None  # No valid scanline found

    # Now, scan the last valid scanline for gray pixels
    scanline = img_array[last_valid_scanline, :]
    has_gray_pixels = np.any(scanline >= gray_threshold)

    if not has_gray_pixels:
        return None, None  # No gray pixels in the last meaningful scanline

    # Find the first MCU block that contains gray pixels
    gray_start = None
    for x in range(0, width, mcu_size):
        block = scanline[x:x + mcu_size]
        if np.any(block >= gray_threshold):  # If any pixel in the block is gray
            gray_start = x // mcu_size
            break  # Stop at the first detected gray block

    if gray_start is not None and gray_start > 0:
        previous_mcu_block_number = gray_start - 1  # MCU block before the gray region
        mcu_to_insert = width_mcu - previous_mcu_block_number
        return previous_mcu_block_number, mcu_to_insert

    return None, None

# Prompt user for JPEG file path
image_path = input("Please enter the path to the JPEG file: ")

if not os.path.exists(image_path):
    print("Error: File not found.")
else:
    try:
        previous_mcu_block, mcu_to_insert = find_previous_mcu_block(image_path)

        if previous_mcu_block is not None:
            mcu_value = mcu_to_insert  # Keep exact value (NO -1)
            print(f"MCU number used to insert empty MCU: {mcu_value}")

            # Save output in 'Repaired' folder
            repaired_folder = os.path.join(os.path.dirname(image_path), "Repaired")
            os.makedirs(repaired_folder, exist_ok=True)

            output_path = os.path.join(repaired_folder, os.path.basename(image_path))

            # Run jpegrepair.exe without modifying MCU number
            command = ["jpegrepair.exe", image_path, output_path, "insert", str(mcu_value)]
            subprocess.run(command, check=True)

            print(f"Repaired file saved: {output_path}")

            # After repairing, open the image to calculate cropping
            img = Image.open(output_path)
            width, height = img.size

            # Get the crop height based on gray pixels at the bottom
            crop_height = get_crop_height_from_pillow(output_path)
            
            # Subtract 1 MCU (16px) from the calculated crop height
            crop_height -= 16

            # Ensure we don't crop beyond the top of the image
            if crop_height < 0:
                crop_height = 0

            # Run jpegtran to crop the image by removing 1 MCU from the bottom
            output_path_final = os.path.join(repaired_folder, os.path.basename(image_path))
            crop_command = [
                "jpegtran.exe", "-crop", f"{width}x{crop_height}+0+0", output_path, output_path_final
            ]
            subprocess.run(crop_command, check=True)

            print(f"Final cropped file saved: {output_path_final}")

        else:
            print("No valid MCU scanline found with gray pixels.")
    
    except Exception as e:
        print(f"Error: {e}")
