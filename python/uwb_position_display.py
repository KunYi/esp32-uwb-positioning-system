#!/usr/bin/env python3
import socket
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
from typing import Dict, List, Tuple

class UWBPositionSystem:
    def __init__(self):
        # 設定 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 12345))
        self.sock.settimeout(0.1)  # 100ms timeout

        # Anchor 位置設定 (x, y) in meters
        self.anchor_positions = {
            'A1': (0.0, 0.0),    # 原點
            'A2': (8.0, 0.0),    # x軸 8m
            'A3': (4.0, 6.0),    # 中間上方 6m
        }

        # 初始化圖表
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.ax.set_xlim(-1, 9)
        self.ax.set_ylim(-1, 7)
        self.ax.grid(True)
        self.ax.set_title('UWB Position Tracking')
        self.ax.set_xlabel('X Position (meters)')
        self.ax.set_ylabel('Y Position (meters)')

        # 畫出 Anchor 位置
        for anchor_id, pos in self.anchor_positions.items():
            self.ax.plot(pos[0], pos[1], 'bs', markersize=10, label=anchor_id)
        self.ax.legend()

        # Tag 位置點
        self.tag_point, = self.ax.plot([], [], 'ro', markersize=10, label='Tag')
        self.tag_trail, = self.ax.plot([], [], 'r-', alpha=0.5)  # 軌跡線
        self.trail_x = []
        self.trail_y = []
        self.max_trail_points = 50  # 最多顯示50個歷史點

        # 距離文字顯示
        self.distance_texts = {}
        for anchor_id in self.anchor_positions:
            text = self.ax.text(0, 0, '', fontsize=8)
            self.distance_texts[anchor_id] = text

    def trilateration(self, distances: Dict[str, float]) -> Tuple[float, float]:
        """使用三邊測量法計算位置"""
        if len(distances) < 3:
            return None, None

        # 準備方程式係數
        A = []
        b = []
        
        # 選擇前三個 anchors
        anchor_ids = list(distances.keys())[:3]
        
        for i in range(2):  # 我們只需要兩個方程式
            anchor1 = self.anchor_positions[anchor_ids[i]]
            anchor2 = self.anchor_positions[anchor_ids[i+1]]
            r1 = distances[anchor_ids[i]]
            r2 = distances[anchor_ids[i+1]]
            
            # 建立方程式係數
            A.append([
                2 * (anchor2[0] - anchor1[0]),
                2 * (anchor2[1] - anchor1[1])
            ])
            
            b.append(
                r1*r1 - r2*r2 - 
                anchor1[0]*anchor1[0] - anchor1[1]*anchor1[1] +
                anchor2[0]*anchor2[0] + anchor2[1]*anchor2[1]
            )
        
        try:
            # 解聯立方程式
            position = np.linalg.solve(A, b)
            return position[0], position[1]
        except np.linalg.LinAlgError:
            return None, None

    def update_plot(self, frame):
        """更新圖表"""
        try:
            # 接收 UDP 數據
            data, addr = self.sock.recvfrom(1024)
            json_data = json.loads(data.decode())
            
            # 解析距離數據
            distances = {}
            for anchor in json_data['anchors']:
                anchor_id = f"A{anchor['id']}"
                if anchor_id in self.anchor_positions:
                    distances[anchor_id] = anchor['distance']

            # 計算位置
            x, y = self.trilateration(distances)
            
            if x is not None and y is not None:
                # 更新 Tag 位置
                self.tag_point.set_data([x], [y])
                
                # 更新軌跡
                self.trail_x.append(x)
                self.trail_y.append(y)
                if len(self.trail_x) > self.max_trail_points:
                    self.trail_x.pop(0)
                    self.trail_y.pop(0)
                self.tag_trail.set_data(self.trail_x, self.trail_y)

                # 更新距離文字
                for anchor_id, distance in distances.items():
                    anchor_pos = self.anchor_positions[anchor_id]
                    text_pos = (
                        (anchor_pos[0] + x) / 2,
                        (anchor_pos[1] + y) / 2
                    )
                    self.distance_texts[anchor_id].set_position(text_pos)
                    self.distance_texts[anchor_id].set_text(
                        f'{anchor_id}: {distance:.2f}m'
                    )

        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error: {e}")

        return (self.tag_point, self.tag_trail, 
                *self.distance_texts.values())

    def run(self):
        """運行動畫"""
        ani = FuncAnimation(
            self.fig, self.update_plot, interval=100,
            blit=True, cache_frame_data=False
        )
        plt.show()

if __name__ == "__main__":
    system = UWBPositionSystem()
    system.run()
