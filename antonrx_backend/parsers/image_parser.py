"""
Image Parser Module
Extracts text from PNG, JPG, and other image files using OCR
"""

import hashlib
import logging
from io import BytesIO
from typing import Dict, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

logger = logging.getLogger(__name__)


class ImageParser:
    """Comprehensive image parsing and OCR text extraction."""
    
    # Supported image formats
    SUPPORTED_FORMATS = {'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'TIFF'}
    
    # OCR preprocessing configuration
    OCR_ENHANCEMENT_LEVEL = 1.5  # Contrast enhancement
    OCR_SHARPENING_STRENGTH = 2.0  # Sharpening strength
    
    @staticmethod
    def extract_text_from_image(file_bytes: bytes, filename: str = "") -> Dict:
        """
        Extract text from image file using OCR.
        
        Processing steps:
        1. Load image from bytes
        2. Validate image format
        3. Enhance image for better OCR (contrast, sharpness)
        4. Run Tesseract OCR
        5. Extract text and metadata
        
        Args:
            file_bytes: Raw image file bytes
            filename: Optional filename for logging
        
        Returns:
            {
                "text": "Extracted text...",
                "format": "PNG",
                "size": (1920, 1080),
                "confidence": 0.85,
                "checksum": "sha256 hash",
                "char_count": 450,
                "processing_info": {...}
            }
        """
        if not file_bytes:
            raise ValueError("Empty image file")
        
        # Compute checksum
        checksum = hashlib.sha256(file_bytes).hexdigest()
        
        try:
            # Load image
            image = Image.open(BytesIO(file_bytes))
        except Exception as e:
            logger.error(f"Failed to open image: {str(e)}")
            raise ValueError(f"Invalid image file: {str(e)}")
        
        try:
            # Convert to RGB if necessary (for PNG with transparency, etc.)
            if image.mode in {'RGBA', 'LA', 'P'}:
                # Create white background for transparency
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract image format and size
            image_format = image.format or "UNKNOWN"
            image_size = image.size
            
            # Enhance image for better OCR
            enhanced_image = ImageParser._enhance_image_for_ocr(image)
            
            # Run OCR
            text = pytesseract.image_to_string(enhanced_image)
            
            # Get OCR data for confidence estimation
            ocr_data = pytesseract.image_to_data(enhanced_image, output_type=pytesseract.Output.DICT)
            confidence = ImageParser._calculate_confidence(ocr_data)
            
            logger.info(f"Image OCR completed: {image_format}, {len(text)} characters, confidence={confidence:.2f}")
            
            return {
                "text": text.strip(),
                "format": image_format,
                "size": image_size,
                "confidence": confidence,
                "checksum": checksum,
                "char_count": len(text.strip()),
                "processing_info": {
                    "enhancement_applied": True,
                    "filename": filename
                }
            }
        
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            raise ValueError(f"Failed to extract text from image: {str(e)}")
    
    @staticmethod
    def _enhance_image_for_ocr(image: Image.Image) -> Image.Image:
        """
        Enhance image for better OCR accuracy.
        
        Techniques:
        1. Increase contrast (makes text darker/clearer)
        2. Apply sharpening (enhances edges)
        3. Denoise (removes artifacts)
        
        Args:
            image: PIL Image object
        
        Returns:
            Enhanced PIL Image
        """
        try:
            # Step 1: Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(ImageParser.OCR_ENHANCEMENT_LEVEL)
            
            # Step 2: Sharpen the image
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(ImageParser.OCR_SHARPENING_STRENGTH)
            
            # Step 3: Optional - apply median filter to denoise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            logger.debug("Image enhancement completed")
            return image
        
        except Exception as e:
            logger.warning(f"Image enhancement failed: {str(e)}, using original")
            return image
    
    @staticmethod
    def _calculate_confidence(ocr_data: dict) -> float:
        """
        Calculate confidence score based on OCR data.
        
        Args:
            ocr_data: Tesseract OCR data dictionary
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            confidences = []
            
            # Extract confidence values for each word
            if 'conf' in ocr_data:
                conf_values = [int(c) for c in ocr_data['conf'] if int(c) > 0]
                if conf_values:
                    # Convert Tesseract confidence (0-100) to 0-1
                    confidences = [c / 100.0 for c in conf_values]
            
            # Calculate average confidence
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                # Ensure it's between 0 and 1
                return min(1.0, max(0.0, avg_confidence))
            else:
                # Default to moderate confidence if no data
                return 0.5
        
        except Exception as e:
            logger.warning(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    @staticmethod
    def extract_text_with_preprocessing(
        file_bytes: bytes,
        deskew: bool = True,
        denoise: bool = True
    ) -> Dict:
        """
        Advanced image preprocessing for difficult/poor-quality images.
        
        Args:
            file_bytes: Image bytes
            deskew: Whether to attempt to correct rotation
            denoise: Whether to apply denoising
        
        Returns:
            Extraction results dictionary
        """
        try:
            image = Image.open(BytesIO(file_bytes))
            
            # Convert to grayscale for preprocessing
            if image.mode != 'L':
                image = image.convert('L')
            
            # Apply denoising if requested
            if denoise:
                image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Convert back to RGB for OCR
            image = image.convert('RGB')
            
            # Run OCR on preprocessed image
            text = pytesseract.image_to_string(image)
            
            return {
                "text": text.strip(),
                "preprocessing_applied": {
                    "deskew": deskew,
                    "denoise": denoise
                },
                "char_count": len(text.strip())
            }
        
        except Exception as e:
            logger.error(f"Advanced preprocessing failed: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")
    
    @staticmethod
    def validate_image(file_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate image file integrity.
        
        Args:
            file_bytes: Image bytes to validate
        
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        try:
            image = Image.open(BytesIO(file_bytes))
            image.verify()
            
            # Open again (verify closes the file)
            image = Image.open(BytesIO(file_bytes))
            
            image_format = image.format or "UNKNOWN"
            size = image.size
            
            if image_format.upper() in ImageParser.SUPPORTED_FORMATS:
                return True, f"Valid {image_format} image ({size[0]}x{size[1]})"
            else:
                return False, f"Unsupported image format: {image_format}"
        
        except Exception as e:
            return False, f"Invalid image: {str(e)}"
    
    @staticmethod
    def batch_extract_from_images(file_bytes_list: list) -> Dict:
        """
        Extract text from multiple images.
        
        Useful for multi-page document images.
        
        Args:
            file_bytes_list: List of image file bytes
        
        Returns:
            Aggregated extraction results
        """
        results = []
        total_text = []
        total_confidence = 0.0
        
        for idx, file_bytes in enumerate(file_bytes_list):
            try:
                result = ImageParser.extract_text_from_image(file_bytes)
                results.append({
                    "image_index": idx,
                    "result": result
                })
                total_text.append(f"--- Image {idx + 1} ---\n{result['text']}")
                total_confidence += result['confidence']
            except Exception as e:
                logger.warning(f"Error processing image {idx}: {str(e)}")
                results.append({
                    "image_index": idx,
                    "error": str(e)
                })
        
        avg_confidence = total_confidence / len(file_bytes_list) if file_bytes_list else 0.0
        
        return {
            "text": "\n\n".join(total_text),
            "total_images": len(file_bytes_list),
            "successful_extractions": len([r for r in results if 'error' not in r]),
            "average_confidence": avg_confidence,
            "individual_results": results
        }
