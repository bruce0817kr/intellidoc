import React from 'react';
import { Typography, Row, Col, Statistic, Card, Button } from 'antd';
import { FileTextOutlined, CheckCircleOutlined, SyncOutlined, WarningOutlined, UploadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import DocumentList from '../components/DocumentList';
import { useDocuments } from '../hooks/useDocuments';

const { Title } = Typography;

/**
 * 대시보드 페이지 컴포넌트
 */
const Dashboard: React.FC = () => {
  const { documents, loading } = useDocuments();
  const navigate = useNavigate();

  // 문서 상태별 개수 계산
  const getDocumentStats = () => {
    const stats = {
      total: documents.length,
      completed: 0,
      processing: 0,
      failed: 0,
    };

    documents.forEach(doc => {
      if (doc.status === 'COMPLETED') {
        stats.completed++;
      } else if (doc.status === 'PROCESSING') {
        stats.processing++;
      } else if (doc.status === 'FAILED') {
        stats.failed++;
      }
    });

    return stats;
  };

  const stats = getDocumentStats();

  return (
    <div>
      <Title level={2}>대시보드</Title>
      
      <Row gutter={16} className="mb-4">
        <Col span={6}>
          <Card>
            <Statistic
              title="전체 문서"
              value={stats.total}
              prefix={<FileTextOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="처리 완료"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="처리 중"
              value={stats.processing}
              prefix={<SyncOutlined spin />}
              valueStyle={{ color: '#1890ff' }}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="처리 실패"
              value={stats.failed}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#cf1322' }}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>
      
      <div className="mb-4" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3}>문서 목록</Title>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={() => navigate('/upload')}
        >
          새 문서 업로드
        </Button>
      </div>
      
      <DocumentList />
    </div>
  );
};

export default Dashboard;
