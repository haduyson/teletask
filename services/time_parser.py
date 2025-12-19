"""
Vietnamese Time Parser
Parses Vietnamese time expressions to datetime objects

Supported formats:
- Hour: 10h, 10h30, 14:30, 10 giờ 30
- Period: sáng, trưa, chiều, tối, đêm
- Relative: hôm nay, ngày mai, ngày kia
- Weekday: thứ 2, thứ hai, t2, chủ nhật
- Date: 15/12, 15/12/2025
"""

import re
import calendar
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz


class VietnameseTimeParser:
    """Parse Vietnamese time expressions."""

    def __init__(self, timezone: str = "Asia/Ho_Chi_Minh"):
        self.TZ = pytz.timezone(timezone)

    # Time patterns: (regex, group_info)
    TIME_PATTERNS = [
        (r"(\d{1,2})h(\d{2})?(?!\d)", "hour_h"),  # 10h, 10h30
        (r"(\d{1,2})\s*giờ\s*(\d{2})?(?:\s*phút)?", "hour_gio"),  # 10 giờ 30
        (r"(\d{1,2}):(\d{2})", "hour_colon"),  # 14:30
    ]

    # Period keywords: (start_hour, end_hour, add_12_if_hour_less_than_12)
    PERIOD_KEYWORDS = {
        "sáng": (5, 12, False),
        "trưa": (11, 14, False),
        "chiều": (12, 18, True),
        "tối": (18, 23, True),
        "đêm": (21, 5, True),
    }

    # Weekday mapping (Monday = 0)
    WEEKDAY_MAP = {
        "thứ 2": 0, "thứ hai": 0, "t2": 0, "hai": 0,
        "thứ 3": 1, "thứ ba": 1, "t3": 1, "ba": 1,
        "thứ 4": 2, "thứ tư": 2, "t4": 2, "tư": 2,
        "thứ 5": 3, "thứ năm": 3, "t5": 3, "năm": 3,
        "thứ 6": 4, "thứ sáu": 4, "t6": 4, "sáu": 4,
        "thứ 7": 5, "thứ bảy": 5, "t7": 5, "bảy": 5,
        "chủ nhật": 6, "cn": 6,
    }

    # Relative day mapping
    RELATIVE_MAP = {
        "hôm nay": 0,
        "ngày mai": 1,
        "ngày kia": 2,
        "hôm qua": -1,
        "mai": 1,
    }

    def extract_datetime(self, text: str) -> Tuple[Optional[datetime], str]:
        """
        Extract datetime from Vietnamese text.

        Args:
            text: Input text containing time expression

        Returns:
            Tuple of (parsed datetime or None, remaining text)
        """
        text_lower = text.lower()
        now = datetime.now(self.TZ)
        result_dt = None
        matched_parts = []

        # Step 1: Try relative keywords (hôm nay, ngày mai, etc.)
        for keyword, days in self.RELATIVE_MAP.items():
            if keyword in text_lower:
                result_dt = now + timedelta(days=days)
                matched_parts.append(keyword)
                text_lower = text_lower.replace(keyword, " ")
                break

        # Step 1.5: Try special keywords (cuối tuần, cuối tháng)
        if not result_dt:
            # "cuối tuần" = Saturday of current week
            if re.search(r"cuối\s*tuần", text_lower):
                days_until_saturday = (5 - now.weekday()) % 7
                if days_until_saturday == 0 and now.hour >= 12:
                    days_until_saturday = 7  # Next Saturday if already past noon on Saturday
                result_dt = now + timedelta(days=days_until_saturday)
                matched_parts.append("cuối tuần")
                text_lower = re.sub(r"cuối\s*tuần", " ", text_lower)

            # "cuối tháng" = last day of current month
            elif re.search(r"cuối\s*tháng", text_lower):
                last_day = calendar.monthrange(now.year, now.month)[1]
                result_dt = self.TZ.localize(datetime(now.year, now.month, last_day))
                matched_parts.append("cuối tháng")
                text_lower = re.sub(r"cuối\s*tháng", " ", text_lower)

        # Step 2: Try weekday patterns
        if not result_dt:
            for weekday, day_num in self.WEEKDAY_MAP.items():
                pattern = rf"\b{re.escape(weekday)}\b"
                if re.search(pattern, text_lower):
                    result_dt = self._next_weekday(now, day_num)

                    # Check for "tuần sau" or "tuần này"
                    if re.search(r"tuần\s*sau", text_lower):
                        result_dt += timedelta(days=7)
                        text_lower = re.sub(r"tuần\s*sau", " ", text_lower)
                    elif re.search(r"tuần\s*này", text_lower):
                        text_lower = re.sub(r"tuần\s*này", " ", text_lower)

                    matched_parts.append(weekday)
                    text_lower = re.sub(pattern, " ", text_lower)
                    break

        # Step 3: Try date patterns (dd/mm or dd/mm/yyyy)
        if not result_dt:
            date_match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", text_lower)
            if date_match:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = int(date_match.group(3)) if date_match.group(3) else now.year

                # If date has passed this year, use next year
                if not date_match.group(3):
                    test_date = datetime(year, month, day)
                    if test_date.date() < now.date():
                        year += 1

                try:
                    result_dt = self.TZ.localize(datetime(year, month, day))
                    matched_parts.append(date_match.group(0))
                    text_lower = text_lower.replace(date_match.group(0), " ")
                except ValueError:
                    pass  # Invalid date

        # Step 4: Extract time (hour:minute)
        hour = None
        minute = 0

        for pattern, _ in self.TIME_PATTERNS:
            time_match = re.search(pattern, text_lower, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0

                # Validate hour/minute
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    matched_parts.append(time_match.group(0))
                    text_lower = text_lower.replace(time_match.group(0), " ")
                else:
                    hour = None
                break

        # Step 5: Apply period keywords (sáng/chiều/tối)
        if hour is not None:
            for period, (_, _, add_12) in self.PERIOD_KEYWORDS.items():
                if period in text_lower:
                    if add_12 and hour < 12:
                        hour += 12
                    elif not add_12 and hour == 12:
                        hour = 0  # 12h sáng = 0:00? No, keep 12
                    matched_parts.append(period)
                    text_lower = text_lower.replace(period, " ")
                    break

        # Step 6: Combine date and time
        if result_dt and hour is not None:
            result_dt = result_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif result_dt and hour is None:
            # Date without time: set to current time or 9:00 AM
            result_dt = result_dt.replace(hour=9, minute=0, second=0, microsecond=0)
        elif hour is not None and not result_dt:
            # Time without date: today or tomorrow if time has passed
            result_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if result_dt < now:
                result_dt += timedelta(days=1)

        # Clean remaining text
        remaining = re.sub(r"\s+", " ", text_lower).strip()

        return result_dt, remaining

    def _next_weekday(self, now: datetime, weekday: int) -> datetime:
        """
        Get next occurrence of weekday.

        Args:
            now: Current datetime
            weekday: Target weekday (0=Monday, 6=Sunday)

        Returns:
            Datetime of next occurrence
        """
        days_ahead = weekday - now.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return now + timedelta(days=days_ahead)

    def format_datetime(self, dt: datetime) -> str:
        """
        Format datetime in Vietnamese style.

        Args:
            dt: Datetime to format

        Returns:
            Formatted string like "14:30 Thứ 2, 15/12/2025"
        """
        weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
        weekday = weekday_names[dt.weekday()]
        return f"{dt.strftime('%H:%M')} {weekday}, {dt.strftime('%d/%m/%Y')}"

    def format_relative(self, dt: datetime) -> str:
        """
        Format datetime relative to now.

        Args:
            dt: Datetime to format

        Returns:
            Relative string like "Ngày mai 14:30" or "15/12 14:30"
        """
        now = datetime.now(self.TZ)
        delta = (dt.date() - now.date()).days

        time_str = dt.strftime("%H:%M")

        if delta == 0:
            return f"Hôm nay {time_str}"
        elif delta == 1:
            return f"Ngày mai {time_str}"
        elif delta == 2:
            return f"Ngày kia {time_str}"
        elif delta == -1:
            return f"Hôm qua {time_str}"
        elif 2 < delta <= 7:
            weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
            return f"{weekday_names[dt.weekday()]} {time_str}"
        else:
            return f"{dt.strftime('%d/%m')} {time_str}"


# Convenience function
def parse_vietnamese_time(text: str, timezone: str = "Asia/Ho_Chi_Minh") -> Tuple[Optional[datetime], str]:
    """
    Parse Vietnamese time expression.

    Args:
        text: Input text
        timezone: Timezone name

    Returns:
        Tuple of (datetime or None, remaining text)
    """
    parser = VietnameseTimeParser(timezone)
    return parser.extract_datetime(text)
