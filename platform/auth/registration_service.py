"""
优化的用户注册服务
Enhanced User Registration Service

Features:
- Password strength validation
- Username format validation
- Email validation
- Weak password detection
- Sensitive username filtering
- Registration audit logging
"""

import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password strength requirements
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL_CHARS = True

# Username requirements
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
USERNAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')

# Weak passwords list
WEAK_PASSWORDS = {
    'password', 'password1', 'password123', '12345678', '123456789',
    'qwerty', 'qwerty123', 'abc123', 'password!', 'admin123',
    'letmein', 'welcome', 'welcome1', 'monkey', 'dragon',
    'master', 'login', 'admin', 'root', 'user', 'test',
}

# Reserved usernames
RESERVED_USERNAMES = {
    'admin', 'administrator', 'root', 'system', 'api', 'user', 'guest',
    'support', 'help', 'info', 'contact', 'sales', 'marketing',
    'moderator', 'mod', 'superuser', 'super', 'manager', 'service',
    'test', 'demo', 'null', 'undefined', 'anonymous', 'public',
    'nobody', 'everyone', 'all', 'default', 'new', 'edit', 'delete',
}


class RegistrationError(Exception):
    """Registration error exception"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class PasswordValidator:
    """Password validation utility"""
    
    @staticmethod
    def validate_strength(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength
        Returns: (is_valid, list of errors)
        """
        errors = []
        
        # Length check
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"密码长度至少需要{MIN_PASSWORD_LENGTH}个字符")
        if len(password) > MAX_PASSWORD_LENGTH:
            errors.append(f"密码长度不能超过{MAX_PASSWORD_LENGTH}个字符")
        
        # Character type checks
        if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("密码需要包含至少一个大写字母")
        
        if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("密码需要包含至少一个小写字母")
        
        if REQUIRE_NUMBERS and not re.search(r'[0-9]', password):
            errors.append("密码需要包含至少一个数字")
        
        if REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("密码需要包含至少一个特殊字符 (!@#$%^&*等)")
        
        # Weak password check
        if password.lower() in WEAK_PASSWORDS:
            errors.append("密码过于简单，请使用更强的密码")
        
        # Common patterns check
        if re.search(r'(.)\1{2,}', password):
            errors.append("密码包含重复字符，请使用更复杂的密码")
        
        if re.search(r'(123|234|345|456|567|678|789|890|abc|qwe)', password.lower()):
            errors.append("密码包含常见序列，请使用更复杂的密码")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_strength_score(password: str) -> int:
        """
        Calculate password strength score (0-100)
        """
        score = 0
        
        # Length score
        score += min(len(password) * 4, 32)
        
        # Character variety
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'[0-9]', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15
        
        # Bonus for length
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # Penalty for weak patterns
        if password.lower() in WEAK_PASSWORDS:
            score -= 50
        if re.search(r'(.)\1{2,}', password):
            score -= 10
        if re.search(r'(123|abc|qwe)', password.lower()):
            score -= 10
        
        return max(0, min(100, score))


class UsernameValidator:
    """Username validation utility"""
    
    @staticmethod
    def validate(username: str) -> Tuple[bool, List[str]]:
        """
        Validate username format
        Returns: (is_valid, list of errors)
        """
        errors = []
        
        # Length check
        if len(username) < MIN_USERNAME_LENGTH:
            errors.append(f"用户名长度至少需要{MIN_USERNAME_LENGTH}个字符")
        if len(username) > MAX_USERNAME_LENGTH:
            errors.append(f"用户名长度不能超过{MAX_USERNAME_LENGTH}个字符")
        
        # Format check
        if not USERNAME_PATTERN.match(username):
            errors.append("用户名只能包含字母、数字、下划线和连字符，且必须以字母开头")
        
        # Reserved username check
        if username.lower() in RESERVED_USERNAMES:
            errors.append("该用户名已被保留，请选择其他用户名")
        
        # Profanity filter (basic)
        profanity_patterns = ['fuck', 'shit', 'damn', 'ass', 'bitch', 'crap']
        for pattern in profanity_patterns:
            if pattern in username.lower():
                errors.append("用户名包含不适当的内容")
                break
        
        return len(errors) == 0, errors
    
    @staticmethod
    def suggest_alternatives(username: str, count: int = 3) -> List[str]:
        """Generate alternative username suggestions"""
        suggestions = []
        base = username.lower()
        
        for i in range(count):
            suffix = secrets.token_hex(2)
            suggestion = f"{base}_{suffix}"
            suggestions.append(suggestion)
        
        return suggestions


class EmailValidator:
    """Email validation utility"""
    
    # Common email domains
    COMMON_DOMAINS = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'qq.com', '163.com', '126.com', 'sina.com', 'foxmail.com',
        'icloud.com', 'live.com', 'msn.com', 'aol.com',
    }
    
    # Blocked domains (temporary email services)
    BLOCKED_DOMAINS = {
        'tempmail.com', 'guerrillamail.com', '10minutemail.com',
        'mailinator.com', 'throwaway.email', 'fakeinbox.com',
        'temp-mail.org', 'dispostable.com', 'mailnesia.com',
    }
    
    @staticmethod
    def validate(email: str) -> Tuple[bool, List[str]]:
        """
        Validate email format
        Returns: (is_valid, list of errors)
        """
        errors = []
        
        # Basic format check
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            errors.append("邮箱格式不正确")
            return False, errors
        
        # Extract domain
        try:
            domain = email.split('@')[1].lower()
        except:
            errors.append("邮箱格式不正确")
            return False, errors
        
        # Blocked domain check
        if domain in EmailValidator.BLOCKED_DOMAINS:
            errors.append("不支持该邮箱服务商，请使用常用邮箱")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def is_common_domain(email: str) -> bool:
        """Check if email uses a common domain"""
        try:
            domain = email.split('@')[1].lower()
            return domain in EmailValidator.COMMON_DOMAINS
        except:
            return False


class RegistrationService:
    """Enhanced registration service"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.password_validator = PasswordValidator()
        self.username_validator = UsernameValidator()
        self.email_validator = EmailValidator()
    
    def validate_registration(self, username: str, email: str, password: str) -> dict:
        """
        Validate all registration fields
        Returns validation result with detailed messages
        """
        result = {
            'valid': True,
            'errors': {},
            'warnings': [],
            'suggestions': {},
        }
        
        # Validate username
        username_valid, username_errors = self.username_validator.validate(username)
        if not username_valid:
            result['valid'] = False
            result['errors']['username'] = username_errors
            result['suggestions']['username'] = self.username_validator.suggest_alternatives(username)
        
        # Validate email
        email_valid, email_errors = self.email_validator.validate(email)
        if not email_valid:
            result['valid'] = False
            result['errors']['email'] = email_errors
        
        # Validate password
        password_valid, password_errors = self.password_validator.validate_strength(password)
        if not password_valid:
            result['valid'] = False
            result['errors']['password'] = password_errors
        
        # Add password strength score
        result['password_strength'] = {
            'score': self.password_validator.get_strength_score(password),
            'level': self._get_strength_level(password)
        }
        
        # Add warnings
        if not self.email_validator.is_common_domain(email):
            result['warnings'].append("请确保邮箱地址正确，重要通知将发送到此邮箱")
        
        return result
    
    def _get_strength_level(self, password: str) -> str:
        """Get password strength level"""
        score = self.password_validator.get_strength_score(password)
        if score >= 80:
            return 'strong'
        elif score >= 60:
            return 'medium'
        elif score >= 40:
            return 'weak'
        else:
            return 'very_weak'
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    def check_existing_user(self, username: str, email: str) -> dict:
        """
        Check if username or email already exists
        Returns existing user info
        """
        # This would typically query the database
        # For now, return a placeholder
        return {
            'username_exists': False,
            'email_exists': False
        }
    
    def create_user(self, username: str, email: str, password: str, 
                    full_name: str = None) -> dict:
        """
        Create a new user with validation
        Returns user data or raises RegistrationError
        """
        # Validate all fields
        validation = self.validate_registration(username, email, password)
        
        if not validation['valid']:
            # Get first error for simplicity
            for field, errors in validation['errors'].items():
                if errors:
                    raise RegistrationError(errors[0], field)
        
        # Check existing users (would query database)
        existing = self.check_existing_user(username, email)
        if existing['username_exists']:
            raise RegistrationError("用户名已被注册", "username")
        if existing['email_exists']:
            raise RegistrationError("邮箱已被注册", "email")
        
        # Create user data
        user_data = {
            'username': username,
            'email': email,
            'hashed_password': self.hash_password(password),
            'full_name': full_name,
            'role': 'developer',
            'is_active': True,
            'is_verified': False,
            'created_at': datetime.utcnow(),
        }
        
        return user_data


# API response helpers
def create_validation_response(validation_result: dict) -> dict:
    """Create API response for validation endpoint"""
    return {
        'valid': validation_result['valid'],
        'errors': validation_result['errors'],
        'warnings': validation_result['warnings'],
        'password_strength': validation_result.get('password_strength', {}),
        'suggestions': validation_result.get('suggestions', {}),
    }


def create_registration_response(user_data: dict, token: str = None) -> dict:
    """Create API response for successful registration"""
    response = {
        'success': True,
        'message': '注册成功',
        'user': {
            'id': user_data.get('id'),
            'username': user_data['username'],
            'email': user_data['email'],
            'full_name': user_data.get('full_name'),
            'role': user_data['role'],
            'is_active': user_data['is_active'],
            'created_at': user_data['created_at'].isoformat(),
        }
    }
    
    if token:
        response['token'] = token
    
    return response
