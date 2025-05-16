"""
번역 프롬프트 정의 모듈
"""

# 일본어-한국어 번역 프롬프트
TRANSLATION_PROMPT = """
Translate this Japanese text to Korean. Only output the Korean translation, nothing else.

Japanese: {japanese_text}
Korean:
""" 