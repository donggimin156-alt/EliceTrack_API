# core/webdriver/enums.py
from enum import Enum


class BrowserType(str, Enum):
    """지원하는 브라우저 타입을 정의하는 Enum 클래스"""
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    # 향후 SAFARI = "safari", MOBILE = "mobile" 등 추가 용이