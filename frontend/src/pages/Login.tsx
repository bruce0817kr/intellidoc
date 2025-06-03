import React, { useState } from 'react';
import { Form, Input, Button, Card, Alert, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuth } from '../store/AuthContext';

const { Title } = Typography;

/**
 * 로그인 페이지 컴포넌트
 */
const Login: React.FC = () => {
  const { login } = useAuth();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 로그인 폼 제출 핸들러
  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    setError(null);
    
    try {
      await login(values.username, values.password);
      // 로그인 성공 시 리디렉션은 AuthContext에서 처리
    } catch (err: any) {
      setError(err.response?.data?.detail || '로그인에 실패했습니다. 사용자 이름과 비밀번호를 확인해주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: '#f0f2f5'
    }}>
      <Card style={{ width: 400, boxShadow: '0 4px 8px rgba(0,0,0,0.1)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2}>IntelliDoc</Title>
          <Title level={4} style={{ marginTop: 0 }}>지능형 문서 처리 시스템</Title>
        </div>
        
        {error && (
          <Alert
            message="로그인 오류"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 24 }}
          />
        )}
        
        <Form
          name="login"
          initialValues={{ remember: true }}
          onFinish={handleSubmit}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '사용자 이름을 입력해주세요!' }]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="사용자 이름" 
            />
          </Form.Item>
          
          <Form.Item
            name="password"
            rules={[{ required: true, message: '비밀번호를 입력해주세요!' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="비밀번호"
            />
          </Form.Item>
          
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              style={{ width: '100%' }}
            >
              로그인
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
