# 서버 관리 스크립트 사용법

## 개요
Starlink Flight Analysis 3D Visualization 프로젝트의 서버를 관리하는 스크립트입니다.

## 포트 구성
- **Frontend (Vite)**: `5173`
- **Backend (Flask)**: `5002`
- **Redis**: `6379`

---

## 스크립트 목록

### 1. `./status.sh` - 서버 상태 확인
현재 실행 중인 서버 상태를 확인합니다.

```bash
./status.sh
```

**출력 예시:**
```
📊 Backend (Flask - Port 5002):
  ✅ Running (PID: 12345)
  📍 URL: http://localhost:5002

🎨 Frontend (Vite - Port 5173):
  ✅ Running (PID: 67890)
  📍 URL: http://localhost:5173

💾 Redis (Port 6379):
  ✅ Running (PID: 11274)
  🔑 Cached keys: 12
```

---

### 2. `./start.sh` - 서버 시작
모든 서버를 시작합니다. (기존 프로세스가 있으면 경고)

```bash
./start.sh
```

**기능:**
- Redis 캐시 초기화
- Flask 백엔드 시작 (port 5002)
- Vite 프론트엔드 시작 (port 5173)
- 시작 검증 및 로그 출력

**주의:** 이미 실행 중인 경우 오류 발생

---

### 3. `./stop.sh` - 서버 중지
모든 서버를 안전하게 중지합니다.

```bash
./stop.sh
```

**기능:**
- Vite 프로세스 종료
- Flask 프로세스 종료
- 포트 정리 (5002, 5173)

---

### 4. `./restart.sh` - 서버 재시작 ⭐ 권장
**가장 자주 사용하는 스크립트**

모든 서버를 강제로 중지하고 다시 시작합니다.

```bash
./restart.sh
```

**기능:**
- 기존 프로세스 강제 종료
- Redis 캐시 초기화
- Python 캐시 정리 (`__pycache__`)
- Flask 백엔드 재시작
- Vite 프론트엔드 재시작
- 시작 검증 및 로그 출력

**언제 사용하나요?**
- ✅ 코드 변경 후 반영할 때
- ✅ 포트 충돌 발생 시
- ✅ 서버가 응답하지 않을 때
- ✅ 캐시를 초기화하고 싶을 때

---

## 일반적인 사용 시나리오

### 시나리오 1: 처음 시작
```bash
./status.sh    # 현재 상태 확인
./start.sh     # 서버 시작
```

### 시나리오 2: 코드 수정 후
```bash
./restart.sh   # 변경사항 반영을 위해 재시작
```

### 시나리오 3: 작업 종료
```bash
./stop.sh      # 모든 서버 중지
```

### 시나리오 4: 포트 충돌 해결
```bash
./restart.sh   # 강제 종료 후 재시작
```

### 시나리오 5: 상태 확인만
```bash
./status.sh    # 서버 상태만 확인
```

---

## 로그 확인

### Flask 백엔드 로그
```bash
tail -f /Users/dykim/dev/starlink/analysis/flask.log
```

### Vite 프론트엔드 로그
```bash
tail -f /tmp/vite.log
```

### 실시간 로그 모니터링 (두 개 동시)
```bash
# 터미널 1
tail -f /Users/dykim/dev/starlink/analysis/flask.log

# 터미널 2
tail -f /tmp/vite.log
```

---

## 문제 해결

### 1. "Address already in use" 오류
**원인:** 포트가 이미 사용 중
**해결:** `./restart.sh` 실행

### 2. Flask가 시작되지 않음
**확인:**
```bash
tail -20 /Users/dykim/dev/starlink/analysis/flask.log
```
**해결:** 로그에서 오류 확인 후 수정

### 3. Vite가 시작되지 않음
**확인:**
```bash
tail -20 /tmp/vite.log
```
**해결:**
- `cd frontend && npm install` 실행
- 로그에서 오류 확인

### 4. Redis 연결 안 됨
**확인:**
```bash
redis-cli ping
```
**해결:**
```bash
brew services start redis
```

---

## 베스트 프랙티스

### ✅ 권장사항
1. **항상 restart.sh 사용**: 수동으로 서버를 시작하지 말고 스크립트 사용
2. **코드 변경 후 재시작**: Python/TypeScript 코드 변경 시 `./restart.sh` 실행
3. **로그 모니터링**: 문제 발생 시 로그를 먼저 확인
4. **상태 확인 습관화**: 작업 전 `./status.sh`로 상태 확인

### ❌ 피해야 할 것
1. **수동 프로세스 시작**: `python3 app.py`, `npm run dev` 직접 실행 금지
2. **포트 변경**: 항상 5002(Flask), 5173(Vite) 사용
3. **강제 종료 남용**: 정상적인 중지는 `./stop.sh` 사용
4. **캐시 무시**: 문제 발생 시 캐시 초기화 필요 (`./restart.sh`)

---

## 접속 URL

| 서비스 | URL | 포트 |
|--------|-----|------|
| Frontend | http://localhost:5173 | 5173 |
| Backend API | http://localhost:5002 | 5002 |
| Redis | localhost:6379 | 6379 |

---

## 스크립트 순서도

```
서버 상태 확인
    ↓
./status.sh
    ↓
전체 중지됨? → ./start.sh → 시작 완료
    ↓
일부 실행중? → ./restart.sh → 재시작 완료
    ↓
전체 실행중? → 작업 진행
    ↓
코드 수정 → ./restart.sh → 변경사항 반영
    ↓
작업 종료 → ./stop.sh → 서버 중지
```

---

## 개발 워크플로우

```bash
# 1. 아침: 작업 시작
./status.sh      # 상태 확인
./start.sh       # 서버 시작

# 2. 개발 중: 코드 수정
# (파일 수정...)
./restart.sh     # 변경사항 반영

# 3. 저녁: 작업 종료
./stop.sh        # 서버 중지
```

---

**💡 TIP**: 가장 자주 사용하는 명령어는 `./restart.sh` 입니다!
