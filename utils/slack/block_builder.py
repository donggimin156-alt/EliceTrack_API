# utils/slack/block_builder.py
from typing import Any

from utils.slack.models import SlackColor
from utils.slack.settings import SlackSettings


class SlackBlockBuilder:
    """
    Slack Block Kit 구조(Header, Section, Divider 등)를 객체 지향적으로 조립하는 Builder 클래스.
    
    메서드 체이닝(Method Chaining)을 지원하여 직관적인 UI 조립을 가능하게 하며, 
    Slack API의 제약 사항(최대 50개 블록)을 안전하게 방어(Truncate)하는 책임을 가집니다.
    순수하게 데이터(딕셔너리)를 조립하는 역할만 하므로 로깅 로직은 배제했습니다.
    """

    def __init__(self, settings: SlackSettings) -> None:
        """
        SlackBlockBuilder 인스턴스를 초기화합니다.
        
        Args:
            settings (SlackSettings): Slack 제한(Limit) 정보가 담긴 환경 설정 객체
        """
        self.settings = settings
        self.blocks: list[dict[str, Any]] = []

    def add_header(self, text: str, icon: str = "") -> "SlackBlockBuilder":
        """
        메시지의 큰 제목이 되는 헤더(Header) 블록을 추가합니다.
        
        Args:
            text (str): 헤더에 표시할 문자열
            icon (str): 제목 앞에 붙일 이모지 아이콘 (기본값: "")
            
        Returns:
            SlackBlockBuilder: Method Chaining을 위한 자기 자신 인스턴스
        """
        header_text = f"{icon} {text}".strip()
        self.blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True}
        })
        return self

    def add_section_fields(self, fields: list[str]) -> "SlackBlockBuilder":
        """
        다단(그리드)으로 데이터를 나열할 수 있는 Section(fields) 블록을 추가합니다.
        주로 테스트 결과 요약(성공/실패 수, 소요 시간 등)을 표시할 때 사용합니다.
        
        Args:
            fields (list[str]): 마크다운이 적용된 문자열 리스트
            
        Returns:
            SlackBlockBuilder: Method Chaining을 위한 자기 자신 인스턴스
        """
        formatted_fields = [{"type": "mrkdwn", "text": f} for f in fields]
        self.blocks.append({
            "type": "section",
            "fields": formatted_fields
        })
        return self

    def add_divider(self) -> "SlackBlockBuilder":
        """
        가로 구분선(Divider) 블록을 추가하여 콘텐츠를 시각적으로 분리합니다.
        
        Returns:
            SlackBlockBuilder: Method Chaining을 위한 자기 자신 인스턴스
        """
        self.blocks.append({"type": "divider"})
        return self

    def add_text_section(self, text: str) -> "SlackBlockBuilder":
        """
        단일 마크다운 텍스트를 길게 출력하는 Section 블록을 추가합니다.
        주로 실패한 테스트 케이스 목록을 나열할 때 사용합니다.
        
        Args:
            text (str): 출력할 마크다운 문자열
            
        Returns:
            SlackBlockBuilder: Method Chaining을 위한 자기 자신 인스턴스
        """
        self.blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        })
        return self

    def add_button(self, text: str, url: str) -> "SlackBlockBuilder":
        """
        클릭 가능한 액션 버튼(Actions) 블록을 추가합니다. 
        CI/CD 파이프라인이나 Allure Report 링크를 연결할 때 유용합니다.
        
        Args:
            text (str): 버튼 내부에 표시될 텍스트
            url (str): 버튼 클릭 시 이동할 타겟 URL
            
        Returns:
            SlackBlockBuilder: Method Chaining을 위한 자기 자신 인스턴스
        """
        self.blocks.append({
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": text},
                "url": url
            }]
        })
        return self

    def build_payload(self, color: SlackColor) -> dict[str, Any]:
        """
        조립된 블록들을 묶어 최종 Slack API 전송용 Payload(DTO)로 변환합니다.
        
        주의: Slack API는 한 번에 50개를 초과하는 블록 전송을 거부하므로, 
        초과 시 설정값(max_blocks)을 기준으로 안전하게 자르고(Truncate) 경고 메시지를 덧붙입니다.
        
        Args:
            color (SlackColor): 메시지 사이드바에 표시될 테마 색상 객체 (성공/실패 여부 등)
            
        Returns:
            dict[str, Any]: 최종 직렬화 준비가 완료된 JSON 호환 딕셔너리
        """
        if len(self.blocks) > self.settings.max_blocks:
            # 설정된 최대 블록 수에서 경고 메시지용 블록 1개 몫을 빼고 자릅니다.
            self.blocks = self.blocks[:self.settings.max_blocks - 1]
            self.add_text_section("*[TRUNCATED]* 너무 많은 데이터로 인해 생략되었습니다.")

        return {
            "attachments": [{
                "color": color.value,
                "blocks": self.blocks
            }]
        }