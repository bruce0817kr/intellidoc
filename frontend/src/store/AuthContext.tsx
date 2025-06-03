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
  logout: () => void;
  refreshToken: () => Promise<boolean>;
}

// 기본값으로 사용할 인증 컨텍스트 생성
const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
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

  // 컴포넌트 마운트 시 로컬 스토리지에서 토큰 확인
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      
      if (token) {
        try {
          // 사용자 정보 조회
          const response = await apiClient.get('/auth/me');
          setAuthState({
            isAuthenticated: true,
            user: response.data,
            loading: false,
          });
        } catch (error) {
          // 토큰이 유효하지 않은 경우
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          setAuthState({
            isAuthenticated: false,
            user: null,
            loading: false,
          });
        }
      } else {
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
      const response = await apiClient.post('/auth/login', {
        username,
        password,
      });

      const { access_token, refresh_token, ...userData } = response.data;
      
      // 토큰 저장
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      
      // 인증 상태 업데이트
      setAuthState({
        isAuthenticated: true,
        user: userData,
        loading: false,
      });
    } catch (error) {
      throw error;
    }
  };

  // 로그아웃 함수
  const logout = () => {
    // 토큰 제거
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    
    // 인증 상태 업데이트
    setAuthState({
      isAuthenticated: false,
      user: null,
      loading: false,
    });
  };

  // 토큰 갱신 함수
  const refreshToken = async (): Promise<boolean> => {
    const refresh = localStorage.getItem('refresh_token');
    
    if (!refresh) {
      return false;
    }
    
    try {
      const response = await apiClient.post('/auth/refresh', {
        refresh_token: refresh,
      });
      
      const { access_token, refresh_token } = response.data;
      
      // 새 토큰 저장
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      
      return true;
    } catch (error) {
      // 갱신 실패 시 로그아웃
      logout();
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
