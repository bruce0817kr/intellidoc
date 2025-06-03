"""
배치 처리 시스템 모듈

주요 기능:
1. 대량 문서 처리
2. 병렬 처리 지원
3. 진행 상황 모니터링
4. 처리 결과 집계
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging

from shared.logger import log_info, log_error
from shared.exceptions import OCREngineError, ResourceNotFoundError


class BatchStatus(Enum):
    """배치 상태 열거형"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """배치 작업 정보"""
    id: str
    document_ids: List[uuid.UUID]
    engine_name: str
    options: Dict[str, Any]
    status: BatchStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    results: List[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []
        self.total_documents = len(self.document_ids)
    
    @property
    def progress_percentage(self) -> float:
        """진행률 계산"""
        if self.total_documents == 0:
            return 0.0
        return (self.processed_documents / self.total_documents) * 100
    
    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.processed_documents == 0:
            return 0.0
        return ((self.processed_documents - self.failed_documents) / self.processed_documents) * 100


class BatchProgress:
    """배치 진행 상황 추적"""
    
    def __init__(self, batch_id: str, total: int):
        self.batch_id = batch_id
        self.total = total
        self.processed = 0
        self.failed = 0
        self.current_document = None
        self.start_time = datetime.now()
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """진행 상황 콜백 추가"""
        self.callbacks.append(callback)
    
    def update(self, document_id: str, success: bool, result: Optional[Dict] = None):
        """진행 상황 업데이트"""
        self.processed += 1
        if not success:
            self.failed += 1
        
        # 콜백 호출
        for callback in self.callbacks:
            try:
                callback(self.batch_id, self.processed, self.total, success, result)
            except Exception as e:
                log_error(f"배치 진행 콜백 오류: {str(e)}")
    
    @property
    def percentage(self) -> float:
        """진행률"""
        if self.total == 0:
            return 100.0
        return (self.processed / self.total) * 100
    
    @property
    def estimated_remaining_time(self) -> float:
        """남은 시간 추정 (초)"""
        if self.processed == 0:
            return 0.0
        
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        avg_time_per_doc = elapsed_time / self.processed
        remaining_docs = self.total - self.processed
        
        return avg_time_per_doc * remaining_docs


class BatchProcessor:
    """배치 처리기"""
    
    def __init__(self, max_workers: int = 4, use_processes: bool = False):
        """
        배치 처리기 초기화
        
        Args:
            max_workers: 최대 워커 수
            use_processes: 프로세스 풀 사용 여부 (True: 프로세스, False: 스레드)
        """
        self.max_workers = max_workers
        self.use_processes = use_processes
        self.active_jobs: Dict[str, BatchJob] = {}
        self.job_history: List[BatchJob] = []
        
        # 실행자 풀 설정
        if use_processes:
            self.executor = ProcessPoolExecutor(max_workers=max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        log_info(f"배치 처리기 초기화: {max_workers}개 워커, {'프로세스' if use_processes else '스레드'} 풀")
    
    def create_batch_job(
        self,
        document_ids: List[uuid.UUID],
        engine_name: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        배치 작업 생성
        
        Args:
            document_ids: 처리할 문서 ID 목록
            engine_name: OCR 엔진 이름
            options: 처리 옵션
            
        Returns:
            str: 배치 작업 ID
        """
        batch_id = str(uuid.uuid4())
        
        batch_job = BatchJob(
            id=batch_id,
            document_ids=document_ids,
            engine_name=engine_name,
            options=options or {},
            status=BatchStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.active_jobs[batch_id] = batch_job
        
        log_info(f"배치 작업 생성: {batch_id}, 문서 수: {len(document_ids)}, 엔진: {engine_name}")
        
        return batch_id
    
    async def process_batch(
        self,
        batch_id: str,
        ocr_processor: Callable,
        progress_callback: Optional[Callable] = None
    ) -> BatchJob:
        """
        배치 처리 실행
        
        Args:
            batch_id: 배치 작업 ID
            ocr_processor: OCR 처리 함수
            progress_callback: 진행 상황 콜백
            
        Returns:
            BatchJob: 완료된 배치 작업
        """
        if batch_id not in self.active_jobs:
            raise ValueError(f"배치 작업을 찾을 수 없습니다: {batch_id}")
        
        batch_job = self.active_jobs[batch_id]
        
        try:
            # 배치 상태 업데이트
            batch_job.status = BatchStatus.RUNNING
            batch_job.started_at = datetime.now()
            
            # 진행 상황 추적기 생성
            progress = BatchProgress(batch_id, len(batch_job.document_ids))
            if progress_callback:
                progress.add_callback(progress_callback)
            
            log_info(f"배치 처리 시작: {batch_id}")
            
            # 병렬 처리
            if self.use_processes:
                results = await self._process_with_processes(batch_job, ocr_processor, progress)
            else:
                results = await self._process_with_threads(batch_job, ocr_processor, progress)
            
            # 결과 집계
            batch_job.results = results
            batch_job.processed_documents = len(results)
            batch_job.failed_documents = sum(1 for r in results if not r.get("success", False))
            batch_job.status = BatchStatus.COMPLETED
            batch_job.completed_at = datetime.now()
            
            log_info(f"배치 처리 완료: {batch_id}, 성공: {batch_job.processed_documents - batch_job.failed_documents}, 실패: {batch_job.failed_documents}")
            
            # 활성 작업에서 제거하고 히스토리에 추가
            del self.active_jobs[batch_id]
            self.job_history.append(batch_job)
            
            return batch_job
            
        except Exception as e:
            # 오류 처리
            batch_job.status = BatchStatus.FAILED
            batch_job.error_message = str(e)
            batch_job.completed_at = datetime.now()
            
            log_error(f"배치 처리 실패: {batch_id}, 오류: {str(e)}")
            
            # 활성 작업에서 제거하고 히스토리에 추가
            del self.active_jobs[batch_id]
            self.job_history.append(batch_job)
            
            raise OCREngineError(
                message=f"배치 처리 중 오류가 발생했습니다: {str(e)}",
                details={"batch_id": batch_id}
            )
    
    async def _process_with_threads(
        self,
        batch_job: BatchJob,
        ocr_processor: Callable,
        progress: BatchProgress
    ) -> List[Dict[str, Any]]:
        """스레드 풀을 사용한 배치 처리"""
        results = []
        
        # 세마포어로 동시 실행 수 제한
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_document(document_id: uuid.UUID) -> Dict[str, Any]:
            async with semaphore:
                try:
                    # OCR 처리 실행
                    result = await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        ocr_processor,
                        document_id,
                        batch_job.engine_name,
                        batch_job.options
                    )
                    
                    progress.update(str(document_id), True, result)
                    
                    return {
                        "document_id": str(document_id),
                        "success": True,
                        "result": result
                    }
                    
                except Exception as e:
                    log_error(f"문서 처리 실패: {document_id}, 오류: {str(e)}")
                    
                    progress.update(str(document_id), False)
                    
                    return {
                        "document_id": str(document_id),
                        "success": False,
                        "error": str(e)
                    }
        
        # 모든 문서를 병렬로 처리
        tasks = [process_document(doc_id) for doc_id in batch_job.document_ids]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        return results
    
    async def _process_with_processes(
        self,
        batch_job: BatchJob,
        ocr_processor: Callable,
        progress: BatchProgress
    ) -> List[Dict[str, Any]]:
        """프로세스 풀을 사용한 배치 처리"""
        results = []
        
        # 프로세스 풀로 처리
        loop = asyncio.get_event_loop()
        futures = []
        
        for document_id in batch_job.document_ids:
            future = loop.run_in_executor(
                self.executor,
                self._process_single_document,
                document_id,
                batch_job.engine_name,
                batch_job.options,
                ocr_processor
            )
            futures.append(future)
        
        # 결과 수집
        for i, future in enumerate(asyncio.as_completed(futures)):
            try:
                result = await future
                progress.update(str(batch_job.document_ids[i]), result["success"], result)
                results.append(result)
            except Exception as e:
                log_error(f"프로세스 처리 실패: {str(e)}")
                progress.update(str(batch_job.document_ids[i]), False)
                results.append({
                    "document_id": str(batch_job.document_ids[i]),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def _process_single_document(
        self,
        document_id: uuid.UUID,
        engine_name: str,
        options: Dict[str, Any],
        ocr_processor: Callable
    ) -> Dict[str, Any]:
        """단일 문서 처리 (프로세스 풀용)"""
        try:
            result = ocr_processor(document_id, engine_name, options)
            return {
                "document_id": str(document_id),
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "document_id": str(document_id),
                "success": False,
                "error": str(e)
            }
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchJob]:
        """배치 상태 조회"""
        # 활성 작업에서 찾기
        if batch_id in self.active_jobs:
            return self.active_jobs[batch_id]
        
        # 히스토리에서 찾기
        for job in self.job_history:
            if job.id == batch_id:
                return job
        
        return None
    
    def cancel_batch(self, batch_id: str) -> bool:
        """배치 취소"""
        if batch_id not in self.active_jobs:
            return False
        
        batch_job = self.active_jobs[batch_id]
        batch_job.status = BatchStatus.CANCELLED
        batch_job.completed_at = datetime.now()
        
        # 활성 작업에서 제거하고 히스토리에 추가
        del self.active_jobs[batch_id]
        self.job_history.append(batch_job)
        
        log_info(f"배치 작업 취소: {batch_id}")
        
        return True
    
    def get_active_batches(self) -> List[BatchJob]:
        """활성 배치 목록 조회"""
        return list(self.active_jobs.values())
    
    def get_batch_history(self, limit: int = 100) -> List[BatchJob]:
        """배치 히스토리 조회"""
        return self.job_history[-limit:]
    
    def cleanup_history(self, days: int = 30):
        """오래된 히스토리 정리"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        original_count = len(self.job_history)
        self.job_history = [job for job in self.job_history if job.completed_at and job.completed_at > cutoff_date]
        
        cleaned_count = original_count - len(self.job_history)
        if cleaned_count > 0:
            log_info(f"배치 히스토리 정리: {cleaned_count}개 작업 제거")
    
    def __del__(self):
        """리소스 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)


# 전역 배치 처리기 인스턴스
batch_processor = BatchProcessor()


def get_batch_processor() -> BatchProcessor:
    """배치 처리기 인스턴스 반환"""
    return batch_processor
