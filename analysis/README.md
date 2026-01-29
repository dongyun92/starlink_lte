# 🛰️ 통신 품질 분석 시스템

비행 데이터(ULG) + LTE 통신 품질 + Starlink 통신 품질을 병합하여 분석하는 종합 시스템

## ✨ 주요 기능

### 1. 📊 데이터 통합 분석
- **ULG 비행 로그**: PX4 비행 로그에서 GPS 좌표 및 비행 정보 추출
- **LTE 품질 데이터**: RSSI, RSRP, RSRQ, SINR 등 37개 통신 품질 메트릭
- **Starlink 품질 데이터**: 지연시간, 다운로드/업로드 속도, SNR 등 69개 메트릭
- **시간 동기화**: 타임스탬프 기반 정확한 데이터 병합

### 2. 🗺️ 인터랙티브 히트맵
- **LTE 품질 히트맵**: RSSI 기반 신호 강도 시각화
- **Starlink 품질 히트맵**: 레이턴시 기반 통신 품질 시각화
- **통합 지도**: 비행 경로 + 마커 클러스터 + 상세 정보
- **Folium 기반**: 확대/축소, 팬 가능한 인터랙티브 지도

### 3. 📄 자동 보고서 생성
- **전문적인 PDF 보고서**: 4페이지 분량의 종합 분석 리포트
- **통계 차트**: 시계열 분석, 히스토그램, 박스플롯
- **품질 등급 분류**: Excellent / Good / Fair 기준
- **권장사항 제공**: 데이터 기반 네트워크 선택 가이드

### 4. 🌐 웹 대시보드
- **Flask 기반**: 로컬 웹 서버로 모든 결과물 통합 관리
- **실시간 통계**: 커버리지, 평균 품질 지표 실시간 표시
- **파일 다운로드**: CSV, PDF, HTML 파일 다운로드 지원
- **반응형 UI**: 모바일/태블릿/데스크탑 지원

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 활성화
source analysis_env/bin/activate

# 필수 라이브러리 설치 (이미 설치됨)
# pip install pyulog pandas folium plotly matplotlib seaborn scipy
```

### 2. 데이터 분석 실행

```bash
# 단계 1: ULG + LTE + Starlink 데이터 병합
python analysis/flight_data_analyzer.py

# 단계 2: 인터랙티브 히트맵 생성
python analysis/quality_heatmap.py

# 단계 3: PDF 보고서 생성
python analysis/quality_report_generator.py

# 단계 4: 웹 대시보드 시작
python analysis/web_dashboard.py
```

### 3. 결과 확인

```bash
# 웹 브라우저에서 접속
http://localhost:5000
```

## 📁 파일 구조

```
analysis/
├── flight_data_analyzer.py          # 데이터 병합 분석기
├── quality_heatmap.py                # 히트맵 생성기
├── quality_report_generator.py      # PDF 보고서 생성기
├── web_dashboard.py                 # 웹 대시보드 서버
├── README.md                        # 이 파일
│
├── merged_flight_data.csv           # 🔹 병합된 데이터
├── lte_quality_heatmap.html         # 🗺️ LTE 히트맵
├── starlink_quality_heatmap.html    # 🛰️ Starlink 히트맵
├── combined_quality_map.html        # 🌍 통합 지도
└── communication_quality_report.pdf # 📄 PDF 보고서
```

## 📊 분석 결과 예시

### 비행 데이터 통계
```
Duration: 398.59 seconds (~6.6 minutes)
Total points: 2,620
Distance: 5.758 km
```

### LTE 품질 통계
```
Coverage: 100.0%
RSSI: -76.5 dBm (± 2.7)
RSRP: -102.3 dBm (± 3.6)
SINR: 17.4 dB (± 2.5)
```

### Starlink 품질 통계
```
Coverage: 53.9%
Latency: 68.4 ms (± 15.9)
Download: 24.7 Mbps (± 76.2)
Upload: 4.4 Mbps (± 12.9)
```

## 🔧 커스터마이징

### 다른 비행 로그 분석

`flight_data_analyzer.py` 파일의 `main()` 함수에서 경로 수정:

```python
def main():
    # 경로 설정 (프로젝트 루트 기준)
    base_dir = Path(__file__).parent.parent
    ulg_path = base_dir / "resource/[YOUR_FLIGHT_LOG].ulg"
    lte_dir = base_dir / "resource"
    starlink_dir = base_dir / "resource"
```

### 시간 윈도우 조정

데이터 병합 시 매칭 시간 윈도우 변경:

```python
analyzer.merge_data(time_window=0.5)  # 0.5초 윈도우 (기본값)
```

## 🎯 기술 스택

- **Python 3.13**: 주 프로그래밍 언어
- **pyulog**: ULG 비행 로그 파싱
- **pandas**: 데이터 처리 및 병합
- **folium**: 인터랙티브 지도 시각화
- **matplotlib/seaborn**: 통계 차트 생성
- **Flask**: 웹 대시보드 서버

## 📈 성능

- **데이터 병합 속도**: ~2초 (2,620 포인트)
- **히트맵 생성**: ~3초 (3개 지도)
- **PDF 보고서 생성**: ~2초 (4페이지)
- **메모리 사용량**: ~200MB

## 🔍 상세 분석 내용

### LTE 품질 메트릭
- **RSSI**: 수신 신호 강도 (-113 ~ -51 dBm)
- **RSRP**: 참조 신호 수신 전력
- **RSRQ**: 참조 신호 수신 품질
- **SINR**: 신호 대 간섭 비율 (높을수록 좋음)

### Starlink 품질 메트릭
- **Latency**: 핑 응답 시간 (ms, 낮을수록 좋음)
- **Download**: 다운로드 속도 (Mbps)
- **Upload**: 업로드 속도 (Mbps)
- **SNR**: 신호 대 잡음비

### 품질 등급 기준

#### LTE (RSSI 기준)
- **Excellent**: > -70 dBm (녹색)
- **Good**: -70 ~ -85 dBm (주황색)
- **Fair**: < -85 dBm (빨간색)

#### Starlink (Latency 기준)
- **Excellent**: < 40 ms (녹색)
- **Good**: 40 ~ 100 ms (주황색)
- **Fair**: > 100 ms (빨간색)

## 🚧 문제 해결

### ULG 파일을 찾을 수 없음
```bash
# 경로 확인
ls -la resource/*.ulg
```

### 타임스탬프 동기화 실패
- ULG 타임스탬프와 CSV 타임스탬프의 시작 시간을 확인
- `find_time_offset()` 함수에서 오프셋 계산 로그 확인

### 웹 대시보드 접속 불가
```bash
# 포트 5000이 사용 중인지 확인
lsof -i :5000

# 다른 포트 사용
# web_dashboard.py에서 app.run(port=5001) 수정
```

## 📝 라이선스

MIT License

## 👨‍💻 개발자

Flight Data Analysis System
Developed for Starlink + LTE Communication Quality Analysis

## 🔗 관련 문서

- [프로젝트 메인 README](../README.md)
- [ULG 파일 형식 문서](https://docs.px4.io/main/en/dev_log/ulog_file_format.html)
- [Folium 문서](https://python-visualization.github.io/folium/)
