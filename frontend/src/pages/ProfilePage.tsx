import React, { useState, useEffect } from 'react';
import { Card, Avatar, Typography, Form, Input, Button, Tabs, Alert, message } from 'antd';
import { UserOutlined, MailOutlined, LockOutlined, TeamOutlined, BankOutlined } from '@ant-design/icons';
import { useAuth } from '../store/AuthContext';
import apiClient from '../utils/apiClient';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

/**
 * 사용자 프로필 페이지 컴포넌트
 */
const ProfilePage: React.FC = () => {
  const { user, refreshToken } = useAuth();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 프로필 업데이트 핸들러
  const handleProfileUpdate = async (values: any) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await apiClient.put('/auth/profile', values);
      setSuccess('프로필이 성공적으로 업데이트되었습니다.');
      // 사용자 정보 갱신
      await refreshToken();
    } catch (err: any) {
      setError(err.response?.data?.detail || '프로필 업데이트 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 비밀번호 변경 핸들러
  const handlePasswordChange = async (values: any) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await apiClient.put('/auth/password', {
        current_password: values.currentPassword,
        new_password: values.newPassword,
      });
      setSuccess('비밀번호가 성공적으로 변경되었습니다.');
      // 폼 초기화
      values.currentPassword = '';
      values.newPassword = '';
      values.confirmPassword = '';
    } catch (err: any) {
      setError(err.response?.data?.detail || '비밀번호 변경 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return <Alert message="사용자 정보를 불러올 수 없습니다." type="error" showIcon />;
  }

  return (
    <div>
      <Title level={2}>내 프로필</Title>
      
      <Card className="mb-4">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Avatar size={64} icon={<UserOutlined />} />
          <div style={{ marginLeft: 16 }}>
            <Title level={4}>{user.full_name || user.username}</Title>
            <Text type="secondary">{user.email}</Text>
            <div>
              {user.roles?.map(role => (
                <Text key={role} type="secondary" style={{ marginRight: 8 }}>
                  {role}
                </Text>
              ))}
            </div>
          </div>
        </div>
      </Card>
      
      <Tabs defaultActiveKey="profile">
        <TabPane tab="프로필 정보" key="profile">
          <Card>
            {error && (
              <Alert
                message="오류"
                description={error}
                type="error"
                showIcon
                className="mb-4"
              />
            )}
            
            {success && (
              <Alert
                message="성공"
                description={success}
                type="success"
                showIcon
                className="mb-4"
              />
            )}
            
            <Form
              layout="vertical"
              initialValues={{
                username: user.username,
                email: user.email,
                full_name: user.full_name || '',
                department: user.department || '',
              }}
              onFinish={handleProfileUpdate}
            >
              <Form.Item
                label="사용자 이름"
                name="username"
                rules={[{ required: true, message: '사용자 이름을 입력해주세요!' }]}
              >
                <Input prefix={<UserOutlined />} disabled />
              </Form.Item>
              
              <Form.Item
                label="이메일"
                name="email"
                rules={[
                  { required: true, message: '이메일을 입력해주세요!' },
                  { type: 'email', message: '유효한 이메일 주소를 입력해주세요!' },
                ]}
              >
                <Input prefix={<MailOutlined />} />
              </Form.Item>
              
              <Form.Item
                label="이름"
                name="full_name"
              >
                <Input prefix={<UserOutlined />} />
              </Form.Item>
              
              <Form.Item
                label="부서"
                name="department"
              >
                <Input prefix={<BankOutlined />} />
              </Form.Item>
              
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                >
                  프로필 업데이트
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
        
        <TabPane tab="비밀번호 변경" key="password">
          <Card>
            {error && (
              <Alert
                message="오류"
                description={error}
                type="error"
                showIcon
                className="mb-4"
              />
            )}
            
            {success && (
              <Alert
                message="성공"
                description={success}
                type="success"
                showIcon
                className="mb-4"
              />
            )}
            
            <Form
              layout="vertical"
              onFinish={handlePasswordChange}
            >
              <Form.Item
                label="현재 비밀번호"
                name="currentPassword"
                rules={[{ required: true, message: '현재 비밀번호를 입력해주세요!' }]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>
              
              <Form.Item
                label="새 비밀번호"
                name="newPassword"
                rules={[
                  { required: true, message: '새 비밀번호를 입력해주세요!' },
                  { min: 8, message: '비밀번호는 최소 8자 이상이어야 합니다!' },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>
              
              <Form.Item
                label="새 비밀번호 확인"
                name="confirmPassword"
                dependencies={['newPassword']}
                rules={[
                  { required: true, message: '비밀번호 확인을 입력해주세요!' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('newPassword') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('비밀번호가 일치하지 않습니다!'));
                    },
                  }),
                ]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>
              
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                >
                  비밀번호 변경
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default ProfilePage;
