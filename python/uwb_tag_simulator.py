#!/usr/bin/env python3
import socket
import json
import time
import math
import random
from typing import Tuple, Dict, List

class UWBTagSimulator:
    def __init__(self):
        # 建立 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 廣播設定
        self.broadcast_ip = '255.255.255.255'
        self.broadcast_port = 12345
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Anchor 位置設定 (x, y, z) in meters
        self.anchor_positions = {
            'A1': (0.0, 0.0, 0.0),    # 原點
            'A2': (8.0, 0.0, 0.0),    # x軸 8m
            'A3': (4.0, 6.0, 0.0),    # y軸 6m
            'A4': (4.0, 3.0, 3.0),    # 上方 3m
        }

        # 多個 Tag 的設定
        self.tags = {
            'T1': {
                'pos': [4.0, 3.0, 1.5],  # 起始位置（房間中心）
                'center': [4.0, 3.0, 1.5],  # 圓周運動中心
                'radius': 2.0,  # 移動半徑
                'angle': 0.0,  # 當前角度
                'speed': 2.0,  # 角速度 (弧度/秒)
                'height_range': [1.0, 2.0]  # 高度範圍
            },
            'T2': {
                'pos': [2.0, 2.0, 1.0],
                'center': [2.0, 2.0, 1.0],
                'radius': 1.5,
                'angle': math.pi,  # 與 T1 相反的起始角度
                'speed': 1.5,
                'height_range': [0.5, 1.5]
            },
            'T3': {
                'pos': [6.0, 4.0, 0.5],
                'center': [6.0, 4.0, 0.5],
                'radius': 1.0,
                'angle': math.pi/2,
                'speed': 3.0,
                'height_range': [0.0, 1.0]
            }
        }

        # 距離測量誤差設定
        self.distance_noise = 0.1      # 距離測量的標準差（米）

    def calculate_distance(self, pos1: Tuple[float, float, float],
                         pos2: List[float]) -> float:
        """計算兩點間 3D 距離"""
        return math.sqrt(sum((p1 - p2)**2 for p1, p2 in zip(pos1, pos2)))

    def add_measurement_noise(self, distance: float) -> float:
        """添加測量噪聲"""
        return distance + random.gauss(0, self.distance_noise)

    def update_position(self, tag_id: str):
        """更新指定 Tag 的 3D 位置（螺旋運動）"""
        tag = self.tags[tag_id]
        tag['angle'] += tag['speed'] * 0.1  # 0.1秒的角度變化

        # 更新 XY 平面的位置（圓周運動）
        tag['pos'][0] = (tag['center'][0] +
                        tag['radius'] * math.cos(tag['angle']))
        tag['pos'][1] = (tag['center'][1] +
                        tag['radius'] * math.sin(tag['angle']))

        # 更新 Z 軸位置（上下擺動）
        z_mid = (tag['height_range'][0] + tag['height_range'][1]) / 2
        z_amplitude = (tag['height_range'][1] - tag['height_range'][0]) / 2
        tag['pos'][2] = z_mid + z_amplitude * math.sin(tag['angle'])

    def generate_random_movement(self, tag_id: str):
        """生成隨機 3D 移動"""
        tag = self.tags[tag_id]

        # XY平面隨機移動
        tag['pos'][0] += random.uniform(-0.2, 0.2)
        tag['pos'][1] += random.uniform(-0.2, 0.2)
        tag['pos'][2] += random.uniform(-0.1, 0.1)

        # 確保不會移出範圍
        tag['pos'][0] = max(0, min(8, tag['pos'][0]))
        tag['pos'][1] = max(0, min(6, tag['pos'][1]))
        tag['pos'][2] = max(tag['height_range'][0],
                           min(tag['height_range'][1], tag['pos'][2]))

    def create_measurement_data(self, tag_id: str) -> dict:
        """創建測量數據"""
        tag = self.tags[tag_id]
        anchors = []

        for anchor_id, pos in self.anchor_positions.items():
            distance = self.calculate_distance(pos, tag['pos'])
            noisy_distance = self.add_measurement_noise(distance)
            tof = noisy_distance / 299792458.0  # 光速（米/秒）
            anchors.append({
                "id": anchor_id,  # 使用完整的錨點ID (e.g., 'A1')
                "distance": round(noisy_distance, 2),  # 保留兩位小數
                "tof": tof
            })

        return {
            "tag": tag_id,  # 改用 "tag" 而不是 "tag_id"
            "anchors": anchors,
            "true_position": {  # 用於驗證的真實位置
                "x": tag['pos'][0],
                "y": tag['pos'][1],
                "z": tag['pos'][2]
            }
        }

    def run(self, movement_type="circle"):
        """運行模擬器"""
        print(f"Starting UWB Tag Simulator ({movement_type} movement)")
        print(f"Simulating {len(self.tags)} tags")
        print("Broadcasting to {}:{}".format(
            self.broadcast_ip, self.broadcast_port))

        try:
            while True:
                for tag_id in self.tags:
                    # 更新位置
                    if movement_type == "circle":
                        self.update_position(tag_id)
                    else:
                        self.generate_random_movement(tag_id)

                    # 生成並發送數據
                    data = self.create_measurement_data(tag_id)
                    json_data = json.dumps(data)
                    self.sock.sendto(
                        json_data.encode(),
                        (self.broadcast_ip, self.broadcast_port)
                    )

                    # 顯示當前位置
                    tag = self.tags[tag_id]
                    print(f"\r{tag_id} position: ({tag['pos'][0]:.2f}, "
                          f"{tag['pos'][1]:.2f}, {tag['pos'][2]:.2f})",
                          end="   ")

                time.sleep(0.1)  # 100ms 間隔

        except KeyboardInterrupt:
            print("\nSimulator stopped by user")
        finally:
            self.sock.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='UWB Tag Simulator')
    parser.add_argument('--movement', choices=['circle', 'random'],
                       default='circle',
                       help='Movement pattern (circle or random)')
    parser.add_argument('--tags', type=int, default=3,
                       help='Number of tags to simulate (1-3)')
    args = parser.parse_args()

    simulator = UWBTagSimulator()
    # 根據用戶設定調整要模擬的標籤數量
    if args.tags < len(simulator.tags):
        tags_to_remove = list(simulator.tags.keys())[args.tags:]
        for tag_id in tags_to_remove:
            del simulator.tags[tag_id]

    simulator.run(args.movement)
