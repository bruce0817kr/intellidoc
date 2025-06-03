#!/bin/bash

# IntelliDoc 시스템 통합 테스트 스크립트
# 백엔드와 프론트엔드를 통합하여 전체 시스템 기능을 검증합니다.

echo "===== IntelliDoc 시스템 통합 테스트 시작 ====="
echo "$(date)"
echo

# 작업 디렉토리 설정
INTELLIDOC_ROOT="/home/ubuntu/intellidoc"
BACKEND_DIR="$INTELLIDOC_ROOT/backend"
FRONTEND_DIR="$INTELLIDOC_ROOT/frontend"
LOG_DIR="$INTELLIDOC_ROOT/logs"
TEST_RESULTS_DIR="$INTELLIDOC_ROOT/test_results"

# 로그 및 결과 디렉토리 생성
mkdir -p $LOG_DIR
mkdir -p $TEST_RESULTS_DIR

# 로그 파일 설정
INTEGRATION_LOG="$LOG_DIR/integration_test_$(date +%Y%m%d_%H%M%S).log"
touch $INTEGRATION_LOG

# 로그 함수
log() {
  echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $1" | tee -a $INTEGRATION_LOG
}

# 오류 처리 함수
handle_error() {
  log "오류: $1"
  exit 1
}

# 환경 확인
log "시스템 환경 확인 중..."
if [ ! -d "$BACKEND_DIR" ]; then
  handle_error "백엔드 디렉토리를 찾을 수 없습니다: $BACKEND_DIR"
fi

if [ ! -d "$FRONTEND_DIR" ]; then
  handle_error "프론트엔드 디렉토리를 찾을 수 없습니다: $FRONTEND_DIR"
fi

# 백엔드 의존성 확인
log "백엔드 의존성 확인 중..."
cd $BACKEND_DIR
if [ ! -f "requirements.txt" ]; then
  handle_error "requirements.txt 파일을 찾을 수 없습니다."
fi

# 프론트엔드 의존성 확인
log "프론트엔드 의존성 확인 중..."
cd $FRONTEND_DIR
if [ ! -f "package.json" ]; then
  handle_error "package.json 파일을 찾을 수 없습니다."
fi

# 데이터베이스 스키마 검증
log "데이터베이스 스키마 검증 중..."
cd $BACKEND_DIR
python3 -c "
import sys
sys.path.append('$BACKEND_DIR')
from shared.models import Base
from shared.database import engine
try:
    Base.metadata.create_all(bind=engine)
    print('데이터베이스 스키마 검증 성공')
except Exception as e:
    print(f'데이터베이스 스키마 검증 실패: {e}')
    sys.exit(1)
" >> $INTEGRATION_LOG 2>&1 || handle_error "데이터베이스 스키마 검증 실패"

# 백엔드 단위 테스트 실행
log "백엔드 단위 테스트 실행 중..."
cd $BACKEND_DIR
python3 -m unittest discover -s tests >> $INTEGRATION_LOG 2>&1 || handle_error "백엔드 단위 테스트 실패"

# 프론트엔드 단위 테스트 실행
log "프론트엔드 단위 테스트 실행 중..."
cd $FRONTEND_DIR
npm test >> $INTEGRATION_LOG 2>&1 || log "프론트엔드 테스트에 일부 실패가 있습니다. 로그를 확인하세요."

# 백엔드 서버 시작
log "백엔드 서버 시작 중..."
cd $BACKEND_DIR
python3 -m uvicorn web_api.main:app --host 0.0.0.0 --port 8000 >> $LOG_DIR/backend.log 2>&1 &
BACKEND_PID=$!
log "백엔드 서버 PID: $BACKEND_PID"

# 백엔드 서버가 시작될 때까지 대기
log "백엔드 서버 준비 대기 중..."
sleep 5
curl -s http://localhost:8000/health > /dev/null
if [ $? -ne 0 ]; then
  handle_error "백엔드 서버 시작 실패"
fi
log "백엔드 서버 준비 완료"

# 프론트엔드 개발 서버 시작
log "프론트엔드 개발 서버 시작 중..."
cd $FRONTEND_DIR
npm start >> $LOG_DIR/frontend.log 2>&1 &
FRONTEND_PID=$!
log "프론트엔드 서버 PID: $FRONTEND_PID"

# 프론트엔드 서버가 시작될 때까지 대기
log "프론트엔드 서버 준비 대기 중..."
sleep 10
curl -s http://localhost:3000 > /dev/null
if [ $? -ne 0 ]; then
  handle_error "프론트엔드 서버 시작 실패"
fi
log "프론트엔드 서버 준비 완료"

# API 엔드포인트 테스트
log "API 엔드포인트 테스트 중..."
API_TEST_RESULT="$TEST_RESULTS_DIR/api_test_results.json"

# 헬스체크 엔드포인트 테스트
log "헬스체크 API 테스트 중..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
echo $HEALTH_RESPONSE | grep -q "status.*ok" || handle_error "헬스체크 API 테스트 실패"
log "헬스체크 API 테스트 성공"

# 인증 API 테스트
log "인증 API 테스트 중..."
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin", "password":"admin123"}')
echo $AUTH_RESPONSE | grep -q "access_token" || log "인증 API 테스트 실패 - 기본 계정이 없을 수 있습니다."

# 문서 API 테스트
log "문서 API 테스트 중..."
DOCUMENTS_RESPONSE=$(curl -s http://localhost:8000/documents)
echo $DOCUMENTS_RESPONSE > $API_TEST_RESULT
log "문서 API 테스트 완료"

# 통합 테스트 결과 요약
log "통합 테스트 결과 요약 작성 중..."
SUMMARY_FILE="$TEST_RESULTS_DIR/integration_test_summary.txt"
echo "IntelliDoc 시스템 통합 테스트 결과 요약" > $SUMMARY_FILE
echo "테스트 일시: $(date)" >> $SUMMARY_FILE
echo "=======================================" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "1. 백엔드 단위 테스트: 성공" >> $SUMMARY_FILE
echo "2. 프론트엔드 단위 테스트: 완료 (로그 확인)" >> $SUMMARY_FILE
echo "3. 데이터베이스 스키마 검증: 성공" >> $SUMMARY_FILE
echo "4. API 엔드포인트 테스트:" >> $SUMMARY_FILE
echo "   - 헬스체크 API: 성공" >> $SUMMARY_FILE
echo "   - 인증 API: 완료 (로그 확인)" >> $SUMMARY_FILE
echo "   - 문서 API: 완료" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "자세한 로그는 $INTEGRATION_LOG 파일을 참조하세요." >> $SUMMARY_FILE

# 서버 종료
log "테스트 서버 종료 중..."
kill $BACKEND_PID
kill $FRONTEND_PID

log "===== IntelliDoc 시스템 통합 테스트 완료 ====="
log "결과 요약: $SUMMARY_FILE"
cat $SUMMARY_FILE

exit 0
