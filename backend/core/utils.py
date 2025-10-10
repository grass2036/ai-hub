"""
Utility functions for AI Hub Platform
通用工具函数
"""

import re
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from uuid import UUID

from pydantic import BaseModel


def generate_slug(name: str) -> str:
    """
    Generate URL-friendly slug from name

    Args:
        name: Input name string

    Returns:
        URL-friendly slug
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'\s+', '-', name.lower())
    # Remove special characters except hyphens and underscores
    slug = re.sub(r'[^a-z0-9-_]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-_')

    # Ensure slug is not empty
    if not slug:
        slug = f"item-{secrets.token_hex(4)}"

    return slug


def validate_email(email: str) -> bool:
    """
    Validate email format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input

    Args:
        text: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(text, str):
        text = str(text)

    # Remove leading/trailing whitespace
    text = text.strip()

    # Apply length limit if specified
    if max_length is not None:
        text = text[:max_length]

    return text


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely load JSON string

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely dump object to JSON string

    Args:
        obj: Object to serialize
        default: Default string if serialization fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return default


def generate_uuid() -> str:
    """Generate a new UUID string"""
    return str(UUID(secrets.token_bytes(16)))


def generate_token(length: int = 32) -> str:
    """
    Generate secure random token

    Args:
        length: Token length in bytes

    Returns:
        Hexadecimal token string
    """
    return secrets.token_hex(length)


def hash_string(text: str, salt: Optional[str] = None) -> str:
    """
    Hash string using SHA-256

    Args:
        text: Text to hash
        salt: Optional salt for hashing

    Returns:
        Hexadecimal hash
    """
    if salt:
        text = f"{salt}{text}"

    return hashlib.sha256(text.encode()).hexdigest()


def verify_hash(text: str, hashed: str, salt: Optional[str] = None) -> bool:
    """
    Verify text against hash

    Args:
        text: Original text
        hashed: Hash to verify against
        salt: Optional salt used for hashing

    Returns:
        True if hash matches, False otherwise
    """
    return secrets.compare_digest(hash_string(text, salt), hashed)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string

    Args:
        dt: Datetime object
        format_str: Format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    Parse datetime string

    Args:
        dt_str: Datetime string
        format_str: Expected format

    Returns:
        Parsed datetime or None if parsing fails
    """
    try:
        return datetime.strptime(dt_str, format_str)
    except ValueError:
        return None


def get_date_range(period: str) -> tuple[datetime, datetime]:
    """
    Get date range for a given period

    Args:
        period: Period type ('today', 'yesterday', 'this_week', 'last_week', 'this_month', 'last_month', 'last_30_days')

    Returns:
        Tuple of (start_date, end_date)
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        start_date = today
        end_date = today + timedelta(days=1)
    elif period == "yesterday":
        start_date = today - timedelta(days=1)
        end_date = today
    elif period == "this_week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=7)
    elif period == "last_week":
        start_date = today - timedelta(days=today.weekday() + 7)
        end_date = start_date + timedelta(days=7)
    elif period == "this_month":
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1)
        else:
            end_date = datetime(today.year, today.month + 1, 1)
    elif period == "last_month":
        if today.month == 1:
            start_date = datetime(today.year - 1, 12, 1)
            end_date = datetime(today.year, 1, 1)
        else:
            start_date = datetime(today.year, today.month - 1, 1)
            end_date = datetime(today.year, today.month, 1)
    else:  # last_30_days or default
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)

    return start_date, end_date


def calculate_percentage(part: Union[int, float], total: Union[int, float]) -> float:
    """
    Calculate percentage

    Args:
        part: Part value
        total: Total value

    Returns:
        Percentage (0-100)
    """
    if total == 0:
        return 0.0

    return float(part) / float(total) * 100


def format_currency(amount: Union[int, float], currency: str = "USD") -> str:
    """
    Format currency amount

    Args:
        amount: Amount to format
        currency: Currency code

    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "GBP":
        return f"£{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def format_number(number: Union[int, float]) -> str:
    """
    Format number with thousand separators

    Args:
        number: Number to format

    Returns:
        Formatted number string
    """
    return f"{number:,}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries

    Args:
        dict1: First dictionary
        dict2: Second dictionary

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def extract_fields(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Extract specific fields from dictionary

    Args:
        data: Source dictionary
        fields: List of field names to extract

    Returns:
        Dictionary with extracted fields
    """
    return {field: data.get(field) for field in fields if field in data}


def remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None values from dictionary

    Args:
        data: Input dictionary

    Returns:
        Dictionary without None values
    """
    return {k: v for k, v in data.items() if v is not None}


def convert_to_snake_case(text: str) -> str:
    """
    Convert text to snake_case

    Args:
        text: Input text

    Returns:
        snake_case text
    """
    # Insert underscores before capital letters and convert to lowercase
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def convert_to_camel_case(text: str) -> str:
    """
    Convert text to camelCase

    Args:
        text: Input text (snake_case or kebab-case)

    Returns:
        camelCase text
    """
    parts = text.replace('-', '_').split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data (like API keys)

    Args:
        data: Sensitive data string
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at the end

    Returns:
        Masked data string
    """
    if len(data) <= visible_chars:
        return mask_char * len(data)

    visible_part = data[-visible_chars:]
    masked_part = mask_char * (len(data) - visible_chars)

    return masked_part + visible_part


def validate_uuid(uuid_str: str) -> bool:
    """
    Validate UUID string

    Args:
        uuid_str: UUID string to validate

    Returns:
        True if valid UUID, False otherwise
    """
    try:
        UUID(uuid_str)
        return True
    except ValueError:
        return False


def paginate_list(items: List[Any], page: int, page_size: int) -> Dict[str, Any]:
    """
    Paginate a list of items

    Args:
        items: List of items to paginate
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Dictionary with paginated data
    """
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size

    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = items[start_idx:end_idx]

    return {
        "items": page_items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry function on exception

    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            import asyncio

            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise last_exception

        def sync_wrapper(*args, **kwargs):
            import time

            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise last_exception

        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class Timer:
    """Context manager for timing operations"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.utcnow()
        self.elapsed = self.end_time - self.start_time

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds"""
        if self.elapsed:
            return self.elapsed.total_seconds()
        return 0.0


class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for identifier

        Args:
            identifier: Unique identifier (IP address, user ID, etc.)

        Returns:
            True if request is allowed, False otherwise
        """
        now = datetime.utcnow()

        if identifier not in self.requests:
            self.requests[identifier] = []

        # Remove old requests outside the time window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if (now - req_time).total_seconds() < self.time_window
        ]

        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True

        return False