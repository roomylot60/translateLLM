# Japanese to Korean Translator (Ollama + FastAPI)

## 프로젝트 개요
- 일본어 텍스트를 한국어로 번역하는 API 서비스
- FastAPI 기반 REST API
- Ollama LLM(gemma2:9b) + GPU 가속
- Docker Compose로 손쉽게 배포 및 개발환경 구성

---

## 오늘의 작업 내역 및 문제 해결 과정

### 1. 기본 API 및 Docker 환경 구축
- FastAPI로 `/translate` 번역 엔드포인트 구현
- Ollama LLM을 Docker 컨테이너로 구동, GPU 사용 설정
- 번역 요청/응답 모델 정의 및 로깅 설정

### 2. GPU 연동 및 모델 상태 확인
- `docker-compose.yml`에서 `runtime: nvidia` 및 GPU capabilities 설정
- `nvidia-smi`로 컨테이너 내 GPU 인식 확인
- Ollama 컨테이너에서 모델 정상 설치 및 GPU 사용 확인

### 3. 주요 오류 및 해결 과정

#### (1) 포트 충돌 오류
- **현상:** `Bind for 0.0.0.0:8000 failed: port is already allocated`
- **원인:** 8000번 포트를 이미 다른 프로세스가 사용 중
- **해결:** 기존 프로세스 종료 후 재시작

#### (2) Ollama API 타임아웃/빈 응답
- **현상:** 번역 요청 시 500 에러, 빈 응답 또는 타임아웃
- **원인:**
  - Ollama 모델이 완전히 로드되지 않았거나, 프롬프트에 번역할 텍스트가 누락됨
  - 프롬프트가 LLM에 적합하지 않아 응답이 비어있음
- **해결:**
  - Ollama 모델 상태 및 GPU 상태를 명확히 확인
  - 프롬프트를 `Japanese: ... Korean:` 형태로 명확하게 수정
  - API에서 프롬프트 생성 로직을 직접 문자열로 작성하여 실제 번역할 텍스트가 포함되도록 개선

#### (3) 번역 결과 중복/불필요한 텍스트
- **현상:** 번역 결과가 두 번 반복되거나, 불필요한 설명이 포함됨
- **원인:** LLM의 출력 패턴 및 후처리 미흡
- **해결:**
  - `clean_translation` 함수에서 중복 문장 제거 및 한글만 남기는 정제 로직 추가

#### (4) 코드 변경 시 컨테이너 자동 반영
- **현상:** 코드 변경 시마다 컨테이너를 재시작해야 하는 불편함
- **해결:**
  - `docker-compose.yml`에 볼륨 마운트 및 Uvicorn `--reload` 옵션 추가로 코드 변경 시 자동 반영

---

## 사용법

### 1. 빌드 및 실행
```bash
docker-compose up --build -d
```

### 2. 번역 API 사용 예시
```bash
curl -X POST "http://localhost:8000/translate" \
     -H "Content-Type: application/json" \
     -d '{"japanese_text": "こんにちは、元気ですか？"}'
```

### 3. API 문서
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 개선 및 참고 사항
- Ollama 모델(gemma2:9b)은 일본어-한국어 번역이 가능하지만, 프롬프트 설계와 후처리가 중요함
- GPU가 정상적으로 인식되지 않으면 NVIDIA 드라이버 및 Docker 설정을 재확인할 것
- 번역 품질 개선을 위해 프롬프트와 후처리 로직을 지속적으로 개선할 것

---

## 주요 명령어 정리
- 모델 목록 확인: `docker exec -it ollama ollama list`
- GPU 상태 확인: `docker exec -it ollama nvidia-smi`
- Ollama 로그 확인: `docker logs ollama --tail 100`
- API 서버 로그 확인: `docker logs translator-api --tail 100`

---
