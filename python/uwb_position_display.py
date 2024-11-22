#!/usr/bin/env python3
import socket
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D  # 3D support
import time
from typing import Dict, List, Tuple
import random
import colorsys

class UWBPositionSystem:
    def __init__(self):
        # 設定 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 12345))
        self.sock.settimeout(0.1)  # 100ms timeout

        # Anchor 位置設定 (x, y, z) in meters
        self.anchor_positions = {
            'A1': (0.0, 0.0, 0.0),    # 原點
            'A2': (8.0, 0.0, 0.0),    # x軸 8m
            'A3': (4.0, 6.0, 0.0),    # y軸 6m
            'A4': (4.0, 3.0, 3.0),    # 上方 3m
        }

        # 創建主視窗和子圖表
        self.fig = plt.figure(figsize=(15, 8))
        self.create_2d_plot()
        self.create_3d_plot()

        # Tag 追蹤數據
        self.tags = {}  # 儲存所有 tag 的數據
        self.tag_colors = {}  # 儲存 tag 的顏色
        self.max_trail_points = 50  # 最多顯示50個歷史點

        plt.tight_layout()

    def create_2d_plot(self):
        """創建 2D 視圖"""
        self.ax2d = self.fig.add_subplot(121)
        self.ax2d.set_xlim(-1, 9)
        self.ax2d.set_ylim(-1, 7)
        self.ax2d.grid(True)
        self.ax2d.set_title('2D Position Tracking')
        self.ax2d.set_xlabel('X Position (meters)')
        self.ax2d.set_ylabel('Y Position (meters)')

        # 畫出 2D Anchor 位置
        for anchor_id, pos in self.anchor_positions.items():
            self.ax2d.plot(pos[0], pos[1], 'bs', markersize=10, label=anchor_id)
        self.ax2d.legend()

    def create_3d_plot(self):
        """創建 3D 視圖"""
        self.ax3d = self.fig.add_subplot(122, projection='3d')
        self.ax3d.set_xlim(-1, 9)
        self.ax3d.set_ylim(-1, 7)
        self.ax3d.set_zlim(0, 4)
        self.ax3d.grid(True)
        self.ax3d.set_title('3D Position Tracking')
        self.ax3d.set_xlabel('X Position (meters)')
        self.ax3d.set_ylabel('Y Position (meters)')
        self.ax3d.set_zlabel('Z Position (meters)')

        # 畫出 3D Anchor 位置
        for anchor_id, pos in self.anchor_positions.items():
            self.ax3d.scatter(pos[0], pos[1], pos[2], c='b', marker='s', s=100)

    def get_tag_color(self, tag_id):
        """為每個 tag 生成唯一的顏色"""
        if tag_id not in self.tag_colors:
            # 使用 HSV 顏色空間生成均勻分布的顏色
            hue = random.random()
            self.tag_colors[tag_id] = colorsys.hsv_to_rgb(hue, 0.8, 0.8)
        return self.tag_colors[tag_id]

    def init_tag(self, tag_id):
        """初始化新的 tag 數據結構"""
        color = self.get_tag_color(tag_id)

        # 2D 視圖元素
        point2d, = self.ax2d.plot([], [], 'o', markersize=10, color=color, label=f'Tag {tag_id}')
        trail2d, = self.ax2d.plot([], [], '-', alpha=0.5, color=color)

        # 3D 視圖元素
        point3d, = self.ax3d.plot3D([], [], [], 'o', markersize=10, color=color)
        trail3d = self.ax3d.plot([], [], [], '-', alpha=0.5, color=color)[0]

        self.tags[tag_id] = {
            '2d': {'point': point2d, 'trail': trail2d},
            '3d': {'point': point3d, 'trail': trail3d},
            'trail_x': [], 'trail_y': [], 'trail_z': []
        }

        # 更新圖例
        self.ax2d.legend()

    def trilateration_3d(self, distances: Dict[str, float]) -> Tuple[float, float, float]:
        """使用三邊測量法計算 3D 位置"""
        if len(distances) < 4:  # 需要至少4個 anchor 進行 3D 定位
            return None, None, None

        # 準備最小二乘法方程式
        A = []
        b = []

        anchor_ids = list(distances.keys())
        reference = anchor_ids[0]
        ref_pos = self.anchor_positions[reference]
        ref_dist = distances[reference]

        for i in range(1, len(anchor_ids)):
            current = anchor_ids[i]
            curr_pos = self.anchor_positions[current]
            curr_dist = distances[current]

            # 建立方程式係數
            A.append([
                2 * (curr_pos[0] - ref_pos[0]),
                2 * (curr_pos[1] - ref_pos[1]),
                2 * (curr_pos[2] - ref_pos[2])
            ])

            b.append(
                ref_dist*ref_dist - curr_dist*curr_dist -
                ref_pos[0]*ref_pos[0] - ref_pos[1]*ref_pos[1] - ref_pos[2]*ref_pos[2] +
                curr_pos[0]*curr_pos[0] + curr_pos[1]*curr_pos[1] + curr_pos[2]*curr_pos[2]
            )

        try:
            # 使用最小二乘法求解
            position = np.linalg.lstsq(A, b, rcond=None)[0]
            return position[0], position[1], position[2]
        except np.linalg.LinAlgError:
            return None, None, None

    def update_plot(self, frame):
        """更新圖表"""
        try:
            # 接收 UDP 數據
            data, addr = self.sock.recvfrom(1024)
            json_data = json.loads(data.decode())

            # 解析數據
            tag_id = json_data.get('tag_id', '1')  # 如果沒有 tag_id，默認為 '1'
            if tag_id not in self.tags:
                self.init_tag(tag_id)

            # 解析距離數據
            distances = {}
            for anchor in json_data['anchors']:
                anchor_id = f"A{anchor['id']}"
                if anchor_id in self.anchor_positions:
                    distances[anchor_id] = anchor['distance']

            # 計算 3D 位置
            x, y, z = self.trilateration_3d(distances)

            if x is not None and y is not None and z is not None:
                tag_data = self.tags[tag_id]

                # 更新軌跡數據
                tag_data['trail_x'].append(x)
                tag_data['trail_y'].append(y)
                tag_data['trail_z'].append(z)
                if len(tag_data['trail_x']) > self.max_trail_points:
                    tag_data['trail_x'].pop(0)
                    tag_data['trail_y'].pop(0)
                    tag_data['trail_z'].pop(0)

                # 更新 2D 視圖
                tag_data['2d']['point'].set_data([x], [y])
                tag_data['2d']['trail'].set_data(tag_data['trail_x'], tag_data['trail_y'])

                # 更新 3D 視圖
                tag_data['3d']['point'].set_data_3d([x], [y], [z])
                tag_data['3d']['trail'].set_data_3d(
                    tag_data['trail_x'],
                    tag_data['trail_y'],
                    tag_data['trail_z']
                )

        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error: {e}")

        # 返回所有需要更新的圖形元素
        plot_elements = []
        for tag_data in self.tags.values():
            plot_elements.extend([
                tag_data['2d']['point'],
                tag_data['2d']['trail'],
                tag_data['3d']['point'],
                tag_data['3d']['trail']
            ])
        return plot_elements

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
