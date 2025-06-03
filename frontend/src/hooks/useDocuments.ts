import { useState, useEffect } from 'react';
import apiClient from '../utils/apiClient';

// 문서 타입 정의
export interface Document {
  id: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  status: string;
  upload_date: string;
  processed_date?: string;
  uploaded_by: string;
  metadata?: Record<string, any>;
}

// 문서 목록 훅 반환 타입
interface UseDocumentsReturn {
  documents: Document[];
  loading: boolean;
  error: string | null;
  fetchDocuments: () => Promise<void>;
  deleteDocument: (id: string) => Promise<void>;
}

/**
 * 문서 목록 관리 커스텀 훅
 * 
 * @returns {UseDocumentsReturn} 문서 목록 상태 및 함수
 */
export const useDocuments = (): UseDocumentsReturn => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 컴포넌트 마운트 시 문서 목록 조회
  useEffect(() => {
    fetchDocuments();
  }, []);

  /**
   * 문서 목록 조회 함수
   */
  const fetchDocuments = async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get('/documents');
      setDocuments(response.data);
      setLoading(false);
    } catch (err: any) {
      setLoading(false);
      setError(err.response?.data?.detail || '문서 목록 조회 중 오류가 발생했습니다.');
    }
  };

  /**
   * 문서 삭제 함수
   * 
   * @param {string} id - 삭제할 문서 ID
   */
  const deleteDocument = async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/documents/${id}`);
      // 목록에서 삭제된 문서 제거
      setDocuments(documents.filter(doc => doc.id !== id));
    } catch (err: any) {
      setError(err.response?.data?.detail || '문서 삭제 중 오류가 발생했습니다.');
      throw err;
    }
  };

  return {
    documents,
    loading,
    error,
    fetchDocuments,
    deleteDocument,
  };
};

// 단일 문서 훅 반환 타입
interface UseDocumentReturn {
  document: Document | null;
  loading: boolean;
  error: string | null;
  fetchDocument: (id: string) => Promise<void>;
  processDocument: (id: string, options?: Record<string, any>) => Promise<any>;
}

/**
 * 단일 문서 관리 커스텀 훅
 * 
 * @returns {UseDocumentReturn} 문서 상태 및 함수
 */
export const useDocument = (): UseDocumentReturn => {
  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * 문서 조회 함수
   * 
   * @param {string} id - 문서 ID
   */
  const fetchDocument = async (id: string): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`/documents/${id}`);
      setDocument(response.data);
      setLoading(false);
    } catch (err: any) {
      setLoading(false);
      setError(err.response?.data?.detail || '문서 조회 중 오류가 발생했습니다.');
    }
  };

  /**
   * 문서 처리 함수
   * 
   * @param {string} id - 문서 ID
   * @param {Record<string, any>} options - 처리 옵션
   * @returns {Promise<any>} 처리 결과
   */
  const processDocument = async (id: string, options?: Record<string, any>): Promise<any> => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post(`/documents/${id}/process`, options || {});
      // 처리 후 문서 정보 업데이트
      await fetchDocument(id);
      setLoading(false);
      return response.data;
    } catch (err: any) {
      setLoading(false);
      setError(err.response?.data?.detail || '문서 처리 중 오류가 발생했습니다.');
      throw err;
    }
  };

  return {
    document,
    loading,
    error,
    fetchDocument,
    processDocument,
  };
};
