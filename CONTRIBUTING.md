# 기여 가이드 (Contributing Guide)

IntelliDoc 프로젝트에 기여해 주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법을 안내합니다.

## 📋 기여 방법

### 1. 이슈 리포팅
- 버그 발견 시 [Issues](https://github.com/YOUR_USERNAME/intellidoc/issues)에서 새 이슈를 생성해 주세요
- 명확한 제목과 상세한 설명을 포함해 주세요
- 재현 단계, 예상 결과, 실제 결과를 포함해 주세요

### 2. 기능 제안
- 새로운 기능 제안은 [Issues](https://github.com/YOUR_USERNAME/intellidoc/issues)에 Feature Request 라벨로 등록해 주세요
- 기능의 필요성과 구체적인 구현 아이디어를 설명해 주세요

### 3. 코드 기여

#### Fork & Clone
```bash
# 1. GitHub에서 프로젝트를 Fork
# 2. 로컬에 클론
git clone https://github.com/YOUR_USERNAME/intellidoc.git
cd intellidoc

# 3. upstream 저장소 추가
git remote add upstream https://github.com/ORIGINAL_OWNER/intellidoc.git
```

#### 개발 환경 설정
```bash
# 가상환경 설정
.\setup_venv.ps1  # Windows
./setup_venv.sh   # Linux/Mac

# 의존성 설치
pip install -r requirements-dev.txt
cd frontend && npm install
```

#### 브랜치 생성
```bash
# 새 기능 개발
git checkout -b feature/your-feature-name

# 버그 수정
git checkout -b bugfix/issue-number-description
```

#### 개발 및 테스트
```bash
# 백엔드 테스트 실행
cd backend
pytest

# 프론트엔드 테스트 실행
cd frontend
npm test

# 통합 테스트
.\test_integration.ps1  # Windows
./integration_test.sh   # Linux/Mac
```

#### 커밋 규칙
```bash
# 커밋 메시지 형식
<type>(<scope>): <description>

# 예시:
feat(ocr): add Mistral OCR engine support
fix(auth): resolve JWT token expiration issue
docs(readme): update installation instructions
test(backend): add unit tests for export service
```

**커밋 타입:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드/설정 파일 수정

#### Pull Request 제출
1. 변경사항을 upstream과 동기화
```bash
git fetch upstream
git rebase upstream/main
```

2. 변경사항 푸시
```bash
git push origin your-branch-name
```

3. GitHub에서 Pull Request 생성
4. PR 템플릿에 따라 내용 작성

## 📝 코딩 스타일

### Python (Backend)
- **PEP 8** 스타일 가이드 준수
- **Black** 포맷터 사용
- **Type hints** 사용 권장
- **Docstring** 작성 (Google 스타일)

```python
def process_document(file_path: str, options: ProcessingOptions) -> ProcessedDocument:
    """문서를 처리하여 텍스트와 메타데이터를 추출합니다.
    
    Args:
        file_path: 처리할 문서 파일 경로
        options: 처리 옵션 설정
        
    Returns:
        ProcessedDocument: 처리된 문서 객체
        
    Raises:
        DocumentProcessingError: 문서 처리 중 오류 발생
    """
```

### TypeScript (Frontend)
- **ESLint** 및 **Prettier** 설정 준수
- **함수형 컴포넌트** 사용
- **TypeScript strict mode** 사용
- **Custom hooks** 적극 활용

```typescript
interface DocumentUploadProps {
  onUpload: (file: File) => Promise<void>;
  acceptedTypes: string[];
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ 
  onUpload, 
  acceptedTypes 
}) => {
  // 컴포넌트 구현
};
```

## 🧪 테스트 가이드

### 백엔드 테스트
```bash
# 전체 테스트 실행
pytest

# 특정 모듈 테스트
pytest backend/tests/test_ocr_service.py

# 커버리지 포함
pytest --cov=backend --cov-report=html
```

### 프론트엔드 테스트
```bash
# 단위 테스트
npm test

# E2E 테스트
npm run test:e2e

# 커버리지 포함
npm run test:coverage
```

## 📚 문서화

### API 문서
- FastAPI의 자동 문서화 활용 (`/docs` 엔드포인트)
- 각 API 엔드포인트에 명확한 설명과 예시 포함

### 코드 문서
- 복잡한 로직에는 주석 추가
- README.md 업데이트 (새 기능 추가 시)
- 변경 로그 업데이트 (CHANGELOG.md)

## 🔍 리뷰 프로세스

### Pull Request 체크리스트
- [ ] 코드가 스타일 가이드를 준수하는가?
- [ ] 새로운 기능에 대한 테스트가 추가되었는가?
- [ ] 모든 테스트가 통과하는가?
- [ ] 문서가 업데이트되었는가?
- [ ] 커밋 메시지가 규칙을 준수하는가?

### 리뷰어 가이드
- 코드 품질과 성능 검토
- 보안 관련 사항 확인
- 사용자 경험 고려
- 건설적인 피드백 제공

## 🎯 우선순위 영역

현재 프로젝트에서 기여가 필요한 영역:

1. **OCR 엔진 추가** - 새로운 OCR 엔진 통합
2. **LLM 모델 지원** - 추가 LLM 모델 지원
3. **UI/UX 개선** - 사용자 인터페이스 개선
4. **성능 최적화** - 처리 속도 및 메모리 사용량 최적화
5. **테스트 커버리지** - 테스트 케이스 추가
6. **국제화** - 다국어 지원
7. **모바일 지원** - 반응형 디자인 개선

## 💬 소통

- **GitHub Issues**: 버그 리포트, 기능 제안
- **GitHub Discussions**: 일반적인 질문, 아이디어 토론
- **Email**: [your-email@example.com] (긴급한 보안 문제)

## 📄 라이선스

이 프로젝트에 기여함으로써, 귀하의 기여가 MIT 라이선스 하에 배포될 것에 동의하는 것으로 간주됩니다.

---

**다시 한 번 감사드립니다! 🙏**

함께 IntelliDoc을 더 나은 프로젝트로 만들어 나가요!
