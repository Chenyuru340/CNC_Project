# D:\cnc_project\utils\data_validator.py
import pandas as pd
import numpy as np
import json
from datetime import datetime
import os


class DataValidator:
    """数据验证器 - 用于验证采集组的数据格式"""

    def __init__(self, expected_format=None):
        """初始化验证器"""
        # 前端期望的数据格式（基于你的mock数据）
        self.expected_format = expected_format or {
            'required_columns': [
                'tool_id',  # 格式: T-001, T-002
                'machine',  # 格式: 机床_1, 机床_2
                'timestamp',  # ISO格式: 2024-03-29 10:30:00
                'vibration',  # 数值型，单位mm/s
                'temperature',  # 数值型，单位°C
                'current',  # 可选：电流
                'power',  # 可选：功率
                'feed_rate'  # 可选：进给率
            ],
            'tool_id_pattern': r'^T-\d{3}$',
            'machine_pattern': r'^机床_\d+$',
            'value_ranges': {
                'vibration': (0.1, 10.0),  # 合理振动范围
                'temperature': (20, 100),  # 合理温度范围
                'current': (0, 50),  # 合理电流范围
                'power': (0, 10),  # 合理功率范围
                'feed_rate': (0, 500)  # 合理进给率
            }
        }

    def validate_csv(self, csv_path, sample_size=100):
        """验证CSV文件格式"""
        print(f"正在验证文件: {csv_path}")
        print("=" * 50)

        results = {
            'file_exists': False,
            'readable': False,
            'columns_match': False,
            'data_quality': {},
            'issues': [],
            'suggestions': []
        }

        try:
            # 1. 检查文件是否存在
            if not os.path.exists(csv_path):
                results['issues'].append(f"文件不存在: {csv_path}")
                return results

            results['file_exists'] = True

            # 2. 尝试读取CSV
            try:
                df = pd.read_csv(csv_path, nrows=sample_size)
                results['readable'] = True
                print(f"成功读取 {len(df)} 行数据")
            except Exception as e:
                results['issues'].append(f"无法读取CSV: {str(e)}")
                return results

            # 3. 检查列名
            current_columns = set(df.columns)
            required_columns = set(self.expected_format['required_columns'][:5])  # 前5列为必需

            missing_columns = required_columns - current_columns
            extra_columns = current_columns - set(self.expected_format['required_columns'])

            if missing_columns:
                results['issues'].append(f"缺少必需列: {missing_columns}")
            else:
                results['columns_match'] = True
                print("✓ 列名验证通过")

            if extra_columns:
                results['suggestions'].append(f"额外列（可能无用）: {extra_columns}")

            # 4. 检查数据格式和质量
            for col in df.columns:
                if col in df.columns:
                    col_info = {
                        'dtype': str(df[col].dtype),
                        'missing_count': df[col].isnull().sum(),
                        'unique_count': df[col].nunique(),
                        'sample_values': df[col].head(3).tolist() if df[col].dtype != 'float64' else []
                    }

                    # 特殊格式检查
                    if col == 'tool_id':
                        valid_format = df[col].astype(str).str.match(self.expected_format['tool_id_pattern'])
                        invalid_samples = df[col][-valid_format].head(5).tolist()
                        if invalid_samples:
                            results['issues'].append(f"tool_id格式错误示例: {invalid_samples}")
                        else:
                            print(f"✓ {col} 格式验证通过")

                    elif col == 'machine':
                        valid_format = df[col].astype(str).str.match(self.expected_format['machine_pattern'])
                        invalid_samples = df[col][-valid_format].head(5).tolist()
                        if invalid_samples:
                            results['issues'].append(f"machine格式错误示例: {invalid_samples}")
                        else:
                            print(f"✓ {col} 格式验证通过")

                    elif col == 'timestamp':
                        # 尝试解析时间戳
                        try:
                            pd.to_datetime(df[col])
                            print(f"✓ {col} 时间格式验证通过")
                        except:
                            results['issues'].append(f"timestamp格式无法解析")

                    elif col in self.expected_format['value_ranges']:
                        # 检查数值范围
                        min_val, max_val = self.expected_format['value_ranges'][col]
                        out_of_range = df[(df[col] < min_val) | (df[col] > max_val)]
                        if not out_of_range.empty:
                            results['issues'].append(
                                f"{col} 有 {len(out_of_range)} 个值超出合理范围({min_val}-{max_val})")
                        else:
                            print(f"✓ {col} 数值范围验证通过")

                    results['data_quality'][col] = col_info

            # 5. 检查数据完整性
            total_rows = len(df)
            for col in required_columns:
                if col in df.columns:
                    missing_pct = (df[col].isnull().sum() / total_rows) * 100
                    if missing_pct > 10:  # 超过10%缺失
                        results['issues'].append(f"{col} 缺失率过高: {missing_pct:.1f}%")

            # 6. 生成数据预览
            print("\n数据预览:")
            print(df.head())

            # 7. 统计信息
            print("\n基本统计信息:")
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                print(df[numeric_cols].describe())

        except Exception as e:
            results['issues'].append(f"验证过程中出错: {str(e)}")

        return results

    def generate_test_data(self, output_path="test_data.csv", num_rows=100):
        """生成测试用的CSV数据（符合格式要求）"""
        import random
        from datetime import datetime, timedelta

        data = []
        base_time = datetime.now()

        for i in range(num_rows):
            tool_id = f"T-{random.randint(1, 20):03d}"
            machine = f"机床_{random.randint(1, 5)}"
            timestamp = (base_time - timedelta(minutes=random.randint(0, 1000))).strftime("%Y-%m-%d %H:%M:%S")

            row = {
                'tool_id': tool_id,
                'machine': machine,
                'timestamp': timestamp,
                'vibration': round(random.uniform(0.1, 5.0), 2),
                'temperature': round(random.uniform(20.0, 80.0), 1),
                'current': round(random.uniform(5.0, 30.0), 1) if random.random() > 0.3 else None,
                'power': round(random.uniform(1.0, 8.0), 1) if random.random() > 0.3 else None,
                'feed_rate': round(random.uniform(100.0, 400.0), 1) if random.random() > 0.3 else None
            }
            data.append(row)

        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"测试数据已生成: {output_path}")
        print(f"行数: {len(df)}")
        print(f"列名: {list(df.columns)}")
        return output_path

    def compare_with_mock(self, csv_path):
        """与mock数据格式对比"""
        from data.mock_data import generate_mock_data

        # 获取mock数据格式
        mock_data = generate_mock_data()
        mock_tools = mock_data['tools']

        # 读取CSV数据
        try:
            df = pd.read_csv(csv_path, nrows=50)

            print("格式对比报告:")
            print("=" * 50)

            # 1. 检查tool_id格式
            mock_tool_ids = set(mock_tools['id'].unique())
            csv_tool_ids = set(df['tool_id'].unique()) if 'tool_id' in df.columns else set()

            print(f"Mock数据中的tool_id格式: {list(mock_tool_ids)[:5]}")
            print(f"CSV数据中的tool_id格式: {list(csv_tool_ids)[:5]}")

            # 2. 检查machine格式
            mock_machines = set(mock_tools['machine'].unique())
            csv_machines = set(df['machine'].unique()) if 'machine' in df.columns else set()

            print(f"\nMock数据中的machine格式: {list(mock_machines)}")
            print(f"CSV数据中的machine格式: {list(csv_machines)}")

            # 3. 检查数值范围
            if 'vibration' in df.columns:
                mock_vib_range = (mock_tools['vibration'].min(), mock_tools['vibration'].max())
                csv_vib_range = (df['vibration'].min(), df['vibration'].max())
                print(f"\n振动范围对比: Mock{mock_vib_range} vs CSV{csv_vib_range}")

            if 'temperature' in df.columns:
                mock_temp_range = (mock_tools['temperature'].min(), mock_tools['temperature'].max())
                csv_temp_range = (df['temperature'].min(), df['temperature'].max())
                print(f"温度范围对比: Mock{mock_temp_range} vs CSV{csv_temp_range}")

            return True

        except Exception as e:
            print(f"对比失败: {str(e)}")
            return False


def main():
    """主测试函数"""
    validator = DataValidator()

    print("数控机床刀具数据验证工具")
    print("=" * 60)

    # 选项菜单
    print("请选择操作:")
    print("1. 验证数据采集组提供的CSV文件")
    print("2. 生成测试CSV文件")
    print("3. 与Mock数据格式对比")
    print("4. 验证所有功能")

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice == "1":
        # 验证CSV文件
        csv_path = input("请输入CSV文件路径: ").strip()
        if not csv_path:
            csv_path = r"D:\cnc_project\data\采集组数据.csv"  # 默认路径

        results = validator.validate_csv(csv_path)

        print("\n" + "=" * 50)
        print("验证结果汇总:")
        print(f"文件存在: {'✓' if results['file_exists'] else '✗'}")
        print(f"可读取: {'✓' if results['readable'] else '✗'}")
        print(f"列名匹配: {'✓' if results['columns_match'] else '✗'}")

        if results['issues']:
            print("\n发现的问题:")
            for issue in results['issues']:
                print(f"  - {issue}")
        else:
            print("\n✓ 所有检查通过！")

        if results['suggestions']:
            print("\n建议:")
            for suggestion in results['suggestions']:
                print(f"  - {suggestion}")

    elif choice == "2":
        # 生成测试文件
        output_path = input("请输入输出路径 (默认: test_data.csv): ").strip()
        if not output_path:
            output_path = "test_data.csv"

        num_rows = input("请输入生成行数 (默认: 100): ").strip()
        num_rows = int(num_rows) if num_rows.isdigit() else 100

        validator.generate_test_data(output_path, num_rows)

    elif choice == "3":
        # 格式对比
        csv_path = input("请输入CSV文件路径: ").strip()
        if not csv_path:
            csv_path = r"D:\cnc_project\data\采集组数据.csv"

        validator.compare_with_mock(csv_path)

    elif choice == "4":
        # 完整测试
        print("开始完整测试...")

        # 1. 生成测试数据
        test_file = validator.generate_test_data("temp_test.csv", 50)

        # 2. 验证测试数据
        print("\n验证生成的测试数据...")
        results = validator.validate_csv(test_file)

        # 3. 格式对比
        print("\n与Mock数据对比...")
        validator.compare_with_mock(test_file)

        # 清理
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n清理临时文件: {test_file}")

        print("\n完整测试完成！")

    else:
        print("无效选项")


if __name__ == "__main__":
    main()
