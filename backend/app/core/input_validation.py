"""
Advanced input validation and sanitization
"""
import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, validator, Field
from fastapi import HTTPException, status


class InputSanitizer:
    """Input sanitization utilities"""
    
    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?-?\.?\s?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$')
    URL_PATTERN = re.compile(r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:\w*))?)?$')
    
    # Dangerous characters and patterns
    XSS_PATTERNS = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe.*?>.*?</iframe>',
        r'<object.*?>.*?</object>',
        r'<embed.*?>.*?</embed>',
        r'<link.*?>',
        r'<meta.*?>',
        r'data:text/html',
        r'vbscript:',
    ]
    
    SQL_INJECTION_PATTERNS = [
        r"('\s*(or|and)\s*')",
        r"(;\s*(drop|delete|update|insert|create|alter)\s+)",
        r"(union\s+select)",
        r"(exec\s*\()",
        r"(script\s*>)",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # HTML escape
        value = html.escape(value)
        
        # Remove potential XSS patterns
        for pattern in cls.XSS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Trim whitespace
        value = value.strip()
        
        # Enforce maximum length
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @classmethod
    def sanitize_sql_string(cls, value: str) -> str:
        """Additional sanitization for database queries"""
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        return cls.sanitize_string(value)
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate and sanitize email"""
        email = cls.sanitize_string(email, max_length=254).lower()
        
        if not cls.EMAIL_PATTERN.match(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        return email
    
    @classmethod
    def validate_phone(cls, phone: str) -> str:
        """Validate and sanitize phone number"""
        phone = re.sub(r'[^\d+]', '', phone)  # Keep only digits and +
        
        if not cls.PHONE_PATTERN.match(phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format"
            )
        
        return phone
    
    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate and sanitize URL"""
        url = cls.sanitize_string(url, max_length=2048)
        
        if not cls.URL_PATTERN.match(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
        
        # Additional security: only allow specific schemes
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HTTP and HTTPS URLs are allowed"
            )
        
        return url
    
    @classmethod
    def validate_decimal(cls, value: Union[str, float, int], max_digits: int = 10, decimal_places: int = 2) -> Decimal:
        """Validate and convert to decimal"""
        try:
            decimal_value = Decimal(str(value))
            
            # Check for reasonable range
            if decimal_value < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Negative values not allowed"
                )
            
            if decimal_value > Decimal('9' * (max_digits - decimal_places) + '.' + '9' * decimal_places):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Value too large"
                )
            
            # Round to specified decimal places
            return decimal_value.quantize(Decimal('0.01'))
            
        except (InvalidOperation, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid decimal value"
            )
    
    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """Validate and sanitize filename"""
        # Remove directory traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:251 - len(ext)] + '.' + ext if ext else name[:255]
        
        if not filename or filename in ['.', '..']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )
        
        return filename


class SecureBaseModel(BaseModel):
    """Base model with input sanitization"""
    
    class Config:
        # Validate assignment to catch changes after creation
        validate_assignment = True
        # Use enum values instead of enum objects
        use_enum_values = True
        # Allow population by field name or alias
        allow_population_by_field_name = True
    
    def __setattr__(self, name: str, value: Any) -> None:
        # Sanitize string values
        if isinstance(value, str) and hasattr(self.__fields__.get(name), 'field_info'):
            field_info = self.__fields__[name].field_info
            max_length = getattr(field_info, 'max_length', None)
            value = InputSanitizer.sanitize_string(value, max_length)
        
        super().__setattr__(name, value)


class UserInputValidation(SecureBaseModel):
    """Validation schema for user input"""
    
    email: str = Field(..., max_length=254)
    full_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('email')
    def validate_email(cls, v):
        return InputSanitizer.validate_email(v)
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v is None:
            return v
        
        # Check for realistic name patterns
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', v):
            raise ValueError('Name contains invalid characters')
        
        return InputSanitizer.sanitize_string(v, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for common patterns
        if v.lower() in ['password', '12345678', 'qwerty123']:
            raise ValueError('Password is too common')
        
        # Require at least one letter and one number
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'[0-9]', v):
            raise ValueError('Password must contain both letters and numbers')
        
        return v


class EventInputValidation(SecureBaseModel):
    """Validation schema for event input"""
    
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=500)
    start_date: datetime
    end_date: Optional[datetime] = None
    max_attendees: Optional[int] = Field(None, gt=0, le=1000000)
    
    @validator('title')
    def validate_title(cls, v):
        v = InputSanitizer.sanitize_string(v, max_length=200)
        if len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters long')
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_string(v, max_length=5000)
    
    @validator('location')
    def validate_location(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_string(v, max_length=500)
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v is not None and 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('start_date')
    def validate_start_date(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('Event start date must be in the future')
        return v


class PaymentInputValidation(SecureBaseModel):
    """Validation schema for payment input"""
    
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    payment_method_id: str = Field(..., max_length=100)
    
    @validator('amount')
    def validate_amount(cls, v):
        return InputSanitizer.validate_decimal(v)
    
    @validator('currency')
    def validate_currency(cls, v):
        v = v.upper()
        if v not in ['USD', 'EUR', 'GBP', 'CAD', 'AUD']:
            raise ValueError('Unsupported currency')
        return v
    
    @validator('payment_method_id')
    def validate_payment_method_id(cls, v):
        # Stripe payment method IDs have specific format
        if not re.match(r'^pm_[a-zA-Z0-9]{24}$', v):
            raise ValueError('Invalid payment method ID format')
        return v


def validate_file_upload(filename: str, content_type: str, file_size: int, max_size: int = 10 * 1024 * 1024):
    """Validate file upload parameters"""
    
    # Validate filename
    filename = InputSanitizer.validate_filename(filename)
    
    # Validate file size
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {file_size} exceeds maximum allowed size {max_size}"
        )
    
    # Validate content type
    allowed_types = {
        'image/jpeg', 'image/png', 'image/webp', 'image/gif',
        'application/pdf', 'text/plain', 'text/csv',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    }
    
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {content_type} not allowed"
        )
    
    return filename


def sanitize_search_query(query: str) -> str:
    """Sanitize search query to prevent injection attacks"""
    if not query:
        return ""
    
    # Remove special characters that could be used for injection
    query = re.sub(r'[<>\'";\\%_]', '', query)
    
    # Limit length
    query = query[:100]
    
    # Remove excessive whitespace
    query = ' '.join(query.split())
    
    return query.strip()