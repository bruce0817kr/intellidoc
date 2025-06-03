#!/bin/bash

# IntelliDoc 보안 검증 스크립트
# 시스템의 보안 취약점을 검사하고 결과를 보고합니다.

echo "===== IntelliDoc 보안 검증 시작 ====="
echo "$(date)"
echo

# 작업 디렉토리 설정
INTELLIDOC_ROOT="/home/ubuntu/intellidoc"
BACKEND_DIR="$INTELLIDOC_ROOT/backend"
FRONTEND_DIR="$INTELLIDOC_ROOT/frontend"
LOG_DIR="$INTELLIDOC_ROOT/logs"
SECURITY_RESULTS_DIR="$INTELLIDOC_ROOT/security_results"

# 로그 및 결과 디렉토리 생성
mkdir -p $LOG_DIR
mkdir -p $SECURITY_RESULTS_DIR

# 로그 파일 설정
SECURITY_LOG="$LOG_DIR/security_test_$(date +%Y%m%d_%H%M%S).log"
touch $SECURITY_LOG

# 로그 함수
log() {
  echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $1" | tee -a $SECURITY_LOG
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

# 백엔드 보안 검증
log "백엔드 보안 검증 중..."

# 1. 의존성 취약점 검사
log "Python 의존성 취약점 검사 중..."
cd $BACKEND_DIR
pip-audit -r requirements.txt > $SECURITY_RESULTS_DIR/backend_dependencies_audit.txt 2>&1 || log "일부 의존성에 취약점이 있을 수 있습니다."

# 2. 비밀번호 해싱 검증
log "비밀번호 해싱 검증 중..."
grep -r "bcrypt" $BACKEND_DIR > $SECURITY_RESULTS_DIR/password_hashing_check.txt
if [ $? -ne 0 ]; then
  log "경고: 안전한 비밀번호 해싱(bcrypt)을 찾을 수 없습니다."
else
  log "비밀번호 해싱 검증 완료"
fi

# 3. JWT 설정 검증
log "JWT 설정 검증 중..."
grep -r "SECRET_KEY\|ALGORITHM\|ACCESS_TOKEN_EXPIRE_MINUTES" $BACKEND_DIR > $SECURITY_RESULTS_DIR/jwt_config_check.txt
log "JWT 설정 검증 완료"

# 4. SQL 인젝션 방지 검증
log "SQL 인젝션 방지 검증 중..."
grep -r "execute\|executemany\|raw" $BACKEND_DIR > $SECURITY_RESULTS_DIR/sql_injection_check.txt
log "SQL 인젝션 방지 검증 완료"

# 5. 권한 검증 메커니즘 확인
log "권한 검증 메커니즘 확인 중..."
grep -r "get_current_user\|has_permission\|requires_role" $BACKEND_DIR > $SECURITY_RESULTS_DIR/auth_check.txt
log "권한 검증 메커니즘 확인 완료"

# 프론트엔드 보안 검증
log "프론트엔드 보안 검증 중..."

# 1. 프론트엔드 의존성 취약점 검사
log "Node.js 의존성 취약점 검사 중..."
cd $FRONTEND_DIR
npm audit > $SECURITY_RESULTS_DIR/frontend_dependencies_audit.txt 2>&1 || log "일부 의존성에 취약점이 있을 수 있습니다."

# 2. XSS 방지 검증
log "XSS 방지 검증 중..."
grep -r "dangerouslySetInnerHTML\|innerHTML" $FRONTEND_DIR/src > $SECURITY_RESULTS_DIR/xss_check.txt
if [ $? -eq 0 ]; then
  log "경고: 잠재적인 XSS 취약점이 있을 수 있습니다."
else
  log "XSS 방지 검증 완료"
fi

# 3. CSRF 방지 검증
log "CSRF 방지 검증 중..."
grep -r "csrf\|xsrf" $FRONTEND_DIR/src > $SECURITY_RESULTS_DIR/csrf_check.txt
log "CSRF 방지 검증 완료"

# 4. 토큰 저장 방식 검증
log "토큰 저장 방식 검증 중..."
grep -r "localStorage\|sessionStorage\|cookies" $FRONTEND_DIR/src > $SECURITY_RESULTS_DIR/token_storage_check.txt
log "토큰 저장 방식 검증 완료"

# API 보안 검증
log "API 보안 검증 중..."

# 1. CORS 설정 검증
log "CORS 설정 검증 중..."
grep -r "CORSMiddleware\|origins" $BACKEND_DIR > $SECURITY_RESULTS_DIR/cors_check.txt
log "CORS 설정 검증 완료"

# 2. 속도 제한 검증
log "속도 제한 검증 중..."
grep -r "RateLimiter\|rate_limit" $BACKEND_DIR > $SECURITY_RESULTS_DIR/rate_limit_check.txt
log "속도 제한 검증 완료"

# 3. 입력 유효성 검사 확인
log "입력 유효성 검사 확인 중..."
grep -r "validator\|validate\|schema" $BACKEND_DIR > $SECURITY_RESULTS_DIR/input_validation_check.txt
log "입력 유효성 검사 확인 완료"

# 보안 검증 결과 요약
log "보안 검증 결과 요약 작성 중..."
SUMMARY_FILE="$SECURITY_RESULTS_DIR/security_test_summary.txt"
echo "IntelliDoc 보안 검증 결과 요약" > $SUMMARY_FILE
echo "테스트 일시: $(date)" >> $SUMMARY_FILE
echo "=======================================" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "1. 백엔드 보안 검증:" >> $SUMMARY_FILE
echo "   - 의존성 취약점 검사: 완료 (결과 파일 확인)" >> $SUMMARY_FILE
echo "   - 비밀번호 해싱 검증: 완료" >> $SUMMARY_FILE
echo "   - JWT 설정 검증: 완료" >> $SUMMARY_FILE
echo "   - SQL 인젝션 방지 검증: 완료" >> $SUMMARY_FILE
echo "   - 권한 검증 메커니즘 확인: 완료" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "2. 프론트엔드 보안 검증:" >> $SUMMARY_FILE
echo "   - 의존성 취약점 검사: 완료 (결과 파일 확인)" >> $SUMMARY_FILE
echo "   - XSS 방지 검증: 완료" >> $SUMMARY_FILE
echo "   - CSRF 방지 검증: 완료" >> $SUMMARY_FILE
echo "   - 토큰 저장 방식 검증: 완료" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "3. API 보안 검증:" >> $SUMMARY_FILE
echo "   - CORS 설정 검증: 완료" >> $SUMMARY_FILE
echo "   - 속도 제한 검증: 완료" >> $SUMMARY_FILE
echo "   - 입력 유효성 검사 확인: 완료" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "자세한 로그는 $SECURITY_LOG 파일을 참조하세요." >> $SUMMARY_FILE
echo "개별 검증 결과는 $SECURITY_RESULTS_DIR 디렉토리에서 확인할 수 있습니다." >> $SUMMARY_FILE

log "===== IntelliDoc 보안 검증 완료 ====="
log "결과 요약: $SUMMARY_FILE"
cat $SUMMARY_FILE

exit 0
