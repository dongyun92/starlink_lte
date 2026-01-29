#!/usr/bin/env python3
"""
통신 품질 히트맵 생성기
- GPS 좌표에 LTE/Starlink 통신 품질 데이터를 지도에 시각화
- Folium 기반 인터랙티브 히트맵
"""

import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
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

        # 중심점 계산
        self.center_lat = self.df['latitude'].mean()
        self.center_lon = self.df['longitude'].mean()

        print(f"✓ Loaded {len(self.df)} data points")
        print(f"  Center: ({self.center_lat:.6f}, {self.center_lon:.6f})")

    def create_lte_heatmap(self, output_path: str = "lte_quality_heatmap.html"):
        """LTE 통신 품질 히트맵 생성"""
        print(f"\n🗺️  Creating LTE Quality Heatmap...")

        # LTE 데이터가 있는 포인트만 필터링
        lte_data = self.df[self.df['lte_available'] == True].copy()

        if len(lte_data) == 0:
            print("⚠️  No LTE data available")
            return

        # 지도 생성
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )

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

        # 지도 저장
        output_file = Path(self.data_path).parent / output_path
        m.save(str(output_file))
        print(f"✓ Saved LTE heatmap: {output_file}")

    def create_starlink_heatmap(self, output_path: str = "starlink_quality_heatmap.html"):
        """Starlink 통신 품질 히트맵 생성"""
        print(f"\n🗺️  Creating Starlink Quality Heatmap...")

        # Starlink 데이터가 있는 포인트만 필터링
        sl_data = self.df[self.df['starlink_available'] == True].copy()

        if len(sl_data) == 0:
            print("⚠️  No Starlink data available")
            return

        # 지도 생성
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )

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

        # 저장
        output_file = Path(self.data_path).parent / output_path
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

            popup_html = f"""
            <b>Time:</b> {pd.to_datetime(row['timestamp'], unit='s').strftime('%H:%M:%S')}<br>
            <b>Altitude:</b> {row['altitude']:.1f} m<br>
            <hr>
            """

            if row['lte_available']:
                popup_html += f"""
                <b>LTE Quality:</b><br>
                RSSI: {row['lte_rssi']:.0f} dBm<br>
                RSRP: {row['lte_rsrp']:.0f} dBm<br>
                SINR: {row['lte_sinr']:.1f} dB<br>
                <hr>
                """
            else:
                popup_html += "<b>LTE:</b> No data<br><hr>"

            if row['starlink_available']:
                popup_html += f"""
                <b>Starlink Quality:</b><br>
                Latency: {row['starlink_latency']:.1f} ms<br>
                Download: {row['starlink_download']:.1f} Mbps<br>
                Upload: {row['starlink_upload']:.1f} Mbps
                """
            else:
                popup_html += "<b>Starlink:</b> No data"

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
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(marker_cluster)

        # 비행 경로 그리기
        flight_path = [
            [row['latitude'], row['longitude']]
            for _, row in self.df.iterrows()
        ]
        folium.PolyLine(
            flight_path,
            color='blue',
            weight=2,
            opacity=0.7,
            name='Flight Path'
        ).add_to(m)

        # 레이어 컨트롤
        folium.LayerControl().add_to(m)

        # 저장
        output_file = Path(self.data_path).parent / output_path
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
