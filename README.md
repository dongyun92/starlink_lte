# Starlink 미니 데이터 모니터링 도구

스타링크 미니의 통신 품질을 모니터링하고 CSV 파일로 저장하는 Python 도구입니다.

## 기능

- 실시간 스타링크 상태 데이터 수집
- CSV 파일 자동 저장
- 지속적 모니터링 (사용자 정의 간격)
- 상세한 통신 품질 지표 추적

## 수집되는 데이터

### 기본 상태 정보
- `timestamp`: 데이터 수집 시간
- `uptime_s`: 디바이스 가동 시간 (초)
- `hardware_version`: 하드웨어 버전
- `software_version`: 소프트웨어 버전
- `state`: 디바이스 상태

### 네트워크 성능
- `pop_ping_drop_rate`: 핑 패킷 손실률
- `pop_ping_latency_ms`: 핑 지연시간 (밀리초)
- `downlink_throughput_bps`: 다운로드 처리량 (bps)
- `uplink_throughput_bps`: 업로드 처리량 (bps)
- `snr`: 신호 대 잡음 비율

### 장애물 및 위성 연결
- `obstruction_fraction`: 장애물로 인한 신호 차단 비율
- `obstruction_avg_duration_s`: 평균 장애물 차단 지속시간
- `seconds_obstructed`: 현재 차단된 시간
- `gps_sats`: GPS 위성 수
- `gps_valid`: GPS 신호 유효성

### 경고 및 알림
- `alerts_thermal_throttle`: 열 제한 경고
- `alerts_thermal_shutdown`: 열 차단 경고
- `alerts_mast_not_near_vertical`: 안테나 기울기 경고
- `alerts_unexpected_location`: 예상치 못한 위치 경고
- `alerts_slow_ethernet_speeds`: 느린 이더넷 속도 경고

### 15분 평균 통계
- `avg_downlink_throughput_bps`: 평균 다운로드 처리량
- `avg_uplink_throughput_bps`: 평균 업로드 처리량
- `avg_pop_ping_drop_rate`: 평균 핑 손실률
- `avg_pop_ping_latency_ms`: 평균 핑 지연시간
- `avg_snr`: 평균 신호 대 잡음 비율

## 설치

1. 이 저장소를 클론하거나 다운로드합니다:
```bash
git clone <저장소 URL>
cd starlink-monitor
```

2. 설치 스크립트를 실행합니다:
```bash
./install.sh
```

## 사용법

### 1. 가상환경 활성화
```bash
source starlink_env/bin/activate
```

### 2. 한 번만 데이터 수집
```bash
python starlink_monitor.py --once
```

### 3. 지속적 모니터링 (기본 5분 간격)
```bash
python starlink_monitor.py
```

### 4. 사용자 정의 간격으로 모니터링 (예: 10분)
```bash
python starlink_monitor.py --interval 10
```

### 5. 사용자 정의 IP 및 CSV 파일명
```bash
python starlink_monitor.py --ip 192.168.100.1 --csv my_starlink_data.csv
```

## 명령행 옵션

- `--ip`: 스타링크 디바이스 IP 주소 (기본값: 192.168.100.1)
- `--csv`: CSV 파일명 (기본값: starlink_data_YYYYMMDD.csv)
- `--interval`: 데이터 수집 간격 (분, 기본값: 5)
- `--once`: 한 번만 수집하고 종료

## 예시 CSV 출력

```csv
timestamp,uptime_s,hardware_version,software_version,state,pop_ping_drop_rate,pop_ping_latency_ms,downlink_throughput_bps,uplink_throughput_bps,snr,obstruction_fraction,gps_sats
2024-01-15T10:30:00,3600,rev1_proto1,2023.01.01.mr12345,CONNECTED,0.01,35.2,15000000,2000000,8.5,0.02,12
```

## 문제 해결

### 연결 오류
- 스타링크 디바이스가 192.168.100.1에서 접근 가능한지 확인
- 방화벽이 9200 포트를 차단하지 않는지 확인

### gRPC 오류
- `starlink-grpc` 패키지가 올바르게 설치되었는지 확인
- Python 3.7 이상이 설치되어 있는지 확인

### 로그 파일
- `starlink_monitor.log` 파일에서 상세한 오류 정보 확인 가능

## 로그 및 출력 파일

- **로그 파일**: `starlink_monitor.log` - 실행 과정 및 오류 기록
- **CSV 파일**: `starlink_data_YYYYMMDD.csv` - 수집된 데이터

## 🌐 웹 대시보드

스타링크 데이터를 실시간으로 볼 수 있는 웹 대시보드가 포함되어 있습니다.

### 웹 대시보드 실행

1. 가상환경을 활성화합니다:
```bash
source starlink_env/bin/activate
```

2. 웹 대시보드를 시작합니다:
```bash
./run_dashboard.sh
```

3. 브라우저에서 접속:
```
http://localhost:5000
```

### 웹 대시보드 기능

- **실시간 모니터링**: 30초마다 자동 업데이트
- **핵심 지표 카드**: SNR, 다운/업로드 속도, 핑 지연시간, 패킷 손실률, 장애물 차단률
- **실시간 차트**: 
  - 네트워크 처리량 그래프 (다운로드/업로드)
  - 신호 품질 그래프 (SNR/핑 지연시간)
- **시스템 정보**: 하드웨어/소프트웨어 버전, 가동시간, GPS 정보
- **경고 알림**: 열 제한, 안테나 기울기, 이더넷 속도 등
- **WebSocket 실시간 통신**: 페이지 새로고침 없이 자동 업데이트

### 스크린샷

대시보드는 다음과 같은 정보를 실시간으로 표시합니다:

- 📊 **상태 카드**: 주요 지표를 한눈에 확인
- 📈 **실시간 차트**: 시간에 따른 성능 변화 추적
- ⚠️ **경고 시스템**: 문제 발생시 즉시 알림
- 📱 **반응형 디자인**: 모바일, 태블릿, 데스크톱 지원

## 라이선스

MIT License