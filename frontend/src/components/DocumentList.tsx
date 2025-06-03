import React, { useState, useEffect } from 'react';
import { Table, Tag, Button, Space, Tooltip, Modal, message } from 'antd';
import { EyeOutlined, DeleteOutlined, DownloadOutlined, FileExcelOutlined, FileTextOutlined } from '@ant-design/icons';
import { useDocuments, Document } from '../hooks/useDocuments';
import { useNavigate } from 'react-router-dom';
import apiClient from '../utils/apiClient';

/**
 * 문서 목록 컴포넌트
 */
const DocumentList: React.FC = () => {
  const { documents, loading, error, fetchDocuments, deleteDocument } = useDocuments();
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [deleteModalVisible, setDeleteModalVisible] = useState<boolean>(false);
  const [exportLoading, setExportLoading] = useState<boolean>(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (error) {
      message.error(error);
    }
  }, [error]);

  // 문서 상태에 따른 태그 색상
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PENDING':
        return 'orange';
      case 'PROCESSING':
        return 'blue';
      case 'COMPLETED':
        return 'green';
      case 'FAILED':
        return 'red';
      default:
        return 'default';
    }
  };

  // 문서 상태 한글 표시
  const getStatusText = (status: string) => {
    switch (status) {
      case 'PENDING':
        return '대기 중';
      case 'PROCESSING':
        return '처리 중';
      case 'COMPLETED':
        return '완료';
      case 'FAILED':
        return '실패';
      default:
        return status;
    }
  };

  // 문서 삭제 확인
  const showDeleteConfirm = (document: Document) => {
    setSelectedDocument(document);
    setDeleteModalVisible(true);
  };

  // 문서 삭제 처리
  const handleDelete = async () => {
    if (!selectedDocument) return;
    
    try {
      await deleteDocument(selectedDocument.id);
      message.success(`${selectedDocument.original_filename} 문서가 삭제되었습니다.`);
      setDeleteModalVisible(false);
      setSelectedDocument(null);
    } catch (err) {
      message.error('문서 삭제 중 오류가 발생했습니다.');
    }
  };

  // 문서 내보내기
  const handleExport = async (documentId: string, format: 'excel' | 'csv' | 'pdf') => {
    setExportLoading(true);
    
    try {
      // 파일 다운로드 요청
      const response = await apiClient.get(`/export/${documentId}/${format}`, {
        responseType: 'blob',
      });
      
      // 파일명 추출
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'export';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }
      
      // 확장자 추가
      if (!filename.includes('.')) {
        switch (format) {
          case 'excel':
            filename += '.xlsx';
            break;
          case 'csv':
            filename += '.csv';
            break;
          case 'pdf':
            filename += '.pdf';
            break;
        }
      }
      
      // 파일 다운로드
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      message.success(`${filename} 파일이 다운로드되었습니다.`);
    } catch (err) {
      message.error('파일 내보내기 중 오류가 발생했습니다.');
    } finally {
      setExportLoading(false);
    }
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: '파일명',
      dataIndex: 'original_filename',
      key: 'original_filename',
      render: (text: string, record: Document) => (
        <a onClick={() => navigate(`/documents/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '파일 크기',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => {
        if (size < 1024) {
          return `${size} B`;
        } else if (size < 1024 * 1024) {
          return `${(size / 1024).toFixed(2)} KB`;
        } else {
          return `${(size / (1024 * 1024)).toFixed(2)} MB`;
        }
      },
    },
    {
      title: '업로드 날짜',
      dataIndex: 'upload_date',
      key: 'upload_date',
      render: (date: string) => new Date(date).toLocaleString('ko-KR'),
    },
    {
      title: '처리 날짜',
      dataIndex: 'processed_date',
      key: 'processed_date',
      render: (date: string) => date ? new Date(date).toLocaleString('ko-KR') : '-',
    },
    {
      title: '작업',
      key: 'actions',
      render: (_: any, record: Document) => (
        <Space size="middle">
          <Tooltip title="상세 보기">
            <Button
              type="primary"
              icon={<EyeOutlined />}
              size="small"
              onClick={() => navigate(`/documents/${record.id}`)}
            />
          </Tooltip>
          
          {record.status === 'COMPLETED' && (
            <>
              <Tooltip title="Excel 내보내기">
                <Button
                  type="default"
                  icon={<FileExcelOutlined />}
                  size="small"
                  onClick={() => handleExport(record.id, 'excel')}
                  loading={exportLoading}
                />
              </Tooltip>
              <Tooltip title="CSV 내보내기">
                <Button
                  type="default"
                  icon={<FileTextOutlined />}
                  size="small"
                  onClick={() => handleExport(record.id, 'csv')}
                  loading={exportLoading}
                />
              </Tooltip>
              <Tooltip title="PDF 내보내기">
                <Button
                  type="default"
                  icon={<DownloadOutlined />}
                  size="small"
                  onClick={() => handleExport(record.id, 'pdf')}
                  loading={exportLoading}
                />
              </Tooltip>
            </>
          )}
          
          <Tooltip title="삭제">
            <Button
              type="primary"
              danger
              icon={<DeleteOutlined />}
              size="small"
              onClick={() => showDeleteConfirm(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Table
        columns={columns}
        dataSource={documents.map(doc => ({ ...doc, key: doc.id }))}
        loading={loading}
        pagination={{ pageSize: 10 }}
        rowClassName={(record) => record.status === 'FAILED' ? 'table-row-error' : ''}
      />
      
      <Modal
        title="문서 삭제"
        open={deleteModalVisible}
        onOk={handleDelete}
        onCancel={() => setDeleteModalVisible(false)}
        okText="삭제"
        cancelText="취소"
      >
        <p>
          {selectedDocument?.original_filename} 문서를 삭제하시겠습니까?
          <br />
          이 작업은 되돌릴 수 없습니다.
        </p>
      </Modal>
    </div>
  );
};

export default DocumentList;
