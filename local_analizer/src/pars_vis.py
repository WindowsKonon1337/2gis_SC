#!/usr/bin/env python3
"""
Bus Signal Distribution Analyzer - Real-time COM port version
- Анализ распределения сигналов в автобусе по RSSI в реальном времени
- Приемник установлен в задней части автобуса
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Используем бэкенд без GUI для избежания проблем с Tkinter
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import serial
import serial.tools.list_ports
import threading
import time
import queue
import os

class BusDistributionAnalyzer:
    def __init__(self, com_port='/dev/ttyUSB0', baudrate=115200, output_dir='results'):
        self.com_port = com_port
        self.baudrate = baudrate
        self.output_dir = output_dir
        self.serial_connection = None
        self.data_queue = queue.Queue()
        self.df = pd.DataFrame(columns=['datetime', 'rssi'])
        self.is_collecting = False
        self.collection_thread = None
        
        # Создаем директорию для результатов
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.location_thresholds = {
            'back': -50,
            'middle': -65,
            'front': -85
        }
        
    def connect_serial(self):
        try:
            self.serial_connection = serial.Serial(
                port=self.com_port,
                baudrate=self.baudrate,
                timeout=1
            )
            print(f"Подключено к {self.com_port}")
            return True
        except Exception as e:
            print(f"Ошибка подключения к {self.com_port}: {e}")
            return False
    
    def start_data_collection(self, collection_minutes=1):
        if not self.connect_serial():
            return False
        
        self.is_collecting = True
        self.collection_start_time = datetime.now()
        self.collection_duration = collection_minutes
        
        self.df = pd.DataFrame(columns=['datetime', 'rssi'])
        self.data_queue = queue.Queue()
        
        self.collection_thread = threading.Thread(target=self._read_serial_data)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        
        print(f"Начат сбор данных на {collection_minutes} минут...")
        return True
    
    def _read_serial_data(self):
        buffer = ""
        while self.is_collecting:
            try:
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            self._process_data_line(line)
                
                if (datetime.now() - self.collection_start_time).total_seconds() >= self.collection_duration * 60:
                    self.is_collecting = False
                    break
                    
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Ошибка чтения данных: {e}")
                break
    
    def _process_data_line(self, line):
        try:
            # Пропускаем служебные сообщения ESP32 и ошибки WiFi
            if (line.startswith("RSSI_COLLECTOR_START") or 
                line.startswith("Format:") or 
                line.startswith("ERROR:") or
                line.startswith("E (") or  # Пропускаем ошибки WiFi
                "wifi:failed to post WiFi event" in line):
                return
                
            if ',' in line:
                parts = line.split(',')
                if len(parts) == 2:
                    timestamp_str = parts[0].strip()
                    rssi_str = parts[1].strip()
                    
                    try:
                        # Конвертируем timestamp из миллисекунд в datetime
                        timestamp_ms = int(timestamp_str)
                        # Базовое время - начало сбора данных
                        dt = self.collection_start_time + timedelta(milliseconds=timestamp_ms)
                    except:
                        dt = datetime.now()
                    
                    rssi = int(rssi_str)
                    
                    new_data = pd.DataFrame({
                        'datetime': [dt],
                        'rssi': [rssi]
                    })
                    
                    # Исправляем предупреждение pandas
                    if not self.df.empty:
                        self.df = pd.concat([self.df, new_data], ignore_index=True)
                    else:
                        self.df = new_data.copy()
                        
                    self.data_queue.put(new_data)
                    
            else:
                # Если только RSSI значение (старый формат)
                rssi = int(line.strip())
                new_data = pd.DataFrame({
                    'datetime': [datetime.now()],
                    'rssi': [rssi]
                })
                
                # Исправляем предупреждение pandas
                if not self.df.empty:
                    self.df = pd.concat([self.df, new_data], ignore_index=True)
                else:
                    self.df = new_data.copy()
                    
                self.data_queue.put(new_data)
                
        except ValueError:
            # Тихий пропуск некорректных данных (не выводим сообщение)
            pass
        except Exception as e:
            # Тихий пропуск других ошибок
            pass
    
    def wait_for_collection_complete(self):
        if self.collection_thread:
            self.collection_thread.join()
        print(f"Сбор данных завершен. Собрано {len(self.df)} измерений")
    
    def stop_data_collection(self):
        self.is_collecting = False
        if self.serial_connection:
            self.serial_connection.close()
    
    def filter_short_stops(self, min_stop_duration=1):
        if self.df is None or len(self.df) == 0:
            return
            
        print(f"Фильтрация коротких остановок (< {min_stop_duration} мин)...")
        
        df_filtered = self.df.copy()
        df_filtered['time_diff'] = df_filtered['datetime'].diff().dt.total_seconds().fillna(0)
        df_filtered['group'] = (df_filtered['time_diff'] > 30).cumsum()
        group_durations = df_filtered.groupby('group')['datetime'].agg(['min', 'max'])
        group_durations['duration'] = (group_durations['max'] - group_durations['min']).dt.total_seconds() / 60
        short_groups = group_durations[group_durations['duration'] < min_stop_duration].index
        df_filtered = df_filtered[~df_filtered['group'].isin(short_groups)]
        df_filtered = df_filtered.drop(['time_diff', 'group'], axis=1)
        
        return df_filtered
    
    def calculate_distribution(self, df):
        def get_location(rssi):
            if rssi > self.location_thresholds['back']:
                return 2, 'Back'      
            elif rssi > self.location_thresholds['middle']:
                return 1, 'Middle'    
            elif rssi > self.location_thresholds['front']:
                return 0, 'Front'     
            else:
                return -1, 'Noise'
        
        location_data = df['rssi'].apply(get_location)
        df['location_level'] = [x[0] for x in location_data]
        df['location_label'] = [x[1] for x in location_data]
        return df
    
    def group_similar_devices(self, df, rssi_threshold=5, time_window_seconds=2, max_packets=5):
        if len(df) == 0:
            return df
            
        df_sorted = df.sort_values('datetime').copy()
        df_sorted['device_group'] = 0
        current_group = 1
        
        i = 0
        while i < len(df_sorted):
            current_time = df_sorted.iloc[i]['datetime']
            current_rssi = df_sorted.iloc[i]['rssi']
            
            time_mask = (df_sorted['datetime'] >= current_time) & \
                       (df_sorted['datetime'] <= current_time + timedelta(seconds=time_window_seconds))
            rssi_mask = abs(df_sorted['rssi'] - current_rssi) <= rssi_threshold
            
            similar_packets = df_sorted[time_mask & rssi_mask]
            
            if len(similar_packets) <= max_packets:
                df_sorted.loc[similar_packets.index, 'device_group'] = current_group
                i += len(similar_packets)
            else:
                df_sorted.loc[df_sorted.index[i], 'device_group'] = current_group
                i += 1
                
            current_group += 1
        
        unique_devices = df_sorted.groupby('device_group').first().reset_index()
        return unique_devices

    def save_data_to_csv(self, df, cycle_count):
        """Сохраняет собранные данные в CSV файл"""
        if df is None or len(df) == 0:
            print("Нет данных для сохранения")
            return
        
        filename = f"{self.output_dir}/collected_data_cycle_{cycle_count}.csv"
        
        # Создаем копию с форматированием времени
        save_df = df.copy()
        save_df['timestamp'] = save_df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # Сохраняем только нужные колонки
        save_df[['timestamp', 'rssi', 'location_label']].to_csv(filename, index=False)
        print(f"Данные сохранены в таблицу: {filename}")
        
        # Также сохраняем сводную статистику
        stats_filename = f"{self.output_dir}/summary_stats_cycle_{cycle_count}.csv"
        if len(df) > 0:
            stats = {
                'cycle': [cycle_count],
                'start_time': [df['datetime'].min().strftime('%Y-%m-%d %H:%M:%S')],
                'end_time': [df['datetime'].max().strftime('%Y-%m-%d %H:%M:%S')],
                'total_measurements': [len(df)],
                'mean_rssi': [df['rssi'].mean()],
                'min_rssi': [df['rssi'].min()],
                'max_rssi': [df['rssi'].max()],
                'front_signals': [len(df[df['location_label'] == 'Front'])],
                'middle_signals': [len(df[df['location_label'] == 'Middle'])],
                'back_signals': [len(df[df['location_label'] == 'Back'])],
                'noise_signals': [len(df[df['location_label'] == 'Noise'])]
            }
            pd.DataFrame(stats).to_csv(stats_filename, index=False)
            print(f"Статистика сохранена: {stats_filename}")
    
    def generate_summary(self, df, cycle_count):
        if df is None or len(df) == 0:
            return
            
        duration = (df['datetime'].max() - df['datetime'].min()).total_seconds() / 60
        
        print("\n" + "="*60)
        print("АНАЛИЗ РАСПРЕДЕЛЕНИЯ СИГНАЛОВ В АВТОБУСЕ")
        print("="*60)
        print(f"Период анализа: {duration:.1f} минут")
        print(f"Всего измерений RSSI: {len(df)}")
        print(f"Средний RSSI: {df['rssi'].mean():.1f} dBm")
        print(f"Используемые пороги: Front={self.location_thresholds['front']}, "
              f"Middle={self.location_thresholds['middle']}, Back={self.location_thresholds['back']}")
        
        valid_signals = df[df['location_level'] >= 0]
        total_valid = len(valid_signals)
        
        zone_stats = {
            'Front': len(valid_signals[valid_signals['location_level'] == 0]),
            'Middle': len(valid_signals[valid_signals['location_level'] == 1]),
            'Back': len(valid_signals[valid_signals['location_level'] == 2]),
            'Noise': len(df[df['location_level'] == -1])
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
    
    def plot_total_devices_per_minute(self, df, cycle_count):
        if df is None or len(df) == 0:
            return
        
        valid_signals = df[df['location_level'] >= 0]
        
        if len(valid_signals) == 0:
            print("Нет валидных сигналов для анализа")
            return
        
        print("Группировка пакетов по устройствам...")
        unique_devices = self.group_similar_devices(valid_signals)
        
        print(f"Всего пакетов: {len(valid_signals)}")
        print(f"Уникальных устройств: {len(unique_devices)}")
        
        # ИСПРАВЛЕНО: Заменяем 'T' на 'min' чтобы убрать предупреждение
        devices_per_minute = unique_devices.groupby(
            pd.Grouper(key='datetime', freq='1min')
        ).size()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(devices_per_minute.index, devices_per_minute.values, 
               color='blue', linewidth=2, marker='o', markersize=4, label='Устройства')
        
        ax.set_xlabel('Время', fontweight='bold')
        ax.set_ylabel('Количество устройств в минуту', fontweight='bold')
        ax.set_title('Качественное количество устройств за минуту', fontweight='bold', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        
        if len(devices_per_minute) > 0:
            ax.legend()
        
        # Сохраняем график
        filename = f"{self.output_dir}/devices_per_minute_cycle_{cycle_count}.png"
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"График сохранен: {filename}")
    
    def plot_distribution_analysis(self, df, cycle_count):
        if df is None or len(df) == 0:
            print("Нет данных для визуализации")
            return
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        fig.suptitle(f'Bus Signal Distribution Analysis - Real-time Data (Cycle {cycle_count})', fontsize=16, fontweight='bold')
        
        ax1.scatter(df['datetime'], df['rssi'], c='blue', alpha=0.6, s=20, label='RSSI сигнал')
        
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
        
        valid_signals = df[df['location_level'] >= 0]
        zone_counts = valid_signals['location_label'].value_counts()
        self.plot_bus_schematic(ax2, zone_counts)
        
        # Сохраняем основной график
        filename = f"{self.output_dir}/distribution_analysis_cycle_{cycle_count}.png"
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"График распределения сохранен: {filename}")
        
        self.plot_total_devices_per_minute(df, cycle_count)
    
    def plot_bus_schematic(self, ax, zone_counts):
        bus_length = 12
        bus_width = 3
        
        total = sum(zone_counts.values) if len(zone_counts) > 0 else 1
        fill_levels = {
            'Front': zone_counts.get('Front', 0) / total,
            'Middle': zone_counts.get('Middle', 0) / total, 
            'Back': zone_counts.get('Back', 0) / total
        }
        
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
    
    def run_continuous_analysis(self, collection_minutes=1, cycles=None):
        cycle_count = 0
        
        try:
            while True:
                if cycles and cycle_count >= cycles:
                    break
                    
                cycle_count += 1
                print(f"\nЦикл анализа #{cycle_count}")
                print("-" * 50)
                
                # ИСПРАВЛЕНО: Убедимся что передается правильное время
                if not self.start_data_collection(collection_minutes):
                    break
                
                self.wait_for_collection_complete()
                
                if len(self.df) == 0:
                    print("Данные не получены. Пропускаем цикл.")
                    continue
                
                df_filtered = self.filter_short_stops()
                df_processed = self.calculate_distribution(df_filtered if df_filtered is not None else self.df)
                
                # СОХРАНЕНИЕ ДАННЫХ В ТАБЛИЦУ
                self.save_data_to_csv(df_processed, cycle_count)
                
                self.generate_summary(df_processed, cycle_count)
                self.plot_distribution_analysis(df_processed, cycle_count)
                
                print(f"\nЦикл #{cycle_count} завершен. Ожидание следующего цикла...")
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\nАнализ остановлен пользователем")
        finally:
            self.stop_data_collection()

def main():
    analyzer = BusDistributionAnalyzer(com_port='/dev/ttyUSB0', output_dir='results')
    
    analyzer.run_continuous_analysis(collection_minutes=2)

if __name__ == "__main__":
    main()