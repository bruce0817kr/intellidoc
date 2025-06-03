import React from 'react';
import { useParams } from 'react-router-dom';
import DocumentDetail from '../components/DocumentDetail';
import { Typography } from 'antd';

const { Title } = Typography;

/**
 * 문서 상세 페이지 컴포넌트
 */
const DocumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div>
      <Title level={2}>문서 상세 정보</Title>
      <DocumentDetail />
    </div>
  );
};

export default DocumentDetailPage;
