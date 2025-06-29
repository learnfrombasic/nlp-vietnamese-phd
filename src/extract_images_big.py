import pymupdf
import os
from pathlib import Path
from PIL import Image

def extract_images_from_pdf(pdf_path, output_dir="extracted_images_big", target_count=20, min_size=(800, 600)):
    """Extract images from PDF with size filtering and upscaling options."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Open PDF
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return []
    
    print(f"🔄 Extracting high-resolution images from: {pdf_path.name}")
    doc = pymupdf.open(pdf_path)
    
    extracted_images = []
    image_count = 0
    
    # Go through each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()
        
        print(f"📄 Page {page_num+1}: Found {len(image_list)} images")
        
        # Extract each image from the page
        for img_index, img in enumerate(image_list):
            if image_count >= target_count:
                print(f"✅ Target of {target_count} images reached!")
                break
                
            try:
                # Get image data
                xref = img[0]
                pix = pymupdf.Pixmap(doc, xref)
                
                # Only process RGB or GRAY images
                if pix.n - pix.alpha < 4:
                    original_size = (pix.width, pix.height)
                    
                    # Create filename
                    img_filename = f"page_{page_num+1:03d}_img_{img_index+1:03d}_big.png"
                    img_path = os.path.join(output_dir, img_filename)
                    
                    # Save at original resolution first
                    pix.save(img_path)
                    
                    # Check if image is too small, upscale if needed
                    if pix.width < min_size[0] or pix.height < min_size[1]:
                        print(f"🔍 Upscaling small image: {original_size} -> target {min_size}")
                        
                        # Load with PIL and upscale
                        pil_img = Image.open(img_path)
                        
                        # Calculate new size maintaining aspect ratio
                        ratio = max(min_size[0]/pil_img.width, min_size[1]/pil_img.height)
                        new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
                        
                        # Upscale using LANCZOS (high quality)
                        upscaled_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                        upscaled_img.save(img_path, 'PNG', quality=100)
                        
                        final_size = new_size
                    else:
                        final_size = original_size
                    
                    # Get image info
                    img_info = {
                        'filename': img_filename,
                        'path': img_path,
                        'page': page_num + 1,
                        'index': img_index + 1,
                        'original_size': f"{original_size[0]}x{original_size[1]}",
                        'final_size': f"{final_size[0]}x{final_size[1]}",
                        'file_size': os.path.getsize(img_path)
                    }
                    
                    extracted_images.append(img_info)
                    image_count += 1
                    
                    print(f"💾 Saved: {img_filename}")
                    print(f"   📏 Size: {img_info['original_size']} -> {img_info['final_size']}")
                    print(f"   💾 File size: {img_info['file_size']} bytes")
                
                pix = None
                
            except Exception as e:
                print(f"⚠️ Error processing image {img_index+1} on page {page_num+1}: {e}")
        
        # Break if we have enough images
        if image_count >= target_count:
            break
    
    doc.close()
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   📁 Output directory: {output_dir}")
    print(f"   🖼️ Total images extracted: {len(extracted_images)}")
    print(f"   📄 Pages processed: {page_num+1}")
    
    if len(extracted_images) < target_count:
        print(f"   ⚠️ Only found {len(extracted_images)} images (target was {target_count})")
    else:
        print(f"   ✅ Successfully extracted {target_count}+ images!")
    
    return extracted_images

def convert_pages_to_images(pdf_path, output_dir="page_images_big", target_count=20, resolution_scale=4.0):
    """Convert PDF pages to high-resolution images."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_path = Path(pdf_path)
    print(f"🔄 Converting PDF pages to HIGH-RES images: {pdf_path.name}")
    print(f"🎯 Resolution scale: {resolution_scale}x")
    
    doc = pymupdf.open(pdf_path)
    converted_images = []
    
    pages_to_convert = min(target_count, len(doc))
    
    for page_num in range(pages_to_convert):
        try:
            page = doc[page_num]
            
            # Convert page to very high-resolution image
            mat = pymupdf.Matrix(resolution_scale, resolution_scale)
            pix = page.get_pixmap(matrix=mat)
            
            # Save as high-quality PNG
            img_filename = f"page_{page_num+1:03d}_big.png"
            img_path = os.path.join(output_dir, img_filename)
            pix.save(img_path)
            
            img_info = {
                'filename': img_filename,
                'path': img_path,
                'page': page_num + 1,
                'size': f"{pix.width}x{pix.height}",
                'resolution_scale': f"{resolution_scale}x",
                'file_size': os.path.getsize(img_path)
            }
            
            converted_images.append(img_info)
            print(f"💾 Page {page_num+1} -> {img_filename}")
            print(f"   📏 Size: {img_info['size']} ({img_info['resolution_scale']} scale)")
            print(f"   💾 File size: {img_info['file_size']} bytes")
            
            pix = None
            
        except Exception as e:
            print(f"⚠️ Error converting page {page_num+1}: {e}")
    
    doc.close()
    
    print(f"\n📊 CONVERSION SUMMARY:")
    print(f"   📁 Output directory: {output_dir}")
    print(f"   🖼️ Pages converted: {len(converted_images)}")
    print(f"   🎯 Resolution scale used: {resolution_scale}x")
    
    return converted_images

if __name__ == "__main__":
    pdf_file = "temp/TRANG TỬ NAM HOA KINH.pdf"
    
    # Method 1: Extract embedded images (with upscaling for small images)
    print("=" * 60)
    print("METHOD 1: Extracting embedded images (HIGH-RES)")
    print("=" * 60)
    images = extract_images_from_pdf(
        pdf_file, 
        "extracted_images_big", 
        target_count=20,
        min_size=(1200, 900)  # Minimum size for upscaling
    )
    
    # Method 2: Convert pages to very high-resolution images
    print("\n" + "=" * 60)
    print("METHOD 2: Converting pages to HIGH-RES images")
    print("=" * 60)
    page_images = convert_pages_to_images(
        pdf_file, 
        "page_images_big", 
        target_count=20,
        resolution_scale=4.0  # 4x resolution for very large images
    )
    
    print(f"\n🎯 TOTAL HIGH-RES IMAGES: {len(images) + len(page_images)}")
    print(f"📁 Check folders: 'extracted_images_big' and 'page_images_big'")
    print(f"🖼️ All images should now be much larger and higher quality!") 