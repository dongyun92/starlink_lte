// 파일 업로드 및 세션 관리 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnLoading = document.getElementById('btnLoading');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const uploadResult = document.getElementById('uploadResult');

    // 드래그 앤 드롭 설정
    setupDragAndDrop('flightLogZone', 'flightLog');
    setupDragAndDrop('lteDataZone', 'lteData');
    setupDragAndDrop('starlinkDataZone', 'starlinkData');

    // 파일 입력 이벤트
    document.getElementById('flightLog').addEventListener('change', function(e) {
        updateFileName('flightLogZone', e.target.files);
    });
    document.getElementById('lteData').addEventListener('change', function(e) {
        updateFileName('lteDataZone', e.target.files);
    });
    document.getElementById('starlinkData').addEventListener('change', function(e) {
        updateFileName('starlinkDataZone', e.target.files);
    });

    // 폼 제출
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        // 파일 검증 - 비행 로그는 필수, LTE/Starlink는 선택
        const flightLogs = document.getElementById('flightLog').files;
        const lteDataFiles = document.getElementById('lteData').files;
        const starlinkDataFiles = document.getElementById('starlinkData').files;

        if (flightLogs.length === 0) {
            showAlert('비행 로그(.ulg) 파일을 최소 1개 이상 선택해주세요.', 'error');
            return;
        }

        // FormData 생성 - 여러 파일 추가
        const formData = new FormData();

        // 비행 로그 파일들 추가
        for (let i = 0; i < flightLogs.length; i++) {
            formData.append('flight_log', flightLogs[i]);
        }

        // LTE 데이터 파일들 추가
        for (let i = 0; i < lteDataFiles.length; i++) {
            formData.append('lte_data', lteDataFiles[i]);
        }

        // Starlink 데이터 파일들 추가
        for (let i = 0; i < starlinkDataFiles.length; i++) {
            formData.append('starlink_data', starlinkDataFiles[i]);
        }

        // 메타데이터 추가
        const sessionName = document.getElementById('sessionName').value;
        if (sessionName) {
            formData.append('metadata', JSON.stringify({
                name: sessionName,
                date: new Date().toISOString()
            }));
        }

        // UI 업데이트
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        btnLoading.classList.remove('hidden');
        uploadProgress.classList.remove('hidden');
        uploadResult.classList.add('hidden');

        try {
            // 업로드 진행 상황 시뮬레이션
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 10;
                if (progress <= 90) {
                    updateProgress(progress);
                }
            }, 200);

            // API 호출
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            clearInterval(progressInterval);
            updateProgress(100);

            const data = await response.json();

            if (response.ok) {
                showAlert(`업로드 성공! 세션 ID: ${data.session_id}`, 'success');

                // 폼 초기화
                uploadForm.reset();
                document.querySelectorAll('.file-name').forEach(el => el.textContent = '');

                // 세션 목록 새로고침
                setTimeout(() => {
                    loadSessions();
                }, 1000);
            } else {
                showAlert(`업로드 실패: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showAlert(`업로드 중 오류 발생: ${error.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            btnLoading.classList.add('hidden');
            setTimeout(() => {
                uploadProgress.classList.add('hidden');
                progressFill.style.width = '0%';
            }, 2000);
        }
    });

    // 세션 목록 로드
    loadSessions();
});

function setupDragAndDrop(zoneId, inputId) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);

    zone.addEventListener('dragover', function(e) {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', function() {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', function(e) {
        e.preventDefault();
        zone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            input.files = files;
            updateFileName(zoneId, files);
        }
    });
}

function updateFileName(zoneId, files) {
    const zone = document.getElementById(zoneId);
    const nameElement = zone.querySelector('.file-name');

    if (files && files.length > 0) {
        if (files.length === 1) {
            nameElement.textContent = `✓ ${files[0].name} (${formatFileSize(files[0].size)})`;
        } else {
            const totalSize = Array.from(files).reduce((sum, f) => sum + f.size, 0);
            nameElement.textContent = `✓ ${files.length}개 파일 선택됨 (총 ${formatFileSize(totalSize)})`;
        }
    } else {
        nameElement.textContent = '';
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function updateProgress(percent) {
    document.getElementById('progressFill').style.width = percent + '%';
    document.getElementById('progressText').textContent = `파일 업로드 중... ${percent}%`;
}

function showAlert(message, type) {
    const uploadResult = document.getElementById('uploadResult');
    uploadResult.className = `alert alert-${type}`;
    uploadResult.textContent = message;
    uploadResult.classList.remove('hidden');
}

async function loadSessions() {
    const sessionsList = document.getElementById('sessionsList');

    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();

        if (data.sessions && data.sessions.length > 0) {
            sessionsList.innerHTML = data.sessions.map(session => `
                <div class="session-card">
                    <div class="session-info">
                        <h3>${session.name}</h3>
                        <p>생성 시간: ${new Date(session.created_at).toLocaleString('ko-KR')}</p>
                        <p>상태: <span class="session-status status-${session.status}">${getStatusText(session.status)}</span></p>
                        ${session.progress ? `<p>진행률: ${session.progress}%</p>` : ''}
                    </div>
                    <div class="session-actions">
                        ${session.status === 'completed' ?
                            `<a href="/session/${session.id}" class="btn-view">결과 보기</a>` :
                            `<button class="btn-view" onclick="checkStatus('${session.id}')">상태 확인</button>`
                        }
                        <button class="btn-delete" onclick="deleteSession('${session.id}')">삭제</button>
                    </div>
                </div>
            `).join('');
        } else {
            sessionsList.innerHTML = '<p class="loading">아직 분석 기록이 없습니다.</p>';
        }
    } catch (error) {
        console.error('Load sessions error:', error);
        sessionsList.innerHTML = '<p class="loading">세션 목록을 불러올 수 없습니다.</p>';
    }
}

function getStatusText(status) {
    const statusMap = {
        'pending': '대기 중',
        'uploaded': '업로드 완료',
        'processing': '분석 중',
        'completed': '완료',
        'failed': '실패'
    };
    return statusMap[status] || status;
}

async function checkStatus(sessionId) {
    try {
        const response = await fetch(`/api/session/${sessionId}/status`);
        const data = await response.json();

        alert(`세션 상태:\n상태: ${getStatusText(data.status)}\n진행률: ${data.progress}%\n현재 단계: ${data.current_step}`);

        if (data.status === 'completed') {
            window.location.href = `/session/${sessionId}`;
        }
    } catch (error) {
        alert('상태 확인 실패: ' + error.message);
    }
}

async function retryAnalysis(sessionId) {
    if (!confirm('이 세션을 재분석하시겠습니까? (한글 폰트가 적용된 차트가 생성됩니다)')) {
        return;
    }

    try {
        const response = await fetch(`/api/retry/${sessionId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('재분석 요청 실패');
        }

        const data = await response.json();
        alert(data.message || '재분석이 시작되었습니다. 완료되면 결과 페이지에서 확인하세요.');

        // Reload sessions list to show updated status
        loadSessions();
    } catch (error) {
        alert('재분석 실패: ' + error.message);
    }
}

async function deleteSession(sessionId) {
    if (!confirm('이 세션을 삭제하시겠습니까?')) {
        return;
    }

    try {
        const response = await fetch(`/api/session/${sessionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('세션이 삭제되었습니다.');
            loadSessions();
        } else {
            const data = await response.json();
            alert('삭제 실패: ' + data.error);
        }
    } catch (error) {
        alert('삭제 중 오류 발생: ' + error.message);
    }
}

// ===== 세션 필터링 기능 =====
let currentFilter = 'all';
let allSessions = [];

function filterSessions(filterType) {
    currentFilter = filterType;

    // 버튼 활성화 표시
    document.querySelectorAll('.btn-filter').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`filter-${filterType}`).classList.add('active');

    // 필터링된 세션 표시
    displayFilteredSessions();
}

function displayFilteredSessions() {
    const sessionsList = document.getElementById('sessionsList');

    let filteredSessions = allSessions;
    if (currentFilter !== 'all') {
        filteredSessions = allSessions.filter(session => session.status === currentFilter);
    }

    if (filteredSessions.length > 0) {
        sessionsList.innerHTML = filteredSessions.map(session => `
            <div class="session-card" data-session-id="${session.id}" data-status="${session.status}">
                ${compareMode ? `<input type="checkbox" class="session-checkbox" data-session-id="${session.id}">` : ''}
                <div class="session-info">
                    <h3>${session.name || `세션 ${session.id.substring(0, 8)}`}</h3>
                    <p>생성 시간: ${new Date(session.created_at).toLocaleString('ko-KR')}</p>
                    <p>상태: <span class="session-status status-${session.status}">${getStatusText(session.status)}</span></p>
                    ${session.progress ? `<p>진행률: ${session.progress}%</p>` : ''}
                    ${session.file_paths && session.file_paths.file_counts ?
                        `<p class="file-counts">📁 파일: ${session.file_paths.file_counts.flight_logs || 0}개 로그, ${session.file_paths.file_counts.lte_data || 0}개 LTE, ${session.file_paths.file_counts.starlink_data || 0}개 Starlink</p>` : ''}
                </div>
                <div class="session-actions">
                    ${session.status === 'completed' ?
                        `<a href="/session/${session.id}" class="btn-view">결과 보기</a>
                         <button class="btn-reanalyze" onclick="retryAnalysis('${session.id}')">🔄 재분석</button>` :
                        session.status === 'failed' ?
                        `<button class="btn-view" onclick="checkStatus('${session.id}')">상태 확인</button>
                         <button class="btn-reanalyze" onclick="retryAnalysis('${session.id}')">🔄 재분석</button>` :
                        `<button class="btn-view" onclick="checkStatus('${session.id}')">상태 확인</button>`
                    }
                    <button class="btn-delete" onclick="deleteSession('${session.id}')">삭제</button>
                </div>
            </div>
        `).join('');
    } else {
        sessionsList.innerHTML = `<p class="loading">${currentFilter === 'all' ? '분석 기록이 없습니다.' : `${getStatusText(currentFilter)} 세션이 없습니다.`}</p>`;
    }
}

// ===== 세션 비교 모드 =====
let compareMode = false;
let selectedSessions = [];

function toggleCompareMode() {
    compareMode = !compareMode;
    const compareBtn = document.getElementById('compareBtn');

    if (compareMode) {
        compareBtn.textContent = '비교 취소';
        compareBtn.classList.add('active');
        document.getElementById('compareActions')?.remove(); // 기존 버튼 제거

        // 비교 실행 버튼 추가
        const actionsDiv = document.createElement('div');
        actionsDiv.id = 'compareActions';
        actionsDiv.style.marginTop = '15px';
        actionsDiv.innerHTML = `
            <button class="btn-primary" onclick="compareSelectedSessions()" style="margin-right: 10px;">선택한 세션 비교</button>
            <span id="selectedCount">0개 선택됨</span>
        `;
        document.querySelector('.sessions-controls').appendChild(actionsDiv);
    } else {
        compareBtn.textContent = '비교 모드';
        compareBtn.classList.remove('active');
        document.getElementById('compareActions')?.remove();
        selectedSessions = [];
    }

    displayFilteredSessions();
}

function compareSelectedSessions() {
    const checkboxes = document.querySelectorAll('.session-checkbox:checked');
    selectedSessions = Array.from(checkboxes).map(cb => cb.dataset.sessionId);

    if (selectedSessions.length < 2) {
        alert('비교하려면 최소 2개의 세션을 선택해주세요.');
        return;
    }

    if (selectedSessions.length > 5) {
        alert('최대 5개까지 비교할 수 있습니다.');
        return;
    }

    // 비교 페이지로 이동
    const sessionIds = selectedSessions.join(',');
    window.location.href = `/compare?sessions=${sessionIds}`;
}

// 체크박스 변경 이벤트
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('session-checkbox')) {
        const checkedCount = document.querySelectorAll('.session-checkbox:checked').length;
        const countElement = document.getElementById('selectedCount');
        if (countElement) {
            countElement.textContent = `${checkedCount}개 선택됨`;
        }
    }
});

// loadSessions 함수 수정 - allSessions에 저장
const originalLoadSessions = loadSessions;
async function loadSessions() {
    const sessionsList = document.getElementById('sessionsList');

    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();

        allSessions = data.sessions || [];

        if (allSessions.length > 0) {
            displayFilteredSessions();
        } else {
            sessionsList.innerHTML = '<p class="loading">아직 분석 기록이 없습니다.</p>';
        }
    } catch (error) {
        console.error('Load sessions error:', error);
        sessionsList.innerHTML = '<p class="loading">세션 목록을 불러올 수 없습니다.</p>';
    }
}
