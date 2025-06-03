# Python 3.11 슬림 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    # 컴파일러 및 빌드 도구
    gcc \
    g++ \
    make \
    # 이미지 처리 라이브러리
    libpoppler-cpp-dev \
    poppler-utils \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    # 이미지 처리 라이브러리
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    # OpenCV 의존성
    libopencv-dev \
    python3-opencv \
    # 기타 유틸리티
    curl \
    wget \
    git \
    # 정리
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사
COPY requirements.txt .
COPY requirements-dev.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 개발 환경용 패키지 설치 (선택적)
ARG INSTALL_DEV_DEPS=false
RUN if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
    pip install --no-cache-dir -r requirements-dev.txt; \
    fi

# 애플리케이션 코드 복사
COPY . .

# 업로드 디렉토리 생성
RUN mkdir -p /app/uploads /app/logs

# 포트 노출
EXPOSE 8000

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
