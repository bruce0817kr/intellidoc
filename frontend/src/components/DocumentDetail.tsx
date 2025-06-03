import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Tabs, Descriptions, Button, Spin, Alert, Tag, Space, Collapse, Typography, message } from 'antd';
import { FileTextOutlined, FileExcelOutlined, DownloadOutlined, SyncOutlined } from '@ant-design/icons';
import { useDocument } from '../hooks/useDocuments';
import apiClient from '../utils/apiClient';

const { TabPane } = Tabs;
const { Panel } = Collapse;
const { Title, Text, Paragraph } = Typography;

/**
 * 문서 상세 컴포넌트
 */
const DocumentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { document, loading, error, fetchDocument, processDocument } = useDocument();
  const [activeTab, setActiveTab] = useState<string>('info');
  const [ocrResult, setOcrResult] = useState<any>(null);
  const [llmResult, setLlmResult] = useState<any>(null);
  const [ocrLoading, setOcrLoading] = useState<boolean>(false);
  const [llmLoading, setLlmLoading] = useState<boolean>(false);
  const [exportLoading, setExportLoading] = useState<boolean>(false);

  // 문서 정보 로드
  useEffect(() => {
    if (id) {
      fetchDocument(id);
    }
  }, [id]);

  // OCR 결과 로드
  const loadOcrResult = async () => {
    if (!id) return;
    
    setOcrLoading(true);
    try {
      const response = await apiClient.get(`/ocr/results/${id}`);
      setOcrResult(response.data);
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'OCR 결과 로드 중 오류가 발생했습니다.');
    } finally {
      setOcrLoading(false);
    }
  };

  // LLM 결과 로드
  const loadLlmResult = async () => {
    if (!id) return;
    
    setLlmLoading(true);
    try {
      const response = await apiClient.get(`/llm/results/${id}`);
      setLlmResult(response.data);
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'LLM 결과 로드 중 오류가 발생했습니다.');
    } finally {
      setLlmLoading(false);
    }
  };

  // 탭 변경 시 데이터 로드
  useEffect(() => {
    if (activeTab === 'ocr' && !ocrResult) {
      loadOcrResult();
    } else if (activeTab === 'llm' && !llmResult) {
      loadLlmResult();
    }
  }, [activeTab]);

  // 문서 처리 요청
  const handleProcessDocument = async (type: 'ocr' | 'llm', options?: any) => {
    if (!id) return;
    
    try {
      if (type === 'ocr') {
        setOcrLoading(true);
        await processDocument(id, { process_type: 'ocr', ...options });
        await loadOcrResult();
      } else if (type === 'llm') {
        setLlmLoading(true);
        await processDocument(id, { process_type: 'llm', ...options });
        await loadLlmResult();
      }
      
      message.success(`문서 ${type.toUpperCase()} 처리가 요청되었습니다.`);
    } catch (err: any) {
      message.error(err.response?.data?.detail || `문서 ${type.toUpperCase()} 처리 요청 중 오류가 발생했습니다.`);
    } finally {
      if (type === 'ocr') setOcrLoading(false);
      else if (type === 'llm') setLlmLoading(false);
    }
  };

  // 문서 내보내기
  const handleExport = async (format: 'excel' | 'csv' | 'pdf') => {
    if (!id) return;
    
    setExportLoading(true);
    
    try {
      // 파일 다운로드 요청
      const response = await apiClient.get(`/export/${id}/${format}`, {
        responseType: 'blob',
      });
      
      // 파일명 추출
      const contentDisposition = response.headers['content-disposition'];
      let filename = document?.original_filename?.split('.')[0] || 'export';
      
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
      const link = (document as any).createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      (document as any).body.appendChild(link);
      link.click();
      (document as any).body.removeChild(link);
      
      message.success(`${filename} 파일이 다운로드되었습니다.`);
    } catch (err) {
      message.error('파일 내보내기 중 오류가 발생했습니다.');
    } finally {
      setExportLoading(false);
    }
  };

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

  if (loading && !document) {
    return <Spin size="large" tip="문서 정보를 불러오는 중..." />;
  }

  if (error) {
    return <Alert message="오류" description={error} type="error" showIcon />;
  }

  if (!document) {
    return <Alert message="문서를 찾을 수 없습니다." type="warning" showIcon />;
  }

  return (
    <div>
      <Card title={document.original_filename}>
        <Descriptions bordered>
          <Descriptions.Item label="상태">
            <Tag color={getStatusColor(document.status)}>
              {getStatusText(document.status)}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="파일 크기">
            {document.file_size < 1024
              ? `${document.file_size} B`
              : document.file_size < 1024 * 1024
              ? `${(document.file_size / 1024).toFixed(2)} KB`
              : `${(document.file_size / (1024 * 1024)).toFixed(2)} MB`}
          </Descriptions.Item>
          <Descriptions.Item label="파일 유형">{document.file_type}</Descriptions.Item>
          <Descriptions.Item label="업로드 날짜">
            {new Date(document.upload_date).toLocaleString('ko-KR')}
          </Descriptions.Item>
          <Descriptions.Item label="처리 날짜">
            {document.processed_date
              ? new Date(document.processed_date).toLocaleString('ko-KR')
              : '-'}
          </Descriptions.Item>
        </Descriptions>

        <Space className="mt-4">
          <Button
            type="primary"
            icon={<FileExcelOutlined />}
            onClick={() => handleExport('excel')}
            loading={exportLoading}
            disabled={document.status !== 'COMPLETED'}
          >
            Excel 내보내기
          </Button>
          <Button
            type="default"
            icon={<FileTextOutlined />}
            onClick={() => handleExport('csv')}
            loading={exportLoading}
            disabled={document.status !== 'COMPLETED'}
          >
            CSV 내보내기
          </Button>
          <Button
            type="default"
            icon={<DownloadOutlined />}
            onClick={() => handleExport('pdf')}
            loading={exportLoading}
            disabled={document.status !== 'COMPLETED'}
          >
            PDF 내보내기
          </Button>
        </Space>
      </Card>

      <Tabs activeKey={activeTab} onChange={setActiveTab} className="mt-4">
        <TabPane tab="문서 정보" key="info">
          <Card>
            <Collapse defaultActiveKey={['metadata']}>
              <Panel header="메타데이터" key="metadata">
                {document.metadata ? (
                  <pre>{JSON.stringify(document.metadata, null, 2)}</pre>
                ) : (
                  <Text type="secondary">메타데이터가 없습니다.</Text>
                )}
              </Panel>
            </Collapse>
          </Card>
        </TabPane>

        <TabPane tab="OCR 결과" key="ocr">
          <Card
            title="OCR 처리 결과"
            extra={
              <Button
                type="primary"
                icon={<SyncOutlined />}
                onClick={() => handleProcessDocument('ocr')}
                loading={ocrLoading}
              >
                OCR 처리
              </Button>
            }
          >
            {ocrLoading ? (
              <Spin tip="OCR 결과를 불러오는 중..." />
            ) : ocrResult ? (
              ocrResult.status === 'not_processed' ? (
                <Alert
                  message="OCR 처리되지 않음"
                  description="이 문서는 아직 OCR 처리되지 않았습니다. OCR 처리 버튼을 클릭하여 처리를 시작하세요."
                  type="info"
                  showIcon
                />
              ) : (
                <div>
                  <Title level={4}>추출된 텍스트</Title>
                  <Card className="mb-4">
                    <Paragraph
                      ellipsis={{ rows: 10, expandable: true, symbol: '더 보기' }}
                    >
                      {ocrResult.results?.full_text || '추출된 텍스트가 없습니다.'}
                    </Paragraph>
                  </Card>

                  <Title level={4}>추출된 필드</Title>
                  <Collapse>
                    {Object.entries(ocrResult.results || {})
                      .filter(([key]) => key !== 'full_text')
                      .map(([key, value]) => (
                        <Panel header={key} key={key}>
                          <pre>{JSON.stringify(value, null, 2)}</pre>
                        </Panel>
                      ))}
                  </Collapse>
                </div>
              )
            ) : (
              <Alert
                message="OCR 결과 없음"
                description="OCR 결과를 불러올 수 없습니다. OCR 처리 버튼을 클릭하여 처리를 시작하세요."
                type="warning"
                showIcon
              />
            )}
          </Card>
        </TabPane>

        <TabPane tab="LLM 결과" key="llm">
          <Card
            title="LLM 처리 결과"
            extra={
              <Space>
                <Button
                  type="primary"
                  onClick={() => handleProcessDocument('llm', { task_type: 'summary' })}
                  loading={llmLoading}
                >
                  요약 생성
                </Button>
                <Button
                  onClick={() => handleProcessDocument('llm', { task_type: 'extraction' })}
                  loading={llmLoading}
                >
                  정보 추출
                </Button>
                <Button
                  onClick={() => handleProcessDocument('llm', { task_type: 'classification' })}
                  loading={llmLoading}
                >
                  문서 분류
                </Button>
              </Space>
            }
          >
            {llmLoading ? (
              <Spin tip="LLM 결과를 불러오는 중..." />
            ) : llmResult ? (
              llmResult.status === 'not_processed' ? (
                <Alert
                  message="LLM 처리되지 않음"
                  description="이 문서는 아직 LLM 처리되지 않았습니다. LLM 처리 버튼을 클릭하여 처리를 시작하세요."
                  type="info"
                  showIcon
                />
              ) : (
                <div>
                  {llmResult.results?.summary && (
                    <div className="mb-4">
                      <Title level={4}>요약</Title>
                      <Card>
                        <Paragraph>{llmResult.results.summary.result?.summary || '요약 결과가 없습니다.'}</Paragraph>
                      </Card>
                    </div>
                  )}

                  {llmResult.results?.extraction && (
                    <div className="mb-4">
                      <Title level={4}>추출된 정보</Title>
                      <Card>
                        <Descriptions bordered column={1}>
                          {Object.entries(llmResult.results.extraction.result?.extracted_data || {}).map(([key, value]) => (
                            <Descriptions.Item label={key} key={key}>
                              {String(value)}
                            </Descriptions.Item>
                          ))}
                        </Descriptions>
                      </Card>
                    </div>
                  )}

                  {llmResult.results?.classification && (
                    <div className="mb-4">
                      <Title level={4}>문서 분류</Title>
                      <Card>
                        <Tag color="blue" style={{ fontSize: '16px', padding: '5px 10px' }}>
                          {llmResult.results.classification.result?.category || '분류 결과가 없습니다.'}
                        </Tag>
                      </Card>
                    </div>
                  )}
                </div>
              )
            ) : (
              <Alert
                message="LLM 결과 없음"
                description="LLM 결과를 불러올 수 없습니다. LLM 처리 버튼을 클릭하여 처리를 시작하세요."
                type="warning"
                showIcon
              />
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default DocumentDetail;
