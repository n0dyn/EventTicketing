"""
Advanced image processing utilities
"""
import io
import logging
from typing import Tuple, Optional, List, Dict
from pathlib import Path

from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont, ExifTags
import qrcode

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Advanced image processing utilities"""
    
    # Standard sizes for different use cases
    SIZES = {
        "avatar": (150, 150),
        "thumbnail": (200, 200),
        "card": (400, 300),
        "banner": (1200, 400),
        "hero": (1920, 1080),
        "ticket": (600, 300)
    }
    
    @staticmethod
    def optimize_image(
        image: Image.Image,
        max_width: int = 1200,
        max_height: int = 800,
        quality: int = 85
    ) -> Image.Image:
        """Optimize image for web use"""
        # Fix orientation based on EXIF data
        image = ImageProcessor.fix_orientation(image)
        
        # Resize if too large
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])
            image = background
        
        return image
    
    @staticmethod
    def fix_orientation(image: Image.Image) -> Image.Image:
        """Fix image orientation based on EXIF data"""
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            
            exif = image._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    image = image.rotate(180, expand=True)
                elif orientation_value == 6:
                    image = image.rotate(270, expand=True)
                elif orientation_value == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, TypeError):
            # No EXIF data or orientation info
            pass
        
        return image
    
    @staticmethod
    def create_thumbnail(
        image: Image.Image,
        size: Tuple[int, int],
        crop_to_fit: bool = True
    ) -> Image.Image:
        """Create thumbnail with optional cropping"""
        if crop_to_fit:
            # Crop to fit exactly
            from PIL import ImageOps
            return ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        else:
            # Resize maintaining aspect ratio
            image_copy = image.copy()
            image_copy.thumbnail(size, Image.Resampling.LANCZOS)
            return image_copy
    
    @staticmethod
    def add_watermark(
        image: Image.Image,
        watermark_text: str,
        position: str = "bottom-right",
        opacity: float = 0.7
    ) -> Image.Image:
        """Add text watermark to image"""
        # Create a transparent overlay
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Try to use a nice font
        try:
            # You might need to adjust the font path based on your system
            font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 20)
        except OSError:
            font = ImageFont.load_default()
        
        # Calculate text size and position
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if position == "bottom-right":
            x = image.width - text_width - 20
            y = image.height - text_height - 20
        elif position == "bottom-left":
            x = 20
            y = image.height - text_height - 20
        elif position == "top-right":
            x = image.width - text_width - 20
            y = 20
        else:  # top-left
            x = 20
            y = 20
        
        # Draw text with semi-transparent background
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, int(128 * opacity))
        )
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, int(255 * opacity)))
        
        # Combine with original image
        return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    
    @staticmethod
    def generate_qr_code(
        data: str,
        size: Tuple[int, int] = (300, 300),
        border: int = 4
    ) -> Image.Image:
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Resize to requested size
        if qr_image.size != size:
            qr_image = qr_image.resize(size, Image.Resampling.LANCZOS)
        
        return qr_image
    
    @staticmethod
    def create_ticket_image(
        event_title: str,
        event_date: str,
        venue: str,
        ticket_id: str,
        qr_data: str,
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """Create a ticket image with QR code"""
        # Create ticket canvas
        width, height = 600, 300
        ticket = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(ticket)
        
        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 24)
            normal_font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 16)
            small_font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 12)
        except OSError:
            title_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw ticket border
        draw.rectangle([10, 10, width-10, height-10], outline=(0, 0, 0), width=2)
        
        # Draw title
        draw.text((20, 30), event_title[:40], font=title_font, fill=(0, 0, 0))
        
        # Draw event details
        draw.text((20, 70), f"Date: {event_date}", font=normal_font, fill=(0, 0, 0))
        draw.text((20, 95), f"Venue: {venue}", font=normal_font, fill=(0, 0, 0))
        draw.text((20, 120), f"Ticket ID: {ticket_id}", font=small_font, fill=(100, 100, 100))
        
        # Add QR code
        qr_image = ImageProcessor.generate_qr_code(qr_data, size=(120, 120))
        ticket.paste(qr_image, (width - 140, height - 140))
        
        # Add QR code label
        draw.text((width - 140, height - 15), "Scan for entry", font=small_font, fill=(100, 100, 100))
        
        return ticket
    
    @staticmethod
    def create_event_banner(
        background_image: Image.Image,
        title: str,
        subtitle: str = "",
        overlay_opacity: float = 0.5
    ) -> Image.Image:
        """Create an event banner with text overlay"""
        # Resize background to banner size
        banner = ImageProcessor.create_thumbnail(
            background_image, 
            ImageProcessor.SIZES["banner"], 
            crop_to_fit=True
        )
        
        # Create overlay
        overlay = Image.new('RGBA', banner.size, (0, 0, 0, int(255 * overlay_opacity)))
        banner = banner.convert('RGBA')
        banner = Image.alpha_composite(banner, overlay)
        
        # Draw text
        draw = ImageDraw.Draw(banner)
        
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 48)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 24)
        except OSError:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Calculate text positions (centered)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (banner.width - title_width) // 2
        title_y = banner.height // 2 - 50
        
        # Draw title
        draw.text((title_x, title_y), title, font=title_font, fill=(255, 255, 255))
        
        # Draw subtitle if provided
        if subtitle:
            subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (banner.width - subtitle_width) // 2
            subtitle_y = title_y + 60
            draw.text((subtitle_x, subtitle_y), subtitle, font=subtitle_font, fill=(200, 200, 200))
        
        return banner.convert('RGB')


# Global image processor instance
image_processor = ImageProcessor()