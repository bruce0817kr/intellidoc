#!/usr/bin/env python3
"""
IntelliDoc 포트 충돌 해결 및 자동 포트 할당 스크립트
포트 매니저는 Docker 배포 시 포트 충돌을 자동으로 해결합니다.

use MCP: context7, Github, Sequential Thinking, Task Manager, Memory Bank 또는 Graph Memory
"""

import socket
import subprocess
import json
import yaml
import re
import os
import shutil
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class PortManager:
    """포트 충돌 해결 및 자동 할당 매니저"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.default_ports = {
            'frontend': 80,      # Nginx 프론트엔드
            'backend': 8000,     # FastAPI 백엔드
            'postgres': 5432,    # PostgreSQL
            'redis': 6379,       # Redis
            'prometheus': 9090,  # Prometheus (선택사항)
            'grafana': 3000      # Grafana (선택사항)
        }
        self.allocated_ports = {}
        self.port_range_start = 3000
        self.port_range_end = 9999
        
    def is_port_available(self, port: int, host: str = 'localhost') -> bool:
        """포트가 사용 가능한지 확인"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # 0이면 연결 성공(사용 중), 0이 아니면 사용 가능
        except Exception as e:
            print(f"⚠️ 포트 {port} 확인 중 오류: {e}")
            return False
            
    def find_available_port(self, start_port: int, max_attempts: int = 100) -> int:
        """사용 가능한 포트 찾기"""
        for i in range(max_attempts):
            port = start_port + i
            if port > self.port_range_end:
                break
            if self.is_port_available(port):
                return port
        raise Exception(f"포트 {start_port}부터 {max_attempts}개 범위에서 사용 가능한 포트를 찾을 수 없습니다.")
        
    def get_used_ports(self) -> List[int]:
        """현재 사용 중인 포트 목록 가져오기"""
        used_ports = []
        try:
            # Windows netstat 명령어 사용
            if os.name == 'nt':
                result = subprocess.run(['netstat', '-an'], 
                                      capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'LISTENING' in line or 'ESTABLISHED' in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                addr = parts[1]
                                if ':' in addr:
                                    try:
                                        port = int(addr.split(':')[-1])
                                        if self.port_range_start <= port <= self.port_range_end:
                                            used_ports.append(port)
                                    except ValueError:
                                        continue
            else:
                # Linux/macOS ss 또는 netstat 명령어 사용
                try:
                    result = subprocess.run(['ss', '-tuln'], 
                                          capture_output=True, text=True)
                except FileNotFoundError:
                    result = subprocess.run(['netstat', '-tuln'], 
                                          capture_output=True, text=True)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if ':' in line:
                            parts = line.split()
                            for part in parts:
                                if ':' in part and part.count(':') >= 1:
                                    try:
                                        port = int(part.split(':')[-1])
                                        if self.port_range_start <= port <= self.port_range_end:
                                            used_ports.append(port)
                                    except (ValueError, IndexError):
                                        continue
                        
        except Exception as e:
            print(f"⚠️ 사용 중인 포트 조회 중 오류: {e}")
            
        return list(set(used_ports))
        
    def get_docker_used_ports(self) -> List[int]:
        """Docker 컨테이너가 사용 중인 포트 목록"""
        used_ports = []
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'table {{.Ports}}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n')[1:]:  # 헤더 제외
                    if line.strip():
                        # 포트 매핑 정보에서 호스트 포트 추출
                        port_mappings = re.findall(r'(\d+):\d+', line)
                        for port_str in port_mappings:
                            try:
                                port = int(port_str)
                                if self.port_range_start <= port <= self.port_range_end:
                                    used_ports.append(port)
                            except ValueError:
                                continue
        except Exception as e:
            print(f"⚠️ Docker 포트 조회 중 오류: {e}")
            
        return used_ports
        
    def allocate_ports(self) -> Dict[str, int]:
        """모든 서비스에 대해 사용 가능한 포트 할당"""
        system_used_ports = self.get_used_ports()
        docker_used_ports = self.get_docker_used_ports()
        all_used_ports = list(set(system_used_ports + docker_used_ports))
        
        print(f"🔍 현재 사용 중인 포트: {sorted(all_used_ports)}")
        
        for service, default_port in self.default_ports.items():
            if self.is_port_available(default_port):
                self.allocated_ports[service] = default_port
                print(f"✅ {service}: {default_port} (기본 포트 사용)")
            else:
                try:
                    new_port = self.find_available_port(default_port + 1)
                    self.allocated_ports[service] = new_port
                    print(f"🔄 {service}: {default_port} → {new_port} (포트 변경)")
                except Exception as e:
                    print(f"❌ {service}: 사용 가능한 포트를 찾을 수 없습니다 - {e}")
                    raise
                    
        return self.allocated_ports
        
    def backup_file(self, file_path: Path) -> Path:
        """파일 백업 생성"""
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        if file_path.exists():
            shutil.copy2(file_path, backup_path)
            print(f"📄 백업 생성: {backup_path}")
        return backup_path
        
    def update_docker_compose(self, ports: Dict[str, int]):
        """Docker Compose 파일의 포트 설정 업데이트"""
        compose_file = self.project_root / "docker-compose.yml"
        
        if not compose_file.exists():
            print(f"⚠️ docker-compose.yml 파일을 찾을 수 없습니다: {compose_file}")
            return
            
        try:
            # 백업 생성
            self.backup_file(compose_file)
            
            # YAML 파일 읽기
            with open(compose_file, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f)
            
            # 서비스별 포트 업데이트
            if 'services' in compose_data:
                # Frontend 포트 업데이트
                if 'frontend' in compose_data['services'] and 'frontend' in ports:
                    compose_data['services']['frontend']['ports'] = [f"{ports['frontend']}:80"]
                    
                # Backend 포트 업데이트  
                if 'backend' in compose_data['services'] and 'backend' in ports:
                    compose_data['services']['backend']['ports'] = [f"{ports['backend']}:8000"]
                    
                # PostgreSQL 포트 업데이트
                if 'postgres' in compose_data['services'] and 'postgres' in ports:
                    compose_data['services']['postgres']['ports'] = [f"{ports['postgres']}:5432"]
                    
                # Redis 포트 업데이트
                if 'redis' in compose_data['services'] and 'redis' in ports:
                    compose_data['services']['redis']['ports'] = [f"{ports['redis']}:6379"]
                    
                # Prometheus 포트 업데이트 (선택사항)
                if 'prometheus' in compose_data['services'] and 'prometheus' in ports:
                    compose_data['services']['prometheus']['ports'] = [f"{ports['prometheus']}:9090"]
                    
                # Grafana 포트 업데이트 (선택사항)
                if 'grafana' in compose_data['services'] and 'grafana' in ports:
                    compose_data['services']['grafana']['ports'] = [f"{ports['grafana']}:3000"]
            
            # 업데이트된 내용을 파일에 저장
            with open(compose_file, 'w', encoding='utf-8') as f:
                yaml.dump(compose_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
            print(f"✅ docker-compose.yml 업데이트 완료")
            
        except Exception as e:
            print(f"❌ docker-compose.yml 업데이트 실패: {e}")
            # 백업에서 복원
            backup_file = compose_file.with_suffix('.yml.bak')
            if backup_file.exists():
                shutil.copy2(backup_file, compose_file)
                print(f"🔄 백업에서 복원: {compose_file}")
            
    def update_env_file(self, ports: Dict[str, int]):
        """환경변수 파일의 URL 업데이트"""
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            print(f"⚠️ .env 파일을 찾을 수 없습니다: {env_file}")
            return
            
        try:
            # 백업 생성
            self.backup_file(env_file)
            
            # .env 파일 읽기
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # URL 관련 환경변수 업데이트
            if 'frontend' in ports:
                content = re.sub(
                    r'FRONTEND_URL=.*',
                    f'FRONTEND_URL=http://localhost:{ports["frontend"]}',
                    content
                )
                content = re.sub(
                    r'ALLOWED_ORIGINS=.*',
                    f'ALLOWED_ORIGINS=http://localhost:{ports["frontend"]},http://localhost,http://127.0.0.1',
                    content
                )
                
            if 'backend' in ports:
                content = re.sub(
                    r'INTERNAL_API_URL=.*',
                    f'INTERNAL_API_URL=http://localhost:{ports["backend"]}',
                    content
                )
                
            # 새로운 환경변수가 없으면 추가
            if 'FRONTEND_URL=' not in content and 'frontend' in ports:
                content += f'\nFRONTEND_URL=http://localhost:{ports["frontend"]}'
                
            if 'INTERNAL_API_URL=' not in content and 'backend' in ports:
                content += f'\nINTERNAL_API_URL=http://localhost:{ports["backend"]}'
            
            # 업데이트된 내용을 파일에 저장
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ .env 파일 업데이트 완료")
            
        except Exception as e:
            print(f"❌ .env 파일 업데이트 실패: {e}")
            # 백업에서 복원
            backup_file = env_file.with_suffix('.bak')
            if backup_file.exists():
                shutil.copy2(backup_file, env_file)
                print(f"🔄 백업에서 복원: {env_file}")
                
    def stop_conflicting_containers(self):
        """IntelliDoc 관련 기존 컨테이너 정리"""
        try:
            print("🧹 기존 IntelliDoc 컨테이너 정리 중...")
            
            # IntelliDoc 관련 컨테이너 이름 패턴
            container_patterns = [
                'intellidoc-',
                'intellidoc_',
                'backend',
                'frontend', 
                'worker',
                'postgres',
                'redis'
            ]
            
            # 실행 중인 컨테이너 조회
            result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')
                stopped_containers = []
                
                for container in containers:
                    if container and any(pattern in container.lower() for pattern in container_patterns):
                        try:
                            # 컨테이너 중지 및 제거
                            subprocess.run(['docker', 'stop', container], 
                                         capture_output=True, text=True)
                            subprocess.run(['docker', 'rm', container], 
                                         capture_output=True, text=True)
                            stopped_containers.append(container)
                        except Exception as e:
                            print(f"⚠️ 컨테이너 {container} 정리 실패: {e}")
                
                if stopped_containers:
                    print(f"✅ 정리된 컨테이너: {', '.join(stopped_containers)}")
                else:
                    print("ℹ️ 정리할 컨테이너가 없습니다.")
                    
        except Exception as e:
            print(f"⚠️ 컨테이너 정리 중 오류: {e}")

def main():
    """메인 함수"""
    print("🔧 IntelliDoc 포트 충돌 해결 및 자동 할당 시작")
    print("=" * 60)
    print("use MCP: context7, Github, Sequential Thinking, Task Manager, Memory Bank 또는 Graph Memory")
    print("=" * 60)
    
    manager = PortManager()
    
    # 1. 기존 컨테이너 정리
    manager.stop_conflicting_containers()
    
    # 2. 포트 할당
    print("\n🔍 포트 할당 분석 중...")
    ports = manager.allocate_ports()
    
    # 3. 설정 파일 업데이트
    print("\n📝 설정 파일 업데이트 중...")
    manager.update_docker_compose(ports)
    manager.update_env_file(ports)
    
    # 4. 결과 출력
    print("\n📊 할당된 포트 정보")
    print("=" * 40)
    for service, port in ports.items():
        status = "✅ 사용 가능" if manager.is_port_available(port) else "⚠️ 확인 필요"
        print(f"{service:12} : {port:5} {status}")
        
    print(f"\n🌐 서비스 접속 URL")
    print("=" * 40)
    if 'frontend' in ports:
        print(f"웹 애플리케이션  : http://localhost:{ports['frontend']}")
    if 'backend' in ports:
        print(f"API 서버        : http://localhost:{ports['backend']}")
        print(f"API 문서        : http://localhost:{ports['backend']}/docs")
    if 'postgres' in ports:
        print(f"PostgreSQL      : postgresql://localhost:{ports['postgres']}")
    if 'redis' in ports:
        print(f"Redis           : redis://localhost:{ports['redis']}")
    if 'grafana' in ports:
        print(f"Grafana         : http://localhost:{ports['grafana']}")
    if 'prometheus' in ports:
        print(f"Prometheus      : http://localhost:{ports['prometheus']}")
    
    # 5. 포트 정보를 파일로 저장
    allocated_ports_file = Path("allocated_ports.json")
    with open(allocated_ports_file, 'w', encoding='utf-8') as f:
        json.dump(ports, f, indent=2, ensure_ascii=False)
        
    print(f"\n💾 포트 정보가 {allocated_ports_file}에 저장되었습니다.")
    print("\n🚀 다음 명령으로 서비스를 시작할 수 있습니다:")
    print("   docker-compose up -d")
    print("\n📋 문제 발생 시:")
    print("   - .bak 확장자 파일들이 백업본입니다")
    print("   - docker-compose down -v 로 완전 정리 후 재시작하세요")

if __name__ == "__main__":
    main()
