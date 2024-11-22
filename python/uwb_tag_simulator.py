#!/usr/bin/env python3
import socket
import json
import time
import math
import random
from typing import Tuple, Dict

class UWBTagSimulator:
    def __init__(self):
        # 建立 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 廣播設定
        self.broadcast_ip = '255.255.255.255'
        self.broadcast_port = 12345
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Anchor 位置設定 (x, y) in meters
        self.anchor_positions = {
            'A1': (0.0, 0.0),    # 原點
            'A2': (8.0, 0.0),    # x軸 8m
            'A3': (4.0, 6.0),    # 中間上方 6m
        }

        # Tag 移動設定
        self.current_pos = [4.0, 3.0]  # 起始位置
        self.movement_radius = 2.0      # 移動半徑
        self.center_pos = [4.0, 3.0]   # 圓周運動中心
        self.angle = 0.0               # 當前角度
        self.speed = 2.0               # 角速度 (弧度/秒)
        
        # 距離測量誤差設定
        self.distance_noise = 0.1      # 距離測量的標準差（米）

    def calculate_distance(self, pos1: Tuple[float, float], 
                         pos2: Tuple[float, float]) -> float:
        """計算兩點間距離"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def add_measurement_noise(self, distance: float) -> float:
        """添加測量噪聲"""
        return distance + random.gauss(0, self.distance_noise)

    def update_position(self):
        """更新 Tag 位置（圓周運動）"""
        self.angle += self.speed * 0.1  # 0.1秒的角度變化
        self.current_pos[0] = (self.center_pos[0] + 
                             self.movement_radius * math.cos(self.angle))
        self.current_pos[1] = (self.center_pos[1] + 
                             self.movement_radius * math.sin(self.angle))

    def generate_random_movement(self):
        """生成隨機移動"""
        self.current_pos[0] += random.uniform(-0.2, 0.2)
        self.current_pos[1] += random.uniform(-0.2, 0.2)
        
        # 確保不會移出範圍
        self.current_pos[0] = max(0, min(8, self.current_pos[0]))
        self.current_pos[1] = max(0, min(6, self.current_pos[1]))

    def create_measurement_data(self) -> dict:
        """創建測量數據"""
        anchors = []
        for anchor_id, pos in self.anchor_positions.items():
            distance = self.calculate_distance(pos, self.current_pos)
            noisy_distance = self.add_measurement_noise(distance)
            tof = noisy_distance / 299792458.0  # 光速（米/秒）
            anchors.append({
                "id": anchor_id[1],  # 只取數字部分
                "distance": noisy_distance,
                "tof": tof
            })

        return {
            "tag": "T1",
            "anchors": anchors
        }

    def run(self, movement_type="circle"):
        """運行模擬器"""
        print(f"Starting UWB Tag Simulator ({movement_type} movement)")
        print("Broadcasting to {}:{}".format(
            self.broadcast_ip, self.broadcast_port))
        
        try:
            while True:
                # 更新位置
                if movement_type == "circle":
                    self.update_position()
                else:
                    self.generate_random_movement()

                # 生成並發送數據
                data = self.create_measurement_data()
                json_data = json.dumps(data)
                self.sock.sendto(
                    json_data.encode(),
                    (self.broadcast_ip, self.broadcast_port)
                )

                # 顯示當前位置
                print(f"\rTag position: ({self.current_pos[0]:.2f}, "
                      f"{self.current_pos[1]:.2f})", end="")
                
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
    args = parser.parse_args()
    
    simulator = UWBTagSimulator()
    simulator.run(args.movement)
