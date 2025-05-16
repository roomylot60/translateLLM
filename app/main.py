from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from typing import Optional, Dict, Any
import os
import logging
import re
from prompts import TRANSLATION_PROMPT
from datetime import datetime

# 로그 디렉토리 생성
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# 로그 파일명 설정 (날짜별)
log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # 콘솔 출력도 유지
    ]
)
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
    
    # 중복된 번역 제거 (같은 문장이 반복되는 경우)
    words = text.split()
    if len(words) > 1:
        half = len(words) // 2
        if words[:half] == words[half:]:
            text = ' '.join(words[:half])
    
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
        "system": "당신은 일본어를 한국어로 번역하는 전문가입니다. 주어진 일본어를 자연스러운 한국어로 번역해주세요. 번역 결과만 출력하고 다른 설명은 하지 마세요.",
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 4096
        }
    }

def call_ollama_api(payload: Dict[str, Any]) -> str:
    """Ollama API 호출 및 응답 처리"""
    try:
        logger.info(f"Ollama API 호출 시작: {payload['model']}")
        response = requests.post(
            f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate",
            json=payload,
            timeout=300  # 300초(5분) 타임아웃 설정
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Ollama API 응답: {result}")
        
        if not result.get("response"):
            logger.error("Ollama API 응답이 비어있습니다.")
            raise HTTPException(
                status_code=500,
                detail="번역 결과가 비어있습니다."
            )
            
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
    일본어 텍스트를 한국어로 번역합니다.

    Args:
        request (TranslationRequest): 
            - japanese_text: 번역할 일본어 텍스트
            - model: 사용할 모델 이름 (기본값: gemma2:9b)

    Returns:
        TranslationResponse:
            - korean_text: 번역된 한국어 텍스트
            - model_used: 사용된 모델 이름

    Raises:
        HTTPException: 
            - 500: 번역 서비스 오류 발생 시
    """
    try:
        logger.info(f"번역 요청 시작: {request.japanese_text}")
        
        # 프롬프트 생성
        prompt = f"다음 일본어를 한국어로 번역해주세요. 번역 결과만 출력하세요.\n\n일본어: {request.japanese_text}\n한국어:"
        logger.info(f"생성된 프롬프트: {prompt}")
        
        # Ollama API 호출을 위한 페이로드 생성
        payload = create_ollama_payload(prompt, request.model)
        
        # Ollama API 호출 및 응답 처리
        translated_text = call_ollama_api(payload)
        logger.info(f"번역 결과: {translated_text}")
        
        # 번역 결과 정제
        cleaned_text = clean_translation(translated_text)
        logger.info(f"정제된 번역 결과: {cleaned_text}")
        
        if not cleaned_text:
            logger.error("정제된 번역 결과가 비어있습니다.")
            raise HTTPException(
                status_code=500,
                detail="번역 결과가 비어있습니다."
            )
        
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
    """
    서비스의 상태를 확인합니다.

    Returns:
        Dict[str, str]: 
            - status: 서비스 상태 ("healthy" 또는 "unhealthy")
    """
    return {"status": "healthy"}
