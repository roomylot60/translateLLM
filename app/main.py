from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from typing import Optional, Dict, Any
import os
import logging
import re
from prompts import TRANSLATION_PROMPT

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수 설정
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
DEFAULT_MODEL = "gemma2:9b"

app = FastAPI(
    title="Japanese to Korean Translator",
    description="Translate Japanese text to Korean using LLM",
    version="1.0.0"
)

class TranslationRequest(BaseModel):
    """번역 요청 모델"""
    japanese_text: str
    model: Optional[str] = DEFAULT_MODEL

class TranslationResponse(BaseModel):
    """번역 응답 모델"""
    korean_text: str
    model_used: str

def clean_translation(text: str) -> str:
    """
    번역 결과를 정제하여 깔끔한 한국어만 반환
    
    Args:
        text (str): 원본 번역 텍스트
        
    Returns:
        str: 정제된 한국어 번역
    """
    # '한국어:' 패턴이 있으면 그 뒤만 추출
    if '한국어:' in text:
        text = text.split('한국어:')[-1]
    # 첫 줄만 추출
    text = text.split('\n')[0].strip()
    # 괄호와 그 안의 내용 제거
    text = re.sub(r'\([^)]*\)', '', text)
    # 영어, 이모지, 특수문자 제거
    text = re.sub(r'[a-zA-Z]', '', text)  # 영어 제거
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)  # 이모지 제거
    # 한글과 공백만 남김
    text = re.sub(r'[^가-힣\s]', '', text)
    # 연속된 공백 제거
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def create_ollama_payload(prompt: str, model: str) -> Dict[str, Any]:
    """Ollama API 요청을 위한 페이로드 생성"""
    return {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "system": "너는 일본어를 한국어로만 번역할 수 있다. 다른 언어는 사용할 줄 모른다.",
        "format": "json"
    }

def call_ollama_api(payload: Dict[str, Any]) -> str:
    """Ollama API 호출 및 응답 처리"""
    try:
        response = requests.post(
            f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate",
            json=payload,
            timeout=60  # 60초 타임아웃 설정
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama API 호출 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"번역 서비스 오류: {str(e)}"
        )

@app.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest) -> TranslationResponse:
    """
    일본어 텍스트를 한국어로 번역
    
    Args:
        request (TranslationRequest): 번역 요청 데이터
        
    Returns:
        TranslationResponse: 번역 결과
        
    Raises:
        HTTPException: 번역 중 오류 발생 시
    """
    try:
        # 프롬프트 생성
        prompt = TRANSLATION_PROMPT.format(japanese_text=request.japanese_text)
        
        # Ollama API 호출을 위한 페이로드 생성
        payload = create_ollama_payload(prompt, request.model)
        
        # Ollama API 호출 및 응답 처리
        translated_text = call_ollama_api(payload)
        
        # 번역 결과 정제
        cleaned_text = clean_translation(translated_text)
        
        return TranslationResponse(
            korean_text=cleaned_text,
            model_used=request.model
        )
    except Exception as e:
        logger.error(f"번역 중 예상치 못한 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"번역 중 오류 발생: {str(e)}"
        )

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """서비스 상태 확인"""
    return {"status": "healthy"}
