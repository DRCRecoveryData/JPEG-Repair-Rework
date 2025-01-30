python
import os

def find_ffda_offset(data):
    # Find the last occurrence of FFDA marker in the JPEG data
    ffda_marker = b'\xFF\xDA'
    ffda_offset = data.rfind(ffda_marker)
    if ffda_offset == -1:
        raise ValueError("FFDA marker not found in the reference JPEG file.")
    return ffda_offset

def remove_exif(data):
    # JPEG markers that indicate the start of a segment
    marker_start = b'\xFF'
    app1_marker = b'\xFF\xE1'  # APP1 marker (where EXIF data is stored)
    
    i = 0
    while i < len(data) - 1:
        # Check if the current byte is a marker start
        if data[i] == 0xFF:
            marker = data[i:i+2]  # Get the marker (2 bytes)
            
            # If the marker is APP1 (EXIF data), remove the entire segment
            if marker == app1_marker:
                segment_length = int.from_bytes(data[i+2:i+4], byteorder='big') + 2
                data = data[:i] + data[i+segment_length:]  # Remove the segment
                continue  # Continue parsing from the current position
            
            # Skip other markers (except SOI and EOI)
            if marker not in (b'\xFF\xD8', b'\xFF\xD9'):  # Skip SOI and EOI
                segment_length = int.from_bytes(data[i+2:i+4], byteorder='big') + 2
                i += segment_length  # Move to the next segment
                continue
        
        i += 1  # Move to the next byte
    
    return data

def repair_jpeg(encrypted_path, reference_path, output_path):
    # Load the encrypted JPEG file
    with open(encrypted_path, 'rb') as encrypted_file:
        encrypted_data = encrypted_file.read()
    
    # Cut the encrypted data from offset 0 to 153605 (inclusive)
    cut_encrypted_data = encrypted_data[:153606]  # 153606 because slicing is exclusive
    
    # Load the reference JPEG file
    with open(reference_path, 'rb') as reference_file:
        reference_data = reference_file.read()
    
    # Find the last FFDA marker in the reference data
    ffda_offset = find_ffda_offset(reference_data)
    
    # Cut the reference data from offset 0 to FFDA + 12 bytes
    cut_reference_data = reference_data[:ffda_offset + 12]
    
    # Merge the cut reference data with the remaining encrypted data after 153605
    repaired_data = cut_reference_data + encrypted_data[153606:]
    
    # Remove EXIF metadata from the repaired data
    repaired_data = remove_exif(repaired_data)
    
    # Remove 334 bytes from the end of the repaired data
    repaired_data = repaired_data[:-334]
    
    # Save the repaired data to the output path
    with open(output_path, 'wb') as output_file:
        output_file.write(repaired_data)

def main():
    # Prompt for the reference and encrypted file paths
    reference_path = input("Enter the path to the reference JPEG file: ")
    encrypted_path = input("Enter the path to the encrypted JPEG file: ")
    
    # Get the base name of the encrypted file (without any extensions)
    base_name = os.path.splitext(encrypted_path)[0]  # Remove the last extension
    base_name = os.path.splitext(base_name)[0]  # Remove the second extension (if any)
    file_name = os.path.basename(base_name)  # Get the file name without path
    
    # Create a "Repaired" folder in the same directory as the encrypted file
    output_folder = os.path.join(os.path.dirname(encrypted_path), "Repaired")
    os.makedirs(output_folder, exist_ok=True)  # Create the folder if it doesn't exist
    
    # Generate the output path in the "Repaired" folder with only .JPG extension
    output_path = os.path.join(output_folder, file_name + '.JPG')
    
    # Repair the JPEG file, remove EXIF metadata, and trim 334 bytes from the end
    repair_jpeg(encrypted_path, reference_path, output_path)
    
    print(f"Repaired file saved as {output_path}")

if __name__ == "__main__":
    main()
