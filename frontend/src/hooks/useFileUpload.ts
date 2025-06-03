import { useState } from 'react';
import apiClient from '../utils/apiClient';

// 파일 업로드 훅 반환 타입
interface UseFileUploadReturn {
  uploading: boolean;
  progress: number;
  error: string | null;
  uploadFile: (file: File) => Promise<any>;
  resetState: () => void;
}

/**
 * 파일 업로드 커스텀 훅
 * 
 * @returns {UseFileUploadReturn} 파일 업로드 상태 및 함수
 */
export const useFileUpload = (): UseFileUploadReturn => {
  const [uploading, setUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  /**
   * 파일 업로드 함수
   * 
   * @param {File} file - 업로드할 파일
   * @returns {Promise<any>} 업로드 결과
   */
  const uploadFile = async (file: File): Promise<any> => {
    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      // FormData 생성
      const formData = new FormData();
      formData.append('file', file);

      // 업로드 요청
      const response = await apiClient.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(percentCompleted);
          }
        },
      });

      setUploading(false);
      return response.data;
    } catch (err: any) {
      setUploading(false);
      setError(err.response?.data?.detail || '파일 업로드 중 오류가 발생했습니다.');
      throw err;
    }
  };

  /**
   * 상태 초기화 함수
   */
  const resetState = () => {
    setUploading(false);
    setProgress(0);
    setError(null);
  };

  return {
    uploading,
    progress,
    error,
    uploadFile,
    resetState,
  };
};
