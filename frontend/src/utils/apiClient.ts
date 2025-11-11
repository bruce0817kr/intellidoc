// API 클라이언트 설정
import axios from 'axios';

// 기본 API 클라이언트 인스턴스 생성
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30초 타임아웃
  withCredentials: true, // 쿠키 전송 허용 (HttpOnly 쿠키 사용)
});

// 요청 인터셉터 설정
apiClient.interceptors.request.use(
  (config) => {
    // HttpOnly 쿠키가 자동으로 전송되므로 별도 처리 불필요
    // Authorization 헤더는 하위 호환성을 위해 백엔드에서 지원하지만
    // 기본적으로 쿠키를 사용합니다.
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 설정
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // 401 에러(인증 실패)이고 재시도하지 않은 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // 리프레시 토큰으로 새 액세스 토큰 요청
        // 쿠키에서 자동으로 refresh_token이 전송됩니다
        await axios.post(
          `${apiClient.defaults.baseURL}/auth/refresh`,
          {},
          { withCredentials: true }
        );

        // 새 토큰이 쿠키에 자동으로 저장되므로 별도 처리 불필요
        // 원래 요청 재시도
        return apiClient(originalRequest);
      } catch (refreshError) {
        // 리프레시 토큰도 만료된 경우
        // 쿠키는 백엔드에서 자동으로 삭제되지만
        // 사용자를 로그인 페이지로 리디렉션합니다

        // React Router 사용 시 navigate 사용 권장
        // 하지만 인터셉터에서는 window.location 사용
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
