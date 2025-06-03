import React from 'react';
import { Button, Card, Progress, Alert, Upload, message } from 'antd';
import { UploadOutlined, FileOutlined, DeleteOutlined } from '@ant-design/icons';
import { useFileUpload } from '../hooks/useFileUpload';

interface FileUploaderProps {
  onUploadSuccess?: (data: any) => void;
  onUploadError?: (error: string) => void;
  allowedTypes?: string[];
  maxSize?: number; // 바이트 단위
}

/**
 * 파일 업로드 컴포넌트
 */
const FileUploader: React.FC<FileUploaderProps> = ({
  onUploadSuccess,
  onUploadError,
  allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.doc', '.docx'],
  maxSize = 10 * 1024 * 1024, // 기본 10MB
}) => {
  const { uploading, progress, error, uploadFile, resetState } = useFileUpload();

  // 파일 업로드 전 검증
  const beforeUpload = (file: File) => {
    // 파일 형식 검증
    const fileType = `.${file.name.split('.').pop()?.toLowerCase()}`;
    const isAllowedType = allowedTypes.includes(fileType);
    if (!isAllowedType) {
      message.error(`${file.name}은(는) 지원하지 않는 파일 형식입니다. 지원 형식: ${allowedTypes.join(', ')}`);
      return false;
    }

    // 파일 크기 검증
    const isLessThanMaxSize = file.size <= maxSize;
    if (!isLessThanMaxSize) {
      message.error(`파일 크기는 ${maxSize / 1024 / 1024}MB 이하여야 합니다.`);
      return false;
    }

    return true;
  };

  // 파일 업로드 처리
  const handleUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    
    if (!beforeUpload(file)) {
      onError('파일 검증 실패');
      return;
    }

    try {
      const result = await uploadFile(file);
      onSuccess(result);
      
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
      
      message.success(`${file.name} 업로드 성공`);
    } catch (err: any) {
      onError(err);
      
      if (onUploadError) {
        onUploadError(err.message || '업로드 실패');
      }
    }
  };

  return (
    <Card title="문서 업로드" className="mb-4">
      <Upload.Dragger
        name="file"
        multiple={false}
        customRequest={handleUpload}
        showUploadList={false}
        disabled={uploading}
      >
        <p className="ant-upload-drag-icon">
          <FileOutlined />
        </p>
        <p className="ant-upload-text">
          이 영역을 클릭하거나 파일을 끌어다 놓으세요
        </p>
        <p className="ant-upload-hint">
          지원 형식: {allowedTypes.join(', ')} / 최대 크기: {maxSize / 1024 / 1024}MB
        </p>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          loading={uploading}
          disabled={uploading}
          className="mt-3"
        >
          파일 선택
        </Button>
      </Upload.Dragger>

      {uploading && (
        <div className="mt-4">
          <Progress percent={progress} status="active" />
          <p className="text-center">업로드 중... {progress}%</p>
        </div>
      )}

      {error && (
        <Alert
          message="업로드 오류"
          description={error}
          type="error"
          showIcon
          closable
          className="mt-4"
          onClose={resetState}
        />
      )}
    </Card>
  );
};

export default FileUploader;
