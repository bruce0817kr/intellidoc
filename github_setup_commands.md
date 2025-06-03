# GitHub 리포지토리 연결 명령어

## 🔗 리모트 저장소 추가 및 푸시

```powershell
# 1. GitHub 리포지토리를 리모트로 추가 (YOUR_USERNAME과 REPO_NAME을 실제 값으로 변경)
git remote add origin https://github.com/YOUR_USERNAME/intellidoc.git

# 2. 리모트 연결 확인
git remote -v

# 3. 메인 브랜치를 GitHub에 푸시 (첫 번째 푸시)
git push -u origin master

# 또는 main 브랜치로 푸시하려면:
# git branch -M main
# git push -u origin main
```

## 🔍 현재 상태 확인

```powershell
# 현재 브랜치 확인
git branch

# 커밋 로그 확인
git log --oneline -5

# 리모트 저장소 확인
git remote -v
```

## 📝 추가 작업 (선택사항)

### 브랜치 이름을 main으로 변경하려면:
```powershell
git branch -M main
git push -u origin main
```

### GitHub Actions 워크플로우 추가:
```powershell
# .github/workflows 디렉토리가 이미 있는지 확인
ls .github/workflows/
```

## 🚀 성공 확인

푸시가 완료되면 GitHub 리포지토리 페이지에서 다음을 확인할 수 있습니다:
- ✅ 모든 프로젝트 파일들
- ✅ README.md가 메인 페이지에 표시
- ✅ 커밋 히스토리
- ✅ 브랜치 정보

## 🔧 문제 해결

### 인증 오류가 발생하는 경우:
1. Personal Access Token 생성: GitHub Settings → Developer settings → Personal access tokens
2. Token을 사용하여 인증: `git push` 시 username에는 GitHub username, password에는 token 입력

### 브랜치 이름 충돌:
- GitHub 기본 브랜치가 main이고 로컬이 master인 경우, 위의 브랜치 변경 명령어 사용
