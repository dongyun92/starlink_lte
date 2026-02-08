#!/usr/bin/env python3
"""
통신 품질 히트맵 생성기
- GPS 좌표에 LTE/Starlink 통신 품질 데이터를 지도에 시각화
- Folium 기반 인터랙티브 히트맵
"""

import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster, Fullscreen
import numpy as np
from pathlib import Path


class QualityHeatmapGenerator:
    """통신 품질 히트맵 생성기"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None
        self.center_lat = None
        self.center_lon = None

    def load_data(self):
        """병합된 데이터 로드"""
        print(f"📁 Loading merged data: {self.data_path.name}")
        self.df = pd.read_csv(self.data_path)

        # 타임스탬프를 datetime으로 변환 (자동 형식 감지)
        # Unix timestamp (숫자) 또는 ISO 문자열 (YYYY-MM-DD HH:MM:SS) 모두 처리
        if pd.api.types.is_datetime64_any_dtype(self.df['timestamp']):
            # Already datetime, no conversion needed
            pass
        elif pd.api.types.is_numeric_dtype(self.df['timestamp']):
            # Unix timestamp (numeric)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='s', utc=True)
        else:
            # ISO string format
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], utc=True, errors='coerce')

        # flight_id로 정렬 후 타임스탬프로 정렬 (여러 비행 경로를 올바르게 그리기 위해 필수!)
        if 'flight_id' in self.df.columns:
            self.df = self.df.sort_values(['flight_id', 'timestamp']).reset_index(drop=True)
            print(f"  🛫 Found {self.df['flight_id'].nunique()} separate flights")
        else:
            self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        # 중심점 계산
        self.center_lat = self.df['latitude'].mean()
        self.center_lon = self.df['longitude'].mean()

        print(f"✓ Loaded {len(self.df)} data points")
        print(f"  Center: ({self.center_lat:.6f}, {self.center_lon:.6f})")

    def _add_flight_paths(self, map_obj):
        """비행 경로를 지도에 추가 (고도별 색상 그라데이션)"""
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors

        # 고도 데이터가 있는지 확인
        has_altitude = 'altitude' in self.df.columns and self.df['altitude'].notna().any()

        if has_altitude:
            # 고도 범위 계산
            min_alt = self.df['altitude'].min()
            max_alt = self.df['altitude'].max()

            # 컬러맵 생성 (terrain - 지형적 색상)
            cmap = plt.cm.get_cmap('terrain')
            norm = mcolors.Normalize(vmin=min_alt, vmax=max_alt)

        # flight_id 컬럼이 있는지 확인
        if 'flight_id' in self.df.columns:
            # 여러 비행이 있는 경우 - 각 비행마다 별도의 경로 그리기
            flight_ids = sorted(self.df['flight_id'].unique())

            for idx, flight_id in enumerate(flight_ids):
                flight_df = self.df[self.df['flight_id'] == flight_id].copy()

                # 비행 이름 가져오기
                flight_name = flight_df['flight_name'].iloc[0] if 'flight_name' in flight_df.columns else f"Flight {flight_id + 1}"

                if has_altitude:
                    # 고도별 색상 선분으로 그리기
                    for i in range(len(flight_df) - 1):
                        start = [flight_df.iloc[i]['latitude'], flight_df.iloc[i]['longitude']]
                        end = [flight_df.iloc[i+1]['latitude'], flight_df.iloc[i+1]['longitude']]

                        # 평균 고도로 색상 결정
                        avg_altitude = (flight_df.iloc[i]['altitude'] + flight_df.iloc[i+1]['altitude']) / 2
                        color_value = norm(avg_altitude)
                        rgb = cmap(color_value)
                        hex_color = mcolors.rgb2hex(rgb)

                        # 선분 그리기
                        folium.PolyLine(
                            [start, end],
                            color=hex_color,
                            weight=4,
                            opacity=0.8,
                            popup=f"{flight_name}<br>고도: {avg_altitude:.1f}m"
                        ).add_to(map_obj)
                else:
                    # 고도 데이터가 없으면 단색으로 그리기
                    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkblue', 'darkred', 'darkgreen']
                    color = colors[idx % len(colors)]

                    flight_path = [
                        [row['latitude'], row['longitude']]
                        for _, row in flight_df.iterrows()
                    ]

                    folium.PolyLine(
                        flight_path,
                        color=color,
                        weight=3,
                        opacity=0.7,
                        name=f'📍 {flight_name}'
                    ).add_to(map_obj)

                # 시작점과 종료점 마커 추가
                start_lat = flight_df.iloc[0]['latitude']
                start_lon = flight_df.iloc[0]['longitude']
                end_lat = flight_df.iloc[-1]['latitude']
                end_lon = flight_df.iloc[-1]['longitude']

                start_alt = flight_df.iloc[0]['altitude'] if has_altitude else 0
                end_alt = flight_df.iloc[-1]['altitude'] if has_altitude else 0

                folium.Marker(
                    [start_lat, start_lon],
                    popup=f"🛫 {flight_name} - Start<br>{flight_df['timestamp'].iloc[0]}<br>고도: {start_alt:.1f}m",
                    icon=folium.Icon(color='green', icon='play', prefix='fa')
                ).add_to(map_obj)

                folium.Marker(
                    [end_lat, end_lon],
                    popup=f"🛬 {flight_name} - End<br>{flight_df['timestamp'].iloc[-1]}<br>고도: {end_alt:.1f}m",
                    icon=folium.Icon(color='red', icon='stop', prefix='fa')
                ).add_to(map_obj)

            print(f"  ✓ Drew {len(flight_ids)} flight paths" + (" with altitude colors" if has_altitude else ""))
        else:
            # 단일 비행인 경우
            if has_altitude:
                # 고도별 색상 선분으로 그리기
                for i in range(len(self.df) - 1):
                    start = [self.df.iloc[i]['latitude'], self.df.iloc[i]['longitude']]
                    end = [self.df.iloc[i+1]['latitude'], self.df.iloc[i+1]['longitude']]

                    avg_altitude = (self.df.iloc[i]['altitude'] + self.df.iloc[i+1]['altitude']) / 2
                    color_value = norm(avg_altitude)
                    rgb = cmap(color_value)
                    hex_color = mcolors.rgb2hex(rgb)

                    folium.PolyLine(
                        [start, end],
                        color=hex_color,
                        weight=4,
                        opacity=0.8,
                        popup=f"고도: {avg_altitude:.1f}m"
                    ).add_to(map_obj)

                print(f"  ✓ Drew single flight path with altitude colors")
            else:
                # 고도 데이터가 없으면 단색으로 그리기
                flight_path = [
                    [row['latitude'], row['longitude']]
                    for _, row in self.df.iterrows()
                ]
                folium.PolyLine(
                    flight_path,
                    color='blue',
                    weight=2,
                    opacity=0.5,
                    name='Flight Path'
                ).add_to(map_obj)
                print(f"  ✓ Drew single flight path")

        # 고도 범례 추가
        if has_altitude:
            legend_html = f'''
            <div style="position: fixed;
                        bottom: 50px; right: 50px; width: 180px; height: 160px;
                        background-color: white; border:2px solid grey; z-index:9999;
                        font-size:12px; padding: 10px; border-radius: 5px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
            <b>고도 범례 (Altitude)</b><br>
            <div style="background: linear-gradient(to bottom,
                        {mcolors.rgb2hex(cmap(1.0))},
                        {mcolors.rgb2hex(cmap(0.75))},
                        {mcolors.rgb2hex(cmap(0.5))},
                        {mcolors.rgb2hex(cmap(0.25))},
                        {mcolors.rgb2hex(cmap(0.0))});
                        height: 90px; margin: 5px 0; border: 1px solid #ccc;"></div>
            <div style="display: flex; justify-content: space-between;">
                <span><b>{max_alt:.0f}m</b></span>
                <span>↕</span>
                <span><b>{min_alt:.0f}m</b></span>
            </div>
            </div>
            '''
            map_obj.get_root().html.add_child(folium.Element(legend_html))

    def create_lte_heatmap(self, output_path: str = "lte_quality_heatmap.html"):
        """LTE 통신 품질 히트맵 생성"""
        print(f"\n🗺️  Creating LTE Quality Heatmap...")

        # LTE 데이터가 있는 포인트만 필터링
        lte_data = self.df[self.df['lte_available'] == True].copy()

        # 지도 생성 (데이터 여부와 상관없이 항상 생성)
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )

        if len(lte_data) == 0:
            print("⚠️  No LTE data available - generating empty map with flight path")

            # 데이터 없음 메시지
            no_data_html = """
            <div style="position: fixed;
                        top: 10px; left: 50px; width: 300px; height: auto;
                        background-color: #fff3cd; border:2px solid #ffc107; z-index:9999;
                        font-size:14px; padding: 15px; border-radius: 5px;">
            <b style="color: #856404;">⚠️ LTE Data Not Available</b><br>
            <span style="color: #856404;">No LTE communication data was found for this flight session.</span>
            </div>
            """
            m.get_root().html.add_child(folium.Element(no_data_html))
        else:
            # RSSI 기반 히트맵 데이터 준비
            # RSSI: -113 ~ -51 dBm, 높을수록 좋음
            # 히트맵 강도: 0 ~ 1로 정규화
            lte_data['rssi_normalized'] = (lte_data['lte_rssi'] + 113) / (51 - (-113))
            lte_data['rssi_normalized'] = lte_data['rssi_normalized'].clip(0, 1)

            # 히트맵 데이터: [lat, lon, intensity]
            heat_data = [
                [row['latitude'], row['longitude'], row['rssi_normalized']]
                for _, row in lte_data.iterrows()
            ]

            # 히트맵 레이어 추가
            HeatMap(
                heat_data,
                name='LTE Signal Strength (RSSI)',
                min_opacity=0.3,
                max_opacity=0.8,
                radius=15,
                blur=20,
                gradient={
                    0.0: 'red',
                    0.4: 'orange',
                    0.6: 'yellow',
                    0.8: 'lightgreen',
                    1.0: 'green'
                }
            ).add_to(m)

            # 통계 정보 추가
            stats_html = f"""
            <div style="position: fixed;
                        top: 10px; left: 50px; width: 250px; height: auto;
                        background-color: white; border:2px solid grey; z-index:9999;
                        font-size:14px; padding: 10px">
            <b>LTE Quality Statistics</b><br>
            Points: {len(lte_data)}<br>
            RSSI: {lte_data['lte_rssi'].mean():.1f} dBm<br>
            RSRP: {lte_data['lte_rsrp'].mean():.1f} dBm<br>
            SINR: {lte_data['lte_sinr'].mean():.1f} dB<br>
            Coverage: {len(lte_data)/len(self.df)*100:.1f}%
            </div>
            """
            m.get_root().html.add_child(folium.Element(stats_html))

            # 범례 추가
            legend_html = '''
            <div style="position: fixed;
                        bottom: 50px; left: 50px; width: 150px; height: 120px;
                        background-color: white; border:2px solid grey; z-index:9999;
                        font-size:12px; padding: 10px">
            <b>Signal Quality</b><br>
            <div style="background: linear-gradient(to right, red, orange, yellow, lightgreen, green);
                        height: 20px; margin: 5px 0;"></div>
            <b>Poor</b> → <b>Excellent</b>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))

        # 비행 경로 그리기 (여러 비행 로그 지원)
        self._add_flight_paths(m)

        # 레이어 컨트롤
        folium.LayerControl().add_to(m)

        # 전체화면 버튼 추가
        Fullscreen(
            position='topright',
            title='전체화면',
            title_cancel='전체화면 종료',
            force_separate_button=True
        ).add_to(m)

        # 지도 저장
        output_file = Path(output_path)
        m.save(str(output_file))
        print(f"✓ Saved LTE heatmap: {output_file}")

    def create_starlink_heatmap(self, output_path: str = "starlink_quality_heatmap.html"):
        """Starlink 통신 품질 히트맵 생성"""
        print(f"\n🗺️  Creating Starlink Quality Heatmap...")

        # Starlink 데이터가 있는 포인트만 필터링
        sl_data = self.df[self.df['starlink_available'] == True].copy()

        # 지도 생성 (데이터 여부와 상관없이 항상 생성)
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )

        if len(sl_data) == 0:
            print("⚠️  No Starlink data available - generating empty map with flight path")

            # 데이터 없음 메시지
            no_data_html = """
            <div style="position: fixed;
                        top: 10px; left: 50px; width: 300px; height: auto;
                        background-color: #fff3cd; border:2px solid #ffc107; z-index:9999;
                        font-size:14px; padding: 15px; border-radius: 5px;">
            <b style="color: #856404;">⚠️ Starlink Data Not Available</b><br>
            <span style="color: #856404;">No Starlink communication data was found for this flight session.</span>
            </div>
            """
            m.get_root().html.add_child(folium.Element(no_data_html))
        else:
            # 레이턴시 기반 히트맵 (낮을수록 좋음)
            # Latency: 0 ~ 200 ms 정도, 낮을수록 좋음
            # 히트맵 강도: 0 (나쁨) ~ 1 (좋음)로 변환
            sl_data['latency_normalized'] = 1 - (sl_data['starlink_latency'].clip(0, 200) / 200)

            # 히트맵 데이터
            heat_data = [
                [row['latitude'], row['longitude'], row['latency_normalized']]
                for _, row in sl_data.iterrows()
            ]

            # 히트맵 레이어
            HeatMap(
                heat_data,
                name='Starlink Latency Quality',
                min_opacity=0.3,
                max_opacity=0.8,
                radius=15,
                blur=20,
                gradient={
                    0.0: 'red',
                    0.4: 'orange',
                    0.6: 'yellow',
                    0.8: 'lightgreen',
                    1.0: 'green'
                }
            ).add_to(m)

            # 통계 정보
            stats_html = f"""
            <div style="position: fixed;
                        top: 10px; left: 50px; width: 280px; height: auto;
                        background-color: white; border:2px solid grey; z-index:9999;
                        font-size:14px; padding: 10px">
            <b>Starlink Quality Statistics</b><br>
            Points: {len(sl_data)}<br>
            Latency: {sl_data['starlink_latency'].mean():.1f} ms<br>
            Download: {sl_data['starlink_download'].mean():.1f} Mbps<br>
            Upload: {sl_data['starlink_upload'].mean():.1f} Mbps<br>
            Coverage: {len(sl_data)/len(self.df)*100:.1f}%
            </div>
            """
            m.get_root().html.add_child(folium.Element(stats_html))

            # 범례
            legend_html = '''
            <div style="position: fixed;
                        bottom: 50px; left: 50px; width: 150px; height: 120px;
                        background-color: white; border:2px solid grey; z-index:9999;
                        font-size:12px; padding: 10px">
            <b>Latency Quality</b><br>
            <div style="background: linear-gradient(to right, red, orange, yellow, lightgreen, green);
                        height: 20px; margin: 5px 0;"></div>
            <b>High</b> → <b>Low</b>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))

        # 비행 경로 그리기 (여러 비행 로그 지원)
        self._add_flight_paths(m)

        # 레이어 컨트롤
        folium.LayerControl().add_to(m)

        # 전체화면 버튼 추가
        Fullscreen(
            position='topright',
            title='전체화면',
            title_cancel='전체화면 종료',
            force_separate_button=True
        ).add_to(m)

        # 저장
        output_file = Path(output_path)
        m.save(str(output_file))
        print(f"✓ Saved Starlink heatmap: {output_file}")

    def create_combined_map(self, output_path: str = "combined_quality_map.html"):
        """LTE + Starlink 통합 지도 생성 (마커 클러스터)"""
        print(f"\n🗺️  Creating Combined Quality Map...")

        # 지도 생성
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )

        # 마커 클러스터 그룹
        marker_cluster = MarkerCluster(name='Data Points').add_to(m)

        # 데이터 포인트 추가
        for idx, row in self.df.iterrows():
            # 10개 중 1개만 표시 (너무 많으면 느려짐)
            if idx % 10 != 0:
                continue

            # 자세값 표시 (있는 경우만)
            attitude_html = ""
            if pd.notna(row.get('roll')) and pd.notna(row.get('pitch')) and pd.notna(row.get('yaw')):
                attitude_html = f"""
                <b>자세:</b><br>
                &nbsp;&nbsp;Roll: {row['roll']:.1f}°<br>
                &nbsp;&nbsp;Pitch: {row['pitch']:.1f}°<br>
                &nbsp;&nbsp;Yaw: {row['yaw']:.1f}°<br>
                """

            # Format timestamp safely
            timestamp_str = 'N/A'
            if pd.notna(row['timestamp']):
                try:
                    timestamp_str = pd.to_datetime(row['timestamp']).strftime('%H:%M:%S')
                except:
                    timestamp_str = str(row['timestamp'])

            popup_html = f"""
            <div style="font-size: 11px; min-width: 280px;">
            <b style="font-size: 13px;">📍 비행 정보</b><br>
            <b>Time:</b> {timestamp_str}<br>
            <b>위치:</b> {row['latitude']:.6f}, {row['longitude']:.6f}<br>
            <b>고도:</b> {row['altitude']:.1f} m<br>
            <b>속도:</b> {row['speed_mps']:.2f} m/s ({row['speed_mps']*3.6:.1f} km/h)<br>
            <b>원점 거리:</b> {row['distance_from_origin']:.1f} m<br>
            <b>비행 시간:</b> {row['flight_time_elapsed']:.1f} s<br>
            {attitude_html}
            <hr style="margin: 8px 0;">
            """

            if row['lte_available']:
                lte_info = f"""
                <b style="font-size: 13px;">📶 LTE 품질</b><br>
                <b>RSSI:</b> {row['lte_rssi']:.0f} dBm<br>
                <b>RSRP:</b> {row['lte_rsrp']:.0f} dBm<br>
                <b>RSRQ:</b> {row['lte_rsrq']:.1f} dB<br>
                <b>SINR:</b> {row['lte_sinr']:.1f} dB<br>
                """
                # 선택적 필드 추가
                if pd.notna(row.get('lte_network_type')):
                    lte_info += f"<b>네트워크:</b> {row['lte_network_type']}"
                    if pd.notna(row.get('lte_network_operator')):
                        lte_info += f" ({row['lte_network_operator']})"
                    lte_info += "<br>"
                if pd.notna(row.get('lte_network_band')):
                    lte_info += f"<b>Band:</b> {row['lte_network_band']}<br>"
                lte_info += "<hr style='margin: 8px 0;'>"
                popup_html += lte_info
            else:
                popup_html += "<b>📶 LTE:</b> No data<br><hr style='margin: 8px 0;'>"

            if row['starlink_available']:
                starlink_info = f"""<b style="font-size: 13px;">🛰️ Starlink 품질</b><br>"""

                # 상태 정보 (선택적)
                if pd.notna(row.get('starlink_state')):
                    starlink_info += f"<b>상태:</b> {row['starlink_state']}<br>"
                if pd.notna(row.get('starlink_uptime')):
                    starlink_info += f"<b>Uptime:</b> {row['starlink_uptime']:.0f} s<br>"

                # 처리량
                if pd.notna(row.get('starlink_download')):
                    starlink_info += f"""<br><b style="color: #2ebd85;">처리량:</b><br>"""
                    starlink_info += f"<b>Download:</b> {row['starlink_download']:.2f} Mbps<br>"
                    if pd.notna(row.get('starlink_upload')):
                        starlink_info += f"<b>Upload:</b> {row['starlink_upload']:.2f} Mbps<br>"

                # 신호 품질
                starlink_info += f"""<br><b style="color: #667eea;">신호 품질:</b><br>"""
                if pd.notna(row.get('starlink_latency')):
                    starlink_info += f"<b>Latency:</b> {row['starlink_latency']:.1f} ms<br>"
                if pd.notna(row.get('starlink_ping_drop_rate')):
                    starlink_info += f"<b>Ping Drop:</b> {row['starlink_ping_drop_rate']:.2f}%<br>"
                if pd.notna(row.get('starlink_snr')):
                    starlink_info += f"<b>SNR:</b> {row['starlink_snr']:.1f} dB<br>"

                # 위성 각도
                if pd.notna(row.get('starlink_azimuth')) and pd.notna(row.get('starlink_elevation')):
                    starlink_info += f"""<br><b style="color: #f5576c;">위성 각도:</b><br>"""
                    starlink_info += f"<b>Azimuth:</b> {row['starlink_azimuth']:.1f}°<br>"
                    starlink_info += f"<b>Elevation:</b> {row['starlink_elevation']:.1f}°<br>"

                # GPS 정보 제거됨 (사용자 요청)

                popup_html += starlink_info
            else:
                popup_html += "<b>🛰️ Starlink:</b> No data"

            popup_html += "</div>"

            # 마커 색상 결정 (LTE 기준)
            if row['lte_available']:
                if row['lte_rssi'] > -70:
                    color = 'green'
                elif row['lte_rssi'] > -85:
                    color = 'orange'
                else:
                    color = 'red'
            else:
                color = 'gray'

            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=350),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(marker_cluster)

        # 비행 경로 그리기 (여러 비행 로그 지원)
        self._add_flight_paths(m)

        # 레이어 컨트롤
        folium.LayerControl().add_to(m)

        # 전체화면 버튼 추가
        Fullscreen(
            position='topright',
            title='전체화면',
            title_cancel='전체화면 종료',
            force_separate_button=True
        ).add_to(m)

        # 저장
        output_file = Path(output_path)
        m.save(str(output_file))
        print(f"✓ Saved combined map: {output_file}")


def main():
    """테스트 실행"""
    print("=" * 60)
    print("QUALITY HEATMAP GENERATOR - TEST")
    print("=" * 60)

    # 경로 설정
    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    # 히트맵 생성기
    generator = QualityHeatmapGenerator(str(merged_data))

    # 데이터 로드
    generator.load_data()

    # 히트맵 생성
    generator.create_lte_heatmap()
    generator.create_starlink_heatmap()
    generator.create_combined_map()

    print("\n" + "=" * 60)
    print("✅ All heatmaps generated successfully!")
    print("=" * 60)
    print("\nGenerated files:")
    print(f"  - {base_dir}/lte_quality_heatmap.html")
    print(f"  - {base_dir}/starlink_quality_heatmap.html")
    print(f"  - {base_dir}/combined_quality_map.html")


if __name__ == "__main__":
    main()
