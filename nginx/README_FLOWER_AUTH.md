# Flower 모니터링 인증 설정 가이드

Flower는 Celery 작업을 모니터링하는 웹 UI입니다. 프로덕션 환경에서는 반드시 인증을 설정해야 합니다.

## 1. htpasswd 파일 생성

```bash
# htpasswd 유틸리티 설치 (Ubuntu/Debian)
sudo apt-get install apache2-utils

# 또는 (CentOS/RHEL)
sudo yum install httpd-tools

# .htpasswd 파일 생성 (첫 번째 사용자)
sudo htpasswd -c /etc/nginx/.htpasswd admin

# 추가 사용자 생성 (첫 번째 사용자 이후)
sudo htpasswd /etc/nginx/.htpasswd username
```

## 2. Nginx 설정 수정

`nginx/nginx.conf` 파일의 Flower location 블록에서 인증 활성화:

```nginx
# Flower (Celery 모니터링)
location /flower/ {
    proxy_pass http://flower:5555/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 기본 인증 활성화
    auth_basic "Flower Monitoring";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

## 3. Docker Compose 설정

`docker-compose.yml`에서 .htpasswd 파일 마운트:

```yaml
nginx:
  image: nginx:alpine
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    - ./nginx/.htpasswd:/etc/nginx/.htpasswd  # 추가
    - ./nginx/ssl:/etc/nginx/ssl
```

## 4. 보안 권장사항

### 프로덕션 환경
- ✅ 반드시 HTTPS 사용
- ✅ .htpasswd 파일 권한: `chmod 644 /etc/nginx/.htpasswd`
- ✅ 강력한 비밀번호 사용
- ✅ IP 화이트리스트 추가 고려

### IP 제한 추가 (선택사항)

```nginx
location /flower/ {
    # IP 제한
    allow 10.0.0.0/8;      # 내부 네트워크
    allow 192.168.1.0/24;  # 로컬 네트워크
    deny all;

    # 기본 인증
    auth_basic "Flower Monitoring";
    auth_basic_user_file /etc/nginx/.htpasswd;

    proxy_pass http://flower:5555/;
    # ...
}
```

## 5. 개발 환경

개발 환경에서는 인증을 비활성화할 수 있지만, **프로덕션에서는 반드시 활성화**하세요.

```bash
# 개발 환경인지 확인
if [ "$ENVIRONMENT" = "development" ]; then
    echo "개발 환경: Flower 인증 비활성화"
else
    echo "프로덕션 환경: Flower 인증 필수!"
fi
```

## 6. Flower 접속

인증이 활성화되면 브라우저에서 접속 시 사용자명과 비밀번호를 입력해야 합니다:

- URL: `http://your-domain.com/flower/`
- 사용자명: (htpasswd로 생성한 사용자명)
- 비밀번호: (설정한 비밀번호)

## 7. 트러블슈팅

### 401 Unauthorized 오류
- .htpasswd 파일 경로 확인
- 파일 권한 확인 (`chmod 644`)
- Nginx 재시작: `docker-compose restart nginx`

### .htpasswd 파일 없음
- htpasswd 유틸리티로 파일 생성
- Docker 볼륨 마운트 확인

## 보안 체크리스트

- [ ] htpasswd 파일 생성 완료
- [ ] nginx.conf에서 auth_basic 활성화
- [ ] Docker Compose에 볼륨 마운트 추가
- [ ] HTTPS 설정 (프로덕션)
- [ ] IP 화이트리스트 설정 (선택)
- [ ] 강력한 비밀번호 사용
- [ ] 정기적인 비밀번호 변경

---

**주의**: 이 설정을 무시하면 누구나 Celery 작업 정보에 접근할 수 있어 보안 위험이 발생합니다!
