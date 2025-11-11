import { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import apiClient from '../utils/apiClient';

// 인증 상태 타입 정의
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
}

// 사용자 정보 타입 정의
interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  department?: string;
  roles: string[];
  permissions: string[];
}

// 인증 컨텍스트 타입 정의
interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
}

// 기본값으로 사용할 인증 컨텍스트 생성
const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
  refreshToken: async () => false,
});

// 인증 컨텍스트 제공자 Props 타입 정의
interface AuthProviderProps {
  children: ReactNode;
}

// 인증 컨텍스트 제공자 컴포넌트
export const AuthProvider = ({ children }: AuthProviderProps) => {
  // 인증 상태 관리
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    loading: true,
  });

  // 컴포넌트 마운트 시 쿠키에서 인증 상태 확인
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // 쿠키에 토큰이 있으면 자동으로 전송됨
        // /auth/me API를 호출하여 인증 상태 확인
        const response = await apiClient.get('/auth/me');
        setAuthState({
          isAuthenticated: true,
          user: response.data,
          loading: false,
        });
      } catch (error) {
        // 쿠키가 없거나 유효하지 않은 경우
        // 백엔드에서 자동으로 쿠키 삭제 처리
        setAuthState({
          isAuthenticated: false,
          user: null,
          loading: false,
        });
      }
    };

    checkAuth();
  }, []);

  // 로그인 함수
  const login = async (username: string, password: string) => {
    try {
      // OAuth2PasswordRequestForm 형식으로 전송 (백엔드 요구사항)
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await apiClient.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      // 토큰은 HttpOnly 쿠키로 자동 저장됨
      // 응답에는 사용자 정보만 포함
      const { user } = response.data;

      // 인증 상태 업데이트
      setAuthState({
        isAuthenticated: true,
        user: user,
        loading: false,
      });
    } catch (error) {
      throw error;
    }
  };

  // 로그아웃 함수
  const logout = async () => {
    try {
      // 백엔드 로그아웃 API 호출 (쿠키 삭제)
      await apiClient.post('/auth/logout');
    } catch (error) {
      // 로그아웃 실패해도 프론트엔드 상태는 초기화
      console.error('로그아웃 중 오류 발생:', error);
    } finally {
      // 인증 상태 초기화
      setAuthState({
        isAuthenticated: false,
        user: null,
        loading: false,
      });
    }
  };

  // 토큰 갱신 함수
  const refreshToken = async (): Promise<boolean> => {
    try {
      // 쿠키에서 자동으로 refresh_token이 전송됨
      await apiClient.post('/auth/refresh');

      // 새 토큰이 쿠키에 자동으로 저장됨
      return true;
    } catch (error) {
      // 갱신 실패 시 로그아웃
      await logout();
      return false;
    }
  };

  // 컨텍스트 값 제공
  const contextValue: AuthContextType = {
    ...authState,
    login,
    logout,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// 인증 컨텍스트 사용을 위한 커스텀 훅
export const useAuth = () => useContext(AuthContext);
