// Starlink 대시보드 JavaScript

// 소켓 연결
const socket = io();

// 차트 변수
let throughputChart;
let signalChart;

// 데이터 저장소
let dataHistory = [];
const maxDataPoints = 20;

// 소켓 이벤트 핸들러
socket.on('connect', function() {
    updateConnectionStatus(true);
    console.log('서버에 연결되었습니다');
});

socket.on('disconnect', function() {
    updateConnectionStatus(false);
    console.log('서버 연결이 끊어졌습니다');
});

socket.on('data_update', function(data) {
    console.log('새 데이터 수신:', data);
    updateDashboard(data);
    updateCharts(data);
    updateLastUpdateTime();
});

// 연결 상태 업데이트
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (connected) {
        statusElement.innerHTML = '<i class="fas fa-circle text-success"></i> 연결됨';
    } else {
        statusElement.innerHTML = '<i class="fas fa-circle text-danger"></i> 연결 끊김';
    }
}

// 마지막 업데이트 시간
function updateLastUpdateTime() {
    const now = new Date();
    document.getElementById('last-update').textContent = 
        `마지막 업데이트: ${now.toLocaleTimeString()}`;
}

// 대시보드 업데이트
function updateDashboard(data) {
    // SNR
    document.getElementById('snr-value').textContent = 
        data.snr ? data.snr.toFixed(1) : '-';
    
    // 다운로드 속도 (bps -> Mbps)
    if (data.downlink_throughput_bps) {
        const mbps = (data.downlink_throughput_bps / 1000000).toFixed(1);
        document.getElementById('downlink-value').textContent = mbps;
    }
    
    // 업로드 속도 (bps -> Mbps)
    if (data.uplink_throughput_bps) {
        const mbps = (data.uplink_throughput_bps / 1000000).toFixed(1);
        document.getElementById('uplink-value').textContent = mbps;
    }
    
    // 핑 지연시간
    document.getElementById('ping-value').textContent = 
        data.pop_ping_latency_ms ? data.pop_ping_latency_ms.toFixed(0) : '-';
    
    // 패킷 손실률
    if (data.pop_ping_drop_rate) {
        const percentage = (data.pop_ping_drop_rate * 100).toFixed(2);
        document.getElementById('packet-loss-value').textContent = percentage;
    }
    
    // 장애물 차단율
    if (data.obstruction_fraction) {
        const percentage = (data.obstruction_fraction * 100).toFixed(2);
        document.getElementById('obstruction-value').textContent = percentage;
    }
    
    // 시스템 정보
    document.getElementById('hardware-version').textContent = 
        data.hardware_version || '-';
    document.getElementById('software-version').textContent = 
        data.software_version || '-';
    
    // 가동시간 (초 -> 시간:분)
    if (data.uptime_s) {
        const hours = Math.floor(data.uptime_s / 3600);
        const minutes = Math.floor((data.uptime_s % 3600) / 60);
        document.getElementById('uptime').textContent = `${hours}시간 ${minutes}분`;
    }
    
    document.getElementById('device-state').textContent = data.state || '-';
    document.getElementById('gps-sats').textContent = data.gps_sats || '-';
    
    // 경고 업데이트
    updateAlerts(data);
}

// 경고 업데이트
function updateAlerts(data) {
    const container = document.getElementById('alerts-container');
    container.innerHTML = '';
    
    const alerts = [];
    
    if (data.alerts_thermal_throttle) {
        alerts.push({type: 'warning', message: '열 제한 활성화'});
    }
    if (data.alerts_thermal_shutdown) {
        alerts.push({type: 'danger', message: '열 차단 경고'});
    }
    if (data.alerts_mast_not_near_vertical) {
        alerts.push({type: 'warning', message: '안테나 기울기 문제'});
    }
    if (data.alerts_unexpected_location) {
        alerts.push({type: 'info', message: '예상치 못한 위치'});
    }
    if (data.alerts_slow_ethernet_speeds) {
        alerts.push({type: 'warning', message: '느린 이더넷 속도'});
    }
    
    if (alerts.length === 0) {
        container.innerHTML = '<div class="alert alert-success">모든 상태 정상</div>';
    } else {
        alerts.forEach(alert => {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${alert.type} alert-custom`;
            alertDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${alert.message}`;
            container.appendChild(alertDiv);
        });
    }
}

// 차트 초기화
function initCharts() {
    // 처리량 차트
    const throughputCtx = document.getElementById('throughputChart').getContext('2d');
    throughputChart = new Chart(throughputCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '다운로드 (Mbps)',
                data: [],
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                tension: 0.4
            }, {
                label: '업로드 (Mbps)',
                data: [],
                borderColor: '#17a2b8',
                backgroundColor: 'rgba(23, 162, 184, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Mbps'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '시간'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            }
        }
    });
    
    // 신호 품질 차트
    const signalCtx = document.getElementById('signalChart').getContext('2d');
    signalChart = new Chart(signalCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'SNR (dB)',
                data: [],
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                tension: 0.4,
                yAxisID: 'y'
            }, {
                label: '핑 지연시간 (ms)',
                data: [],
                borderColor: '#ffc107',
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                tension: 0.4,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'SNR (dB)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '지연시간 (ms)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            }
        }
    });
}

// 차트 데이터 업데이트
function updateCharts(data) {
    const now = new Date();
    const timeLabel = now.toLocaleTimeString();
    
    // 데이터 히스토리에 추가
    dataHistory.push({
        time: timeLabel,
        ...data
    });
    
    // 최대 포인트 수 제한
    if (dataHistory.length > maxDataPoints) {
        dataHistory.shift();
    }
    
    // 차트 라벨 업데이트
    const labels = dataHistory.map(d => d.time);
    
    // 처리량 차트 업데이트
    throughputChart.data.labels = labels;
    throughputChart.data.datasets[0].data = dataHistory.map(d => 
        d.downlink_throughput_bps ? (d.downlink_throughput_bps / 1000000).toFixed(1) : 0
    );
    throughputChart.data.datasets[1].data = dataHistory.map(d => 
        d.uplink_throughput_bps ? (d.uplink_throughput_bps / 1000000).toFixed(1) : 0
    );
    throughputChart.update('none');
    
    // 신호 품질 차트 업데이트
    signalChart.data.labels = labels;
    signalChart.data.datasets[0].data = dataHistory.map(d => d.snr || 0);
    signalChart.data.datasets[1].data = dataHistory.map(d => d.pop_ping_latency_ms || 0);
    signalChart.update('none');
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    console.log('대시보드가 초기화되었습니다');
});

// 브라우저 탭이 활성화될 때 다시 연결 시도
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && !socket.connected) {
        socket.connect();
    }
});