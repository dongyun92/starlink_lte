#!/usr/bin/env python3
"""
Starlink 미니 데이터 모니터링 및 CSV 저장 도구
"""

import grpc
import json
import csv
import time
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import argparse
import schedule

# Starlink gRPC imports
try:
    from spacex.api.device import device_pb2_grpc
    from spacex.api.device import device_pb2
except ImportError:
    print("Starlink gRPC 라이브러리를 설치해야 합니다:")
    print("pip install starlink-grpc")
    exit(1)

class StarlinkMonitor:
    def __init__(self, dish_ip: str = "192.168.100.1", csv_file: str = None):
        self.dish_ip = dish_ip
        self.csv_file = csv_file or f"starlink_data_{datetime.now().strftime('%Y%m%d')}.csv"
        self.setup_logging()
        self.channel = None
        self.stub = None
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('starlink_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """Starlink 디바이스에 gRPC 연결"""
        try:
            self.channel = grpc.insecure_channel(f'{self.dish_ip}:9200')
            self.stub = device_pb2_grpc.DeviceStub(self.channel)
            self.logger.info(f"Starlink ({self.dish_ip})에 연결되었습니다.")
            return True
        except Exception as e:
            self.logger.error(f"연결 실패: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """디바이스 상태 정보 수집"""
        try:
            request = device_pb2.Request()
            request.get_status.CopyFrom(device_pb2.GetStatusRequest())
            
            response = self.stub.Handle(request)
            
            # 상태 데이터 추출
            status_data = {
                'timestamp': datetime.now().isoformat(),
                'uptime_s': response.dish_get_status.device_info.uptime_s,
                'hardware_version': response.dish_get_status.device_info.hardware_version,
                'software_version': response.dish_get_status.device_info.software_version,
                'state': response.dish_get_status.state,
                'seconds_to_first_nonempty_slot': response.dish_get_status.seconds_to_first_nonempty_slot,
                'pop_ping_drop_rate': response.dish_get_status.pop_ping_drop_rate,
                'pop_ping_latency_ms': response.dish_get_status.pop_ping_latency_ms,
                'downlink_throughput_bps': response.dish_get_status.downlink_throughput_bps,
                'uplink_throughput_bps': response.dish_get_status.uplink_throughput_bps,
                'obstruction_fraction': response.dish_get_status.obstruction_stats.fraction_obstruction_time,
                'obstruction_avg_duration_s': response.dish_get_status.obstruction_stats.avg_prolonged_obstruction_duration_s,
                'alerts_thermal_throttle': response.dish_get_status.alerts.thermal_throttle,
                'alerts_thermal_shutdown': response.dish_get_status.alerts.thermal_shutdown,
                'alerts_mast_not_near_vertical': response.dish_get_status.alerts.mast_not_near_vertical,
                'alerts_unexpected_location': response.dish_get_status.alerts.unexpected_location,
                'alerts_slow_ethernet_speeds': response.dish_get_status.alerts.slow_ethernet_speeds,
                'snr': response.dish_get_status.snr,
                'seconds_obstructed': response.dish_get_status.obstruction_stats.currently_obstructed_duration_s,
                'gps_sats': response.dish_get_status.gps_stats.gps_sats,
                'gps_valid': response.dish_get_status.gps_stats.gps_valid,
            }
            
            return status_data
            
        except Exception as e:
            self.logger.error(f"상태 정보 수집 실패: {e}")
            return {}
    
    def get_history(self) -> Dict[str, Any]:
        """과거 데이터 히스토리 수집"""
        try:
            request = device_pb2.Request()
            request.get_history.CopyFrom(device_pb2.GetHistoryRequest())
            
            response = self.stub.Handle(request)
            
            # 최신 데이터 포인트만 추출 (마지막 15분)
            recent_data = {}
            if response.dish_get_history.downlink_throughput_bps:
                recent_data['avg_downlink_throughput_bps'] = sum(response.dish_get_history.downlink_throughput_bps[-15:]) / 15
            if response.dish_get_history.uplink_throughput_bps:
                recent_data['avg_uplink_throughput_bps'] = sum(response.dish_get_history.uplink_throughput_bps[-15:]) / 15
            if response.dish_get_history.pop_ping_drop_rate:
                recent_data['avg_pop_ping_drop_rate'] = sum(response.dish_get_history.pop_ping_drop_rate[-15:]) / 15
            if response.dish_get_history.pop_ping_latency_ms:
                recent_data['avg_pop_ping_latency_ms'] = sum(response.dish_get_history.pop_ping_latency_ms[-15:]) / 15
            if response.dish_get_history.snr:
                recent_data['avg_snr'] = sum(response.dish_get_history.snr[-15:]) / 15
                
            return recent_data
            
        except Exception as e:
            self.logger.error(f"히스토리 데이터 수집 실패: {e}")
            return {}
    
    def save_to_csv(self, data: Dict[str, Any]):
        """CSV 파일에 데이터 저장"""
        try:
            file_exists = os.path.exists(self.csv_file)
            
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = data.keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 파일이 없으면 헤더 작성
                if not file_exists:
                    writer.writeheader()
                    self.logger.info(f"새 CSV 파일 생성: {self.csv_file}")
                
                writer.writerow(data)
                
        except Exception as e:
            self.logger.error(f"CSV 저장 실패: {e}")
    
    def collect_data(self) -> Dict[str, Any]:
        """모든 데이터 수집 및 병합"""
        if not self.stub:
            if not self.connect():
                return {}
        
        status_data = self.get_status()
        history_data = self.get_history()
        
        # 데이터 병합
        combined_data = {**status_data, **history_data}
        
        if combined_data:
            self.logger.info(f"데이터 수집 완료: {len(combined_data)} 필드")
        
        return combined_data
    
    def run_once(self):
        """한 번 데이터 수집 및 저장"""
        data = self.collect_data()
        if data:
            self.save_to_csv(data)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 데이터 저장 완료")
            return True
        return False
    
    def run_continuous(self, interval_minutes: int = 5):
        """지속적인 데이터 수집"""
        self.logger.info(f"지속적 모니터링 시작 (간격: {interval_minutes}분)")
        
        # 스케줄 설정
        schedule.every(interval_minutes).minutes.do(self.run_once)
        
        # 즉시 첫 수집 실행
        self.run_once()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # 30초마다 스케줄 체크
        except KeyboardInterrupt:
            self.logger.info("모니터링이 사용자에 의해 중단되었습니다.")
        finally:
            self.disconnect()
    
    def disconnect(self):
        """연결 종료"""
        if self.channel:
            self.channel.close()
            self.logger.info("연결이 종료되었습니다.")

def main():
    parser = argparse.ArgumentParser(description='Starlink 미니 데이터 모니터링 도구')
    parser.add_argument('--ip', default='192.168.100.1', help='Starlink 디바이스 IP (기본값: 192.168.100.1)')
    parser.add_argument('--csv', help='CSV 파일명 (기본값: starlink_data_YYYYMMDD.csv)')
    parser.add_argument('--interval', type=int, default=5, help='수집 간격 (분, 기본값: 5)')
    parser.add_argument('--once', action='store_true', help='한 번만 수집하고 종료')
    
    args = parser.parse_args()
    
    monitor = StarlinkMonitor(dish_ip=args.ip, csv_file=args.csv)
    
    if args.once:
        success = monitor.run_once()
        if success:
            print(f"데이터가 {monitor.csv_file}에 저장되었습니다.")
        else:
            print("데이터 수집에 실패했습니다.")
    else:
        monitor.run_continuous(args.interval)

if __name__ == "__main__":
    main()