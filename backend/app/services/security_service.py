"""
Security service for monitoring and threat detection
"""
import hashlib
import hmac
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: str
    user_id: Optional[int]
    ip_address: str
    user_agent: str
    timestamp: datetime
    details: Dict[str, Any]
    severity: str  # low, medium, high, critical


class ThreatDetectionService:
    """Service for detecting security threats"""
    
    def __init__(self):
        self.failed_login_attempts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.suspicious_ips: Dict[str, Dict[str, Any]] = {}
        self.security_events: List[SecurityEvent] = []
    
    def record_failed_login(self, ip_address: str, email: str, user_agent: str):
        """Record a failed login attempt"""
        current_time = datetime.utcnow()
        
        # Track failed attempts by IP
        self.failed_login_attempts[ip_address].append({
            'timestamp': current_time,
            'email': email,
            'user_agent': user_agent
        })
        
        # Check for brute force attack
        recent_failures = [
            attempt for attempt in self.failed_login_attempts[ip_address]
            if current_time - attempt['timestamp'] < timedelta(minutes=15)
        ]
        
        if len(recent_failures) >= 5:
            self.flag_suspicious_ip(ip_address, "brute_force_login", {
                "failed_attempts": len(recent_failures),
                "emails_targeted": list(set(attempt['email'] for attempt in recent_failures))
            })
        
        # Log security event
        self.log_security_event(
            event_type="failed_login",
            user_id=None,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email, "attempt_count": len(recent_failures)},
            severity="medium" if len(recent_failures) >= 3 else "low"
        )
    
    def record_successful_login(self, user_id: int, ip_address: str, user_agent: str):
        """Record a successful login"""
        # Clear failed attempts for this IP
        if ip_address in self.failed_login_attempts:
            self.failed_login_attempts[ip_address].clear()
        
        # Check for suspicious login patterns
        if self.is_suspicious_login(user_id, ip_address, user_agent):
            self.log_security_event(
                event_type="suspicious_login",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "unusual_location_or_device"},
                severity="medium"
            )
    
    def is_suspicious_login(self, user_id: int, ip_address: str, user_agent: str) -> bool:
        """Check if login appears suspicious"""
        # In a real implementation, you'd check:
        # - Geographic location changes
        # - Device fingerprinting
        # - Time-based patterns
        # - Known malicious IPs
        
        # Simplified check for demo
        suspicious_patterns = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap',
            'burp', 'w3af', 'skipfish', 'arachni'
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)
    
    def flag_suspicious_ip(self, ip_address: str, reason: str, details: Dict[str, Any]):
        """Flag an IP address as suspicious"""
        self.suspicious_ips[ip_address] = {
            'flagged_at': datetime.utcnow(),
            'reason': reason,
            'details': details,
            'blocked': False  # For future implementation
        }
        
        logger.warning(f"Suspicious IP flagged: {ip_address} - {reason}")
    
    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        details: Dict[str, Any],
        severity: str
    ):
        """Log a security event"""
        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
            details=details,
            severity=severity
        )
        
        self.security_events.append(event)
        
        # Keep only recent events in memory (last 1000)
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Log high-severity events immediately
        if severity in ['high', 'critical']:
            logger.error(f"Security event: {event_type} - {details}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary for admin dashboard"""
        current_time = datetime.utcnow()
        
        # Recent events (last 24 hours)
        recent_events = [
            event for event in self.security_events
            if current_time - event.timestamp < timedelta(hours=24)
        ]
        
        # Group by severity
        severity_counts = defaultdict(int)
        for event in recent_events:
            severity_counts[event.severity] += 1
        
        # Top suspicious IPs
        suspicious_ips = list(self.suspicious_ips.items())[:10]
        
        return {
            "total_events_24h": len(recent_events),
            "severity_breakdown": dict(severity_counts),
            "suspicious_ips": suspicious_ips,
            "active_threats": len(self.suspicious_ips),
            "last_updated": current_time
        }
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address should be blocked"""
        if ip_address in self.suspicious_ips:
            suspicious_info = self.suspicious_ips[ip_address]
            # Auto-block IPs flagged for brute force
            if suspicious_info['reason'] == 'brute_force_login':
                return True
        
        return False


class PasswordSecurityService:
    """Service for password security operations"""
    
    @staticmethod
    def check_password_strength(password: str) -> Dict[str, Any]:
        """Comprehensive password strength check"""
        score = 0
        feedback = []
        
        # Length check
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            feedback.append("Password should be at least 8 characters long")
        
        # Character variety
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        char_types = sum([has_lower, has_upper, has_digit, has_special])
        score += char_types
        
        if not has_lower:
            feedback.append("Add lowercase letters")
        if not has_upper:
            feedback.append("Add uppercase letters") 
        if not has_digit:
            feedback.append("Add numbers")
        if not has_special:
            feedback.append("Add special characters")
        
        # Common password patterns
        common_patterns = [
            r'(.)\1{2,}',  # Repeated characters
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
        ]
        
        import re
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                score -= 1
                feedback.append("Avoid repeated or sequential characters")
                break
        
        # Common passwords check (simplified)
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        
        if password.lower() in common_passwords:
            score = 0
            feedback.append("This is a commonly used password")
        
        # Calculate strength
        if score >= 6:
            strength = "strong"
        elif score >= 4:
            strength = "medium"
        else:
            strength = "weak"
        
        return {
            "strength": strength,
            "score": max(0, score),
            "feedback": feedback,
            "meets_requirements": score >= 4
        }
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def hash_password_with_pepper(password: str, salt: str) -> str:
        """Hash password with additional pepper for extra security"""
        pepper = settings.SECRET_KEY  # Use app secret as pepper
        combined = password + salt + pepper
        return hashlib.pbkdf2_hex(combined.encode(), salt.encode(), 100000, 64)


class APISecurityService:
    """Service for API security operations"""
    
    @staticmethod
    def generate_api_key(user_id: int) -> str:
        """Generate API key for user"""
        timestamp = str(int(time.time()))
        message = f"{user_id}:{timestamp}"
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"etk_{user_id}_{timestamp}_{signature[:16]}"
    
    @staticmethod
    def validate_api_key(api_key: str) -> Optional[int]:
        """Validate API key and return user ID"""
        try:
            if not api_key.startswith("etk_"):
                return None
            
            parts = api_key[4:].split("_")
            if len(parts) != 3:
                return None
            
            user_id, timestamp, signature = parts
            
            # Check if key is not too old (1 year)
            if int(time.time()) - int(timestamp) > 365 * 24 * 3600:
                return None
            
            # Verify signature
            message = f"{user_id}:{timestamp}"
            expected_signature = hmac.new(
                settings.SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()[:16]
            
            if hmac.compare_digest(signature, expected_signature):
                return int(user_id)
            
        except (ValueError, TypeError):
            pass
        
        return None
    
    @staticmethod
    async def log_api_usage(
        db: AsyncSession,
        user_id: int,
        endpoint: str,
        method: str,
        ip_address: str,
        response_status: int
    ):
        """Log API usage for monitoring and billing"""
        # In a real implementation, you'd store this in a separate table
        # For now, just log it
        logger.info(
            f"API_USAGE: user_id={user_id}, endpoint={endpoint}, "
            f"method={method}, ip={ip_address}, status={response_status}"
        )


# Global threat detection service instance
threat_detection = ThreatDetectionService()