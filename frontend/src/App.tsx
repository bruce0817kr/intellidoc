import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout, Menu, Typography, Button, Dropdown } from 'antd';
import { 
  FileTextOutlined, 
  UploadOutlined, 
  UserOutlined, 
  LogoutOutlined,
  DashboardOutlined
} from '@ant-design/icons';
import { useAuth, AuthProvider } from './store/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import DocumentDetailPage from './pages/DocumentDetailPage';
import UploadPage from './pages/UploadPage';
import ProfilePage from './pages/ProfilePage';
import './App.css';

const { Header, Content, Footer, Sider } = Layout;
const { Title } = Typography;

// 인증 필요한 라우트 래퍼 컴포넌트
const PrivateRoute: React.FC<{ element: React.ReactElement }> = ({ element }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div>로딩 중...</div>;
  }
  
  return isAuthenticated ? element : <Navigate to="/login" />;
};

// 메인 앱 컴포넌트
const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

// 앱 내용 컴포넌트
const AppContent: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth();
  
  // 사용자 메뉴 아이템
  const userMenuItems = [
    {
      key: 'profile',
      label: '프로필',
      icon: <UserOutlined />,
    },
    {
      key: 'logout',
      label: '로그아웃',
      icon: <LogoutOutlined />,
      danger: true,
    },
  ];
  
  // 사용자 메뉴 클릭 핸들러
  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout();
    }
  };
  
  // 로그인 페이지 렌더링
  if (!isAuthenticated) {
    return (
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </Router>
    );
  }
  
  // 인증된 사용자 UI 렌더링
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider
          breakpoint="lg"
          collapsedWidth="0"
        >
          <div className="logo">
            <Title level={4} style={{ color: 'white', margin: '16px' }}>IntelliDoc</Title>
          </div>
          <Menu
            theme="dark"
            mode="inline"
            defaultSelectedKeys={['dashboard']}
            items={[
              {
                key: 'dashboard',
                icon: <DashboardOutlined />,
                label: '대시보드',
                path: '/',
              },
              {
                key: 'upload',
                icon: <UploadOutlined />,
                label: '문서 업로드',
                path: '/upload',
              },
              {
                key: 'documents',
                icon: <FileTextOutlined />,
                label: '문서 관리',
                path: '/documents',
              },
            ].map(item => ({
              key: item.key,
              icon: item.icon,
              label: <a href={item.path}>{item.label}</a>,
            }))}
          />
        </Sider>
        <Layout>
          <Header style={{ background: '#fff', padding: '0 16px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }}
              placement="bottomRight"
            >
              <Button icon={<UserOutlined />}>
                {user?.username || '사용자'}
              </Button>
            </Dropdown>
          </Header>
          <Content style={{ margin: '24px 16px 0' }}>
            <div style={{ padding: 24, minHeight: 360, background: '#fff' }}>
              <Routes>
                <Route path="/" element={<PrivateRoute element={<Dashboard />} />} />
                <Route path="/upload" element={<PrivateRoute element={<UploadPage />} />} />
                <Route path="/documents" element={<PrivateRoute element={<Dashboard />} />} />
                <Route path="/documents/:id" element={<PrivateRoute element={<DocumentDetailPage />} />} />
                <Route path="/profile" element={<PrivateRoute element={<ProfilePage />} />} />
                <Route path="*" element={<Navigate to="/" />} />
              </Routes>
            </div>
          </Content>
          <Footer style={{ textAlign: 'center' }}>
            IntelliDoc ©{new Date().getFullYear()} - 지능형 문서 처리 시스템
          </Footer>
        </Layout>
      </Layout>
    </Router>
  );
};

export default App;
