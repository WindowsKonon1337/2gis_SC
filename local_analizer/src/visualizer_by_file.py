#!/usr/bin/env python3
"""
Bus Signal Distribution Analyzer
- Анализ распределения сигналов в автобусе по RSSI
- Приемник установлен в задней части автобуса
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

class BusDistributionAnalyzer:
    def __init__(self, filename):
        self.filename = filename
        self.df = None
        self.df_filtered = None
        
        # Пороги для определения зон в автобусе
        self.location_thresholds = {
            'back': -50,      # Сильный сигнал - зад автобуса
            'middle': -65,    # Средний сигнал - середина
            'front': -85      # Слабый сигнал - перед
        }
        
    def load_data(self):
        """Загрузка данных из файла"""
        try:
            if self.filename.endswith('.csv'):
                self.df = pd.read_csv(self.filename)
                if 'datetime' in self.df.columns and 'rssi' in self.df.columns:
                    self.df['datetime'] = pd.to_datetime(self.df['datetime'])
                    
            elif self.filename.endswith('.txt'):
                data = []
                with open(self.filename, 'r') as f:
                    for line in f:
                        if ',' in line and 'rssi' not in line.lower():
                            parts = line.strip().split(',')
                            if len(parts) == 2:
                                try:
                                    dt = pd.to_datetime(parts[0])
                                    rssi = int(parts[1])
                                    data.append({'datetime': dt, 'rssi': rssi})
                                except:
                                    continue
                self.df = pd.DataFrame(data)
                
            if self.df.empty:
                return False
                
            # Сортируем по времени
            self.df = self.df.sort_values('datetime')
            
            # Фильтруем короткие остановки
            self.filter_short_stops()
            
            # Пересчитываем распределение с новыми порогами
            self.calculate_distribution()
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            return False

    def filter_short_stops(self, min_stop_duration=1):
        """
        Фильтрация коротких остановок (менее min_stop_duration минут)
        где автобус стоит и ловит много людей
        """
        if self.df is None or len(self.df) == 0:
            return
            
        print(f"Фильтрация коротких остановок (< {min_stop_duration} мин)...")
        
        self.df_filtered = self.df.copy()
        self.df_filtered['time_diff'] = self.df_filtered['datetime'].diff().dt.total_seconds().fillna(0)
        self.df_filtered['group'] = (self.df_filtered['time_diff'] > 30).cumsum()
        group_durations = self.df_filtered.groupby('group')['datetime'].agg(['min', 'max'])
        group_durations['duration'] = (group_durations['max'] - group_durations['min']).dt.total_seconds() / 60
        short_groups = group_durations[group_durations['duration'] < min_stop_duration].index
        initial_count = len(self.df_filtered)
        self.df_filtered = self.df_filtered[~self.df_filtered['group'].isin(short_groups)]
        filtered_count = len(self.df_filtered)
        self.df_filtered = self.df_filtered.drop(['time_diff', 'group'], axis=1)
    
    def update_thresholds(self, front=None, middle=None, back=None):
        if front is not None:
            self.location_thresholds['front'] = front
        if middle is not None:
            self.location_thresholds['middle'] = middle
        if back is not None:
            self.location_thresholds['back'] = back
            
        if self.df is not None:
            self.calculate_distribution()
    
    def calculate_distribution(self):
        """Расчет распределения сигналов по автобусу"""
        def get_location(rssi):
            if rssi > self.location_thresholds['back']:
                return 2, 'Back'      
            elif rssi > self.location_thresholds['middle']:
                return 1, 'Middle'    
            elif rssi > self.location_thresholds['front']:
                return 0, 'Front'     
            else:
                return -1, 'Noise'
        
        df_to_use = self.df_filtered if self.df_filtered is not None else self.df
        
        location_data = df_to_use['rssi'].apply(get_location)
        df_to_use['location_level'] = [x[0] for x in location_data]
        df_to_use['location_label'] = [x[1] for x in location_data]
    
    def group_similar_devices(self, df, rssi_threshold=5, time_window_seconds=2, max_packets=5):
        """
        Группирует пакеты от одного устройства.
        Если RSSI отличается не более чем на rssi_threshold в течение time_window_seconds
        и количество пакетов не более max_packets, то считаем это одним устройством.
        """
        if len(df) == 0:
            return df
            
        df_sorted = df.sort_values('datetime').copy()
        df_sorted['device_group'] = 0
        current_group = 1
        
        i = 0
        while i < len(df_sorted):
            current_time = df_sorted.iloc[i]['datetime']
            current_rssi = df_sorted.iloc[i]['rssi']
            
            # Находим пакеты в временном окне с похожим RSSI
            time_mask = (df_sorted['datetime'] >= current_time) & \
                       (df_sorted['datetime'] <= current_time + timedelta(seconds=time_window_seconds))
            rssi_mask = abs(df_sorted['rssi'] - current_rssi) <= rssi_threshold
            
            similar_packets = df_sorted[time_mask & rssi_mask]
            
            if len(similar_packets) <= max_packets:
                # Группируем эти пакеты как одно устройство
                df_sorted.loc[similar_packets.index, 'device_group'] = current_group
                i += len(similar_packets)
            else:
                # Слишком много пакетов - не группируем
                df_sorted.loc[df_sorted.index[i], 'device_group'] = current_group
                i += 1
                
            current_group += 1
        
        # Оставляем только по одному представителю от каждой группы
        unique_devices = df_sorted.groupby('device_group').first().reset_index()
        return unique_devices
    
    def generate_summary(self):
        """Генерация сводки по распределению"""
        df_to_use = self.df_filtered if self.df_filtered is not None else self.df
        
        if df_to_use is None:
            return
            
        duration = (df_to_use['datetime'].max() - df_to_use['datetime'].min()).total_seconds() / 60
        
        print("\n" + "="*60)
        print("АНАЛИЗ РАСПРЕДЕЛЕНИЯ СИГНАЛОВ В АВТОБУСЕ")
        print("="*60)
        print(f"Приемник установлен: ЗАД автобуса")
        print(f"Период анализа: {duration:.1f} минут")
        print(f"Всего измерений RSSI: {len(df_to_use)}")
        if self.df_filtered is not None:
            print(f"Исходные измерения: {len(self.df)} (фильтрация применена)")
        print(f"Средний RSSI: {df_to_use['rssi'].mean():.1f} dBm")
        print(f"Используемые пороги: Front={self.location_thresholds['front']}, "
              f"Middle={self.location_thresholds['middle']}, Back={self.location_thresholds['back']}")
        
        valid_signals = df_to_use[df_to_use['location_level'] >= 0]
        total_valid = len(valid_signals)
        
        zone_stats = {
            'Front': len(valid_signals[valid_signals['location_level'] == 0]),
            'Middle': len(valid_signals[valid_signals['location_level'] == 1]),
            'Back': len(valid_signals[valid_signals['location_level'] == 2]),
            'Noise': len(df_to_use[df_to_use['location_level'] == -1])
        }
        
        print(f"\n--- РАСПРЕДЕЛЕНИЕ СИГНАЛОВ ПО ЗОНАМ ---")
        print(f"Всего валидных сигналов: {total_valid}")
        print(f"Шум/потери: {zone_stats['Noise']}")
        
        for zone in ['Front', 'Middle', 'Back']:
            count = zone_stats[zone]
            percentage = (count / total_valid) * 100 if total_valid > 0 else 0
            print(f"{zone:<6}: {count:>5} измерений ({percentage:5.1f}%)")
        
        if total_valid > 0:
            back_ratio = zone_stats['Back'] / total_valid
            if back_ratio > 0.6:
                print(f"\nПРЕОБЛАДАЮЩИЙ СИГНАЛ: ЗАДНЯЯ часть автобуса")
            elif back_ratio < 0.3:
                print(f"\nПРЕОБЛАДАЮЩИЙ СИГНАЛ: ПЕРЕДНЯЯ часть автобуса") 
            else:
                print(f"\nРАСПРЕДЕЛЕНИЕ СИГНАЛОВ: СМЕШАННОЕ")
    
    def plot_total_devices_per_minute(self):
        """График суммарного количества устройств за минуту (с группировкой пакетов)"""
        if self.df_filtered is None:
            return
            
        df_to_use = self.df_filtered
        valid_signals = df_to_use[df_to_use['location_level'] >= 0]
        
        if len(valid_signals) == 0:
            print("Нет валидных сигналов для анализа")
            return
        
        # Группируем пакеты по устройствам
        print("Группировка пакетов по устройствам...")
        unique_devices = self.group_similar_devices(valid_signals)
        
        print(f"Всего пакетов: {len(valid_signals)}")
        
        # Группируем устройства по минутам
        devices_per_minute = unique_devices.groupby(
            pd.Grouper(key='datetime', freq='1T')
        ).size()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(devices_per_minute.index, devices_per_minute.values, 
               color='blue', linewidth=2, marker='o', markersize=4, label='Устройства')
        
        ax.set_xlabel('Время', fontweight='bold')
        ax.set_ylabel('Количество сигналов в минуту', fontweight='bold')
        ax.set_title('Качественное количество устройств за минуту', fontweight='bold', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        
        if len(devices_per_minute) > 0:
            ax.legend()
        
        plt.tight_layout()
        plt.show()
    
    def plot_distribution_analysis(self):
        """Визуализация распределения сигналов"""
        df_to_use = self.df_filtered if self.df_filtered is not None else self.df
        
        if df_to_use is None:
            return
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        if self.df_filtered is not None:
            fig.suptitle(f'Bus Signal Distribution Analysis (Filtered)', fontsize=16, fontweight='bold')
        else:
            fig.suptitle(f'Bus Signal Distribution Analysis', fontsize=16, fontweight='bold')
        
        # 1. График RSSI с пороговыми линиями
        ax1.scatter(df_to_use['datetime'], df_to_use['rssi'], c='blue', alpha=0.6, s=20, label='RSSI сигнал')
        
        # Добавляем пороговые линии
        colors = ['red', 'orange', 'green']
        zones = ['Front', 'Middle', 'Back']
        thresholds = [self.location_thresholds['front'], 
                     self.location_thresholds['middle'], 
                     self.location_thresholds['back']]
        
        for i, (threshold, color, zone) in enumerate(zip(thresholds, colors, zones)):
            ax1.axhline(y=threshold, color=color, linestyle='--', linewidth=2,
                       alpha=0.7, label=f'{zone} zone ({threshold} dBm)')
        
        ax1.set_ylabel('RSSI (dBm)', fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_title('RSSI Signal Strength and Bus Zones', fontweight='bold')
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. Схема автобуса
        valid_signals = df_to_use[df_to_use['location_level'] >= 0]
        zone_counts = valid_signals['location_label'].value_counts()
        self.plot_bus_schematic(ax2, zone_counts)
        
        plt.tight_layout()
        plt.show()
        
        # 3. Суммарное количество устройств за минуту
        self.plot_total_devices_per_minute()
    
    def plot_bus_schematic(self, ax, zone_counts):
        """Схематичное изображение автобуса с заполнением"""
        bus_length = 12
        bus_width = 3
        
        total = sum(zone_counts.values) if len(zone_counts) > 0 else 1
        fill_levels = {
            'Front': zone_counts.get('Front', 0) / total,
            'Middle': zone_counts.get('Middle', 0) / total, 
            'Back': zone_counts.get('Back', 0) / total
        }
        
        # Рисуем контур автобуса
        ax.add_patch(plt.Rectangle((0, 0), bus_length, bus_width, 
                                 fill=False, edgecolor='black', linewidth=2))
        
        zone_width = bus_length / 3
        zones_order = ['Front', 'Middle', 'Back'] 
        colors = ['red', 'orange', 'green']
        
        for i, (zone, color) in enumerate(zip(zones_order, colors)):
            x_start = i * zone_width
            fill_height = fill_levels[zone] * bus_width
            
            ax.add_patch(plt.Rectangle((x_start, 0), zone_width, fill_height,
                                     facecolor=color, alpha=0.6, edgecolor='black'))
            
            ax.text(x_start + zone_width/2, bus_width/2, zone, 
                   ha='center', va='center', fontweight='bold', fontsize=12)
            
            ax.text(x_start + zone_width/2, -0.5, f'{fill_levels[zone]*100:.1f}%',
                   ha='center', va='center', fontsize=10, fontweight='bold')
        
        ax.plot(bus_length, bus_width/2, 'ro', markersize=10)
        ax.text(bus_length + 0.5, bus_width/2, 'Приемник', va='center', fontweight='bold')
        
        ax.arrow(-0.5, bus_width/2, 0.3, 0, head_width=0.3, head_length=0.2, 
                fc='black', ec='black')
        ax.text(-0.8, bus_width/2 + 0.5, 'Направление', rotation=90, 
               va='center', ha='center', fontsize=9)
        
        ax.set_xlim(-1, bus_length + 2)
        ax.set_ylim(-1, bus_width + 1.5)
        ax.set_aspect('equal')
        ax.set_title(f'Bus Signal Distribution', fontweight='bold')
        ax.axis('off')

def main():
    filename = "bus_evening.csv" 
    
    analyzer = BusDistributionAnalyzer(filename)
    
    if analyzer.load_data():
        analyzer.generate_summary()
        analyzer.plot_distribution_analysis()

if __name__ == "__main__":
    main()