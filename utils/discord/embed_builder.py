# utils/discord/embed_builder.py
from typing import Any

# [주의] 팀의 구체적인 명명 규칙에 맞춰 아래 임포트 경로는 적절히 수정해 주세요.
# 예: DiscordColor(Enum형태로 10진수 색상값 관리), DiscordSettings(제한값 관리)
from utils.discord.models import DiscordColor
from utils.discord.settings import DiscordSettings


class DiscordEmbedBuilder:
    """
    Discord Embed 구조(Title, Fields, Footer 등)를 객체 지향적으로 조립하는 Builder 클래스.
    
    메서드 체이닝(Method Chaining)을 지원하여 직관적인 UI 조립을 가능하게 하며, 
    Discord API의 제약 사항(최대 25개 필드)을 안전하게 방어(Truncate)하는 책임을 가집니다.
    """

    def __init__(self, settings: DiscordSettings) -> None:
        """
        DiscordEmbedBuilder 인스턴스를 초기화합니다.
        
        Args:
            settings (DiscordSettings): Discord 제한(Limit) 정보가 담긴 환경 설정 객체
        """
        self.settings = settings
        self.title: str = ""
        self.description: str = ""
        self.fields: list[dict[str, Any]] = []
        self.footer_text: str = ""

    def set_title(self, title: str, icon: str = "") -> "DiscordEmbedBuilder":
        """
        Embed의 메인 제목을 설정합니다. (Slack의 Header 역할)
        
        Args:
            title (str): 제목에 표시할 문자열
            icon (str): 제목 앞에 붙일 이모지 아이콘 (기본값: "")
        """
        self.title = f"{icon} {title}".strip()
        return self

    def set_description(self, description: str) -> "DiscordEmbedBuilder":
        """Embed의 상단 본문(설명글)을 설정합니다."""
        self.description = description
        return self

    def add_field(self, name: str, value: str, inline: bool = True) -> "DiscordEmbedBuilder":
        """
        다단(그리드) 또는 단독 행으로 데이터를 나열할 수 있는 Field를 추가합니다.
        주로 테스트 결과 요약(성공/실패 수, 소요 시간 등)을 표시할 때 사용합니다.
        
        Args:
            name (str): 필드의 제목 (굵은 글씨로 표시됨)
            value (str): 필드의 상세 내용 (마크다운 지원)
            inline (bool): 다른 필드와 가로로 나란히 배치할지 여부 (기본값: True)
        """
        self.fields.append({
            "name": name,
            "value": value,
            "inline": inline
        })
        return self

    def set_footer(self, text: str) -> "DiscordEmbedBuilder":
        """Embed 하단에 작게 표시될 푸터 텍스트를 설정합니다."""
        self.footer_text = text
        return self

    def build_payload(self, color: DiscordColor, username: str = "디스코드 QA 알림봇") -> dict[str, Any]:
        """
        조립된 데이터들을 묶어 최종 Discord Webhook 전송용 Payload(DTO)로 변환합니다.
        
        주의: Discord API는 한 번에 25개를 초과하는 필드 전송을 거부하므로, 
        초과 시 설정값(max_fields)을 기준으로 안전하게 자르고(Truncate) 안내 문구를 덧붙입니다.
        """
        # Discord 필드 제한 방어 (기본 제한은 25개)
        if len(self.fields) > self.settings.max_fields:
            self.fields = self.fields[:self.settings.max_fields - 1]
            self.fields.append({
                "name": "⚠️ [TRUNCATED]",
                "value": "너무 많은 데이터로 인해 일부 필드가 생략되었습니다.",
                "inline": False
            })

        embed = {
            "color": color.value  # 디스코드는 10진수(int) 형태의 색상 코드를 받습니다.
        }

        if self.title:
            embed["title"] = self.title
        if self.description:
            embed["description"] = self.description
        if self.fields:
            embed["fields"] = self.fields
        if self.footer_text:
            embed["footer"] = {"text": self.footer_text}

        return {
            "username": username,
            "embeds": [embed]
        }