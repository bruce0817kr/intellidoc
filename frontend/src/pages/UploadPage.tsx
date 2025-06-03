import React from 'react';
import { Typography, Card } from 'antd';
import FileUploader from '../components/FileUploader';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph } = Typography;

/**
 * 업로드 페이지 컴포넌트
 */
const UploadPage: React.FC = () => {
  const navigate = useNavigate();

  // 업로드 성공 핸들러
  const handleUploadSuccess = (data: any) => {
    // 업로드 성공 시 해당 문서 상세 페이지로 이동
    navigate(`/documents/${data.document_id}`);
  };

  return (
    <div>
      <Title level={2}>문서 업로드</Title>
      
      <Paragraph>
        처리할 문서를 업로드하세요. PDF, 이미지(JPG, PNG, TIFF), 워드 문서(DOC, DOCX) 형식을 지원합니다.
      </Paragraph>
      
      <FileUploader 
        onUploadSuccess={handleUploadSuccess}
        allowedTypes={['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.doc', '.docx']}
        maxSize={20 * 1024 * 1024} // 20MB
      />
      
      <Card title="업로드 가이드" className="mt-4">
        <Typography>
          <Title level={4}>지원 파일 형식</Title>
          <Paragraph>
            <ul>
              <li><strong>PDF 문서</strong>: .pdf</li>
              <li><strong>이미지</strong>: .jpg, .jpeg, .png, .tiff, .bmp</li>
              <li><strong>워드 문서</strong>: .doc, .docx</li>
            </ul>
          </Paragraph>
          
          <Title level={4}>파일 크기 제한</Title>
          <Paragraph>
            최대 20MB까지 업로드 가능합니다.
          </Paragraph>
          
          <Title level={4}>처리 과정</Title>
          <Paragraph>
            <ol>
              <li>파일 업로드 및 검증</li>
              <li>OCR 처리 (텍스트 추출)</li>
              <li>LLM 처리 (내용 분석)</li>
              <li>데이터 구조화 및 저장</li>
            </ol>
          </Paragraph>
          
          <Title level={4}>주의사항</Title>
          <Paragraph>
            <ul>
              <li>스캔된 문서는 해상도가 높을수록 OCR 정확도가 향상됩니다.</li>
              <li>문서가 기울어지거나 왜곡된 경우 처리 정확도가 떨어질 수 있습니다.</li>
              <li>개인정보가 포함된 문서는 업로드 전 확인해주세요.</li>
            </ul>
          </Paragraph>
        </Typography>
      </Card>
    </div>
  );
};

export default UploadPage;
