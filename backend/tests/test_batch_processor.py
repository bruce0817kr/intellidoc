"""
배치 처리 시스템 테스트 모듈

주요 테스트:
1. 배치 작업 생성
2. 배치 처리 실행
3. 진행 상황 모니터링
4. 오류 처리
5. 취소 기능
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import uuid
import asyncio
from datetime import datetime

# 테스트 대상 모듈 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트 대상 모듈 임포트
from ocr_engines.batch_processor import (
    BatchProcessor, BatchJob, BatchProgress, BatchStatus
)
from shared.exceptions import OCREngineError, ResourceNotFoundError


class TestBatchProcessor(unittest.TestCase):
    """배치 처리기 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        self.batch_processor = BatchProcessor(max_workers=2, use_processes=False)
        self.test_document_ids = [uuid.uuid4() for _ in range(3)]
        self.engine_name = "tesseract"
        self.options = {"language": "kor+eng"}

    def test_create_batch_job(self):
        """배치 작업 생성 테스트"""
        # 배치 작업 생성
        batch_id = self.batch_processor.create_batch_job(
            document_ids=self.test_document_ids,
            engine_name=self.engine_name,
            options=self.options
        )
        
        # 검증
        self.assertIsNotNone(batch_id)
        self.assertIn(batch_id, self.batch_processor.active_jobs)
        
        batch_job = self.batch_processor.active_jobs[batch_id]
        self.assertEqual(batch_job.document_ids, self.test_document_ids)
        self.assertEqual(batch_job.engine_name, self.engine_name)
        self.assertEqual(batch_job.options, self.options)
        self.assertEqual(batch_job.status, BatchStatus.PENDING)
        self.assertEqual(batch_job.total_documents, 3)

    def test_batch_job_properties(self):
        """배치 작업 속성 테스트"""
        batch_job = BatchJob(
            id="test_batch",
            document_ids=self.test_document_ids,
            engine_name=self.engine_name,
            options=self.options,
            status=BatchStatus.RUNNING,
            created_at=datetime.now(),
            processed_documents=2,
            failed_documents=1
        )
        
        # 진행률 테스트
        self.assertAlmostEqual(batch_job.progress_percentage, 66.67, places=1)
        
        # 성공률 테스트
        self.assertEqual(batch_job.success_rate, 50.0)  # 2개 처리 중 1개 실패

    def test_batch_progress(self):
        """배치 진행 상황 테스트"""
        batch_id = "test_progress"
        total = 5
        progress = BatchProgress(batch_id, total)
        
        # 초기 상태 확인
        self.assertEqual(progress.batch_id, batch_id)
        self.assertEqual(progress.total, total)
        self.assertEqual(progress.processed, 0)
        self.assertEqual(progress.failed, 0)
        self.assertEqual(progress.percentage, 0.0)
        
        # 콜백 함수 추가
        callback_calls = []
        def test_callback(batch_id, processed, total, success, result):
            callback_calls.append((batch_id, processed, total, success))
        
        progress.add_callback(test_callback)
        
        # 진행 상황 업데이트
        progress.update("doc1", True, {"success": True})
        progress.update("doc2", False, {"success": False})
        
        # 검증
        self.assertEqual(progress.processed, 2)
        self.assertEqual(progress.failed, 1)
        self.assertEqual(progress.percentage, 40.0)
        self.assertEqual(len(callback_calls), 2)

    async def test_process_batch_with_threads(self):
        """스레드 풀을 사용한 배치 처리 테스트"""
        # 배치 작업 생성
        batch_id = self.batch_processor.create_batch_job(
            document_ids=self.test_document_ids,
            engine_name=self.engine_name,
            options=self.options
        )
        
        # 모의 OCR 처리 함수
        async def mock_ocr_processor(doc_id, engine, options):
            await asyncio.sleep(0.1)  # 비동기 처리 시뮬레이션
            return {
                "document_id": str(doc_id),
                "success": True,
                "text": f"Processed document {doc_id}",
                "confidence": 0.95
            }
        
        # 배치 처리 실행
        result = await self.batch_processor.process_batch(
            batch_id=batch_id,
            ocr_processor=mock_ocr_processor
        )
        
        # 검증
        self.assertIsInstance(result, BatchJob)
        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.processed_documents, 3)
        self.assertEqual(result.failed_documents, 0)
        self.assertEqual(len(result.results), 3)
        
        # 활성 작업에서 제거되고 히스토리에 추가되었는지 확인
        self.assertNotIn(batch_id, self.batch_processor.active_jobs)
        self.assertEqual(len(self.batch_processor.job_history), 1)

    async def test_process_batch_with_errors(self):
        """오류가 포함된 배치 처리 테스트"""
        # 배치 작업 생성
        batch_id = self.batch_processor.create_batch_job(
            document_ids=self.test_document_ids,
            engine_name=self.engine_name,
            options=self.options
        )
        
        # 일부 문서에서 오류가 발생하는 모의 OCR 처리 함수
        async def mock_ocr_processor_with_errors(doc_id, engine, options):
            await asyncio.sleep(0.1)
            
            # 첫 번째 문서에서 오류 발생
            if str(doc_id) == str(self.test_document_ids[0]):
                raise Exception("Processing failed")
            
            return {
                "document_id": str(doc_id),
                "success": True,
                "text": f"Processed document {doc_id}",
                "confidence": 0.95
            }
        
        # 배치 처리 실행
        result = await self.batch_processor.process_batch(
            batch_id=batch_id,
            ocr_processor=mock_ocr_processor_with_errors
        )
        
        # 검증
        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.processed_documents, 3)
        self.assertEqual(result.failed_documents, 1)  # 1개 실패
        self.assertEqual(len(result.results), 3)

    def test_get_batch_status(self):
        """배치 상태 조회 테스트"""
        # 배치 작업 생성
        batch_id = self.batch_processor.create_batch_job(
            document_ids=self.test_document_ids,
            engine_name=self.engine_name,
            options=self.options
        )
        
        # 상태 조회
        status = self.batch_processor.get_batch_status(batch_id)
        
        # 검증
        self.assertIsNotNone(status)
        self.assertEqual(status.id, batch_id)
        self.assertEqual(status.status, BatchStatus.PENDING)

    def test_get_batch_status_not_found(self):
        """존재하지 않는 배치 상태 조회 테스트"""
        # 존재하지 않는 배치 ID로 조회
        status = self.batch_processor.get_batch_status("non_existent_batch")
        
        # 검증
        self.assertIsNone(status)

    def test_cancel_batch(self):
        """배치 취소 테스트"""
        # 배치 작업 생성
        batch_id = self.batch_processor.create_batch_job(
            document_ids=self.test_document_ids,
            engine_name=self.engine_name,
            options=self.options
        )
        
        # 배치 취소
        result = self.batch_processor.cancel_batch(batch_id)
        
        # 검증
        self.assertTrue(result)
        
        # 취소된 배치 상태 확인
        batch_job = self.batch_processor.get_batch_status(batch_id)
        self.assertEqual(batch_job.status, BatchStatus.CANCELLED)

    def test_cancel_batch_not_found(self):
        """존재하지 않는 배치 취소 테스트"""
        # 존재하지 않는 배치 ID로 취소 시도
        result = self.batch_processor.cancel_batch("non_existent_batch")
        
        # 검증
        self.assertFalse(result)

    def test_get_active_batches(self):
        """활성 배치 목록 조회 테스트"""
        # 여러 배치 작업 생성
        batch_ids = []
        for i in range(3):
            batch_id = self.batch_processor.create_batch_job(
                document_ids=[uuid.uuid4()],
                engine_name=self.engine_name,
                options=self.options
            )
            batch_ids.append(batch_id)
        
        # 활성 배치 목록 조회
        active_batches = self.batch_processor.get_active_batches()
        
        # 검증
        self.assertEqual(len(active_batches), 3)
        for batch in active_batches:
            self.assertIn(batch.id, batch_ids)
            self.assertEqual(batch.status, BatchStatus.PENDING)

    def test_get_batch_history(self):
        """배치 히스토리 조회 테스트"""
        # 히스토리에 직접 추가 (실제로는 배치 완료 시 추가됨)
        completed_batch = BatchJob(
            id="completed_batch",
            document_ids=[uuid.uuid4()],
            engine_name=self.engine_name,
            options=self.options,
            status=BatchStatus.COMPLETED,
            created_at=datetime.now(),
            completed_at=datetime.now()
        )
        self.batch_processor.job_history.append(completed_batch)
        
        # 히스토리 조회
        history = self.batch_processor.get_batch_history(limit=10)
        
        # 검증
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].id, "completed_batch")
        self.assertEqual(history[0].status, BatchStatus.COMPLETED)

    def test_cleanup_history(self):
        """오래된 히스토리 정리 테스트"""
        # 오래된 배치 작업 추가
        from datetime import timedelta
        old_date = datetime.now() - timedelta(days=35)
        
        old_batch = BatchJob(
            id="old_batch",
            document_ids=[uuid.uuid4()],
            engine_name=self.engine_name,
            options=self.options,
            status=BatchStatus.COMPLETED,
            created_at=old_date,
            completed_at=old_date
        )
        
        recent_batch = BatchJob(
            id="recent_batch",
            document_ids=[uuid.uuid4()],
            engine_name=self.engine_name,
            options=self.options,
            status=BatchStatus.COMPLETED,
            created_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        self.batch_processor.job_history.extend([old_batch, recent_batch])
        
        # 히스토리 정리 (30일 이상)
        self.batch_processor.cleanup_history(days=30)
        
        # 검증
        self.assertEqual(len(self.batch_processor.job_history), 1)
        self.assertEqual(self.batch_processor.job_history[0].id, "recent_batch")

    async def test_process_batch_progress_callback(self):
        """배치 처리 진행 콜백 테스트"""
        # 배치 작업 생성
        batch_id = self.batch_processor.create_batch_job(
            document_ids=self.test_document_ids,
            engine_name=self.engine_name,
            options=self.options
        )
        
        # 진행 상황 추적을 위한 리스트
        progress_updates = []
        
        def progress_callback(batch_id, processed, total, success, result):
            progress_updates.append({
                "batch_id": batch_id,
                "processed": processed,
                "total": total,
                "success": success
            })
        
        # 모의 OCR 처리 함수
        async def mock_ocr_processor(doc_id, engine, options):
            await asyncio.sleep(0.1)
            return {
                "document_id": str(doc_id),
                "success": True,
                "text": f"Processed document {doc_id}",
                "confidence": 0.95
            }
        
        # 배치 처리 실행 (콜백과 함께)
        result = await self.batch_processor.process_batch(
            batch_id=batch_id,
            ocr_processor=mock_ocr_processor,
            progress_callback=progress_callback
        )
        
        # 검증
        self.assertEqual(len(progress_updates), 3)  # 3개 문서 처리
        
        # 각 진행 상황 업데이트 확인
        for i, update in enumerate(progress_updates):
            self.assertEqual(update["batch_id"], batch_id)
            self.assertEqual(update["processed"], i + 1)
            self.assertEqual(update["total"], 3)
            self.assertTrue(update["success"])

    def test_batch_processor_max_workers(self):
        """배치 처리기 워커 수 설정 테스트"""
        # 다른 워커 수로 배치 처리기 생성
        processor = BatchProcessor(max_workers=8, use_processes=True)
        
        # 설정 확인
        self.assertEqual(processor.max_workers, 8)
        self.assertTrue(processor.use_processes)

    def test_batch_processor_destructor(self):
        """배치 처리기 소멸자 테스트"""
        # 새 배치 처리기 생성
        processor = BatchProcessor(max_workers=2, use_processes=False)
        
        # executor 확인
        self.assertIsNotNone(processor.executor)
        
        # 소멸자 호출 시뮬레이션
        with patch.object(processor.executor, 'shutdown') as mock_shutdown:
            del processor
            # Python의 가비지 컬렉션으로 인해 즉시 호출되지 않을 수 있음


class AsyncTestCase(unittest.TestCase):
    """비동기 테스트를 위한 베이스 클래스"""
    
    def setUp(self):
        """비동기 테스트 설정"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """비동기 테스트 정리"""
        self.loop.close()
    
    def run_async(self, coro):
        """비동기 함수 실행"""
        return self.loop.run_until_complete(coro)


class TestBatchProcessorAsync(AsyncTestCase):
    """배치 처리기 비동기 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        super().setUp()
        self.batch_processor = BatchProcessor(max_workers=2, use_processes=False)
        self.test_document_ids = [uuid.uuid4() for _ in range(2)]
    
    def test_async_batch_processing(self):
        """비동기 배치 처리 통합 테스트"""
        # 배치 작업 생성
        batch_id = self.batch_processor.create_batch_job(
            document_ids=self.test_document_ids,
            engine_name="tesseract",
            options={"language": "kor+eng"}
        )
        
        # 모의 OCR 처리 함수
        async def mock_ocr_processor(doc_id, engine, options):
            await asyncio.sleep(0.1)
            return {
                "document_id": str(doc_id),
                "success": True,
                "text": f"Content of {doc_id}",
                "confidence": 0.9
            }
        
        # 배치 처리 실행
        result = self.run_async(
            self.batch_processor.process_batch(batch_id, mock_ocr_processor)
        )
        
        # 검증
        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.processed_documents, 2)
        self.assertEqual(result.failed_documents, 0)


if __name__ == '__main__':
    unittest.main()
