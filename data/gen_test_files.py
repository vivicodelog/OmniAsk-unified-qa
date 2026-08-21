"""生成测试文件：Excel / CSV，覆盖日期、布尔、多 sheet 等场景。

用法：
    python data/gen_test_files.py            # 默认输出到 data/samples/
    python data/gen_test_files.py ~/Desktop  # 指定输出目录
"""
import sys
from pathlib import Path

import pandas as pd

# 输出目录取命令行参数，缺省落在仓库内，避免硬编码某台机器的桌面路径
OUT_DIR = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path(__file__).parent / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DESKTOP = OUT_DIR  # 下方沿用原变量名，少改几处

# ------------------------------------------------------------
# 1. 销售数据.xlsx —— 含日期、地区、品类、数值（测折线/饼/柱图）
# ------------------------------------------------------------
sales = pd.DataFrame({
    "日期": pd.date_range("2026-01-01", periods=24, freq="MS"),  # 每月一条
    "地区": ["华东", "华北", "华南", "西南"] * 6,
    "品类": ["数码", "家电", "服饰", "食品"] * 6,
    "销售额": [120000, 98000, 85000, 72000, 135000, 102000,
               90000, 76000, 140000, 108000, 95000, 80000,
               128000, 99000, 88000, 74000, 150000, 115000,
               98000, 82000, 132000, 105000, 92000, 78000],
    "订单量": [320, 280, 410, 350, 360, 300,
               430, 380, 390, 310, 450, 400,
               340, 290, 420, 370, 380, 320,
               440, 390, 360, 300, 460, 410],
    "是否退款": [False, True, False, False, True, False] * 4,
})
sales.to_excel(DESKTOP / "销售数据.xlsx", index=False)

# ------------------------------------------------------------
# 2. 销售明细.csv —— 明细粒度，测 CSV 解析 + 大行数
# ------------------------------------------------------------
import random
random.seed(42)
cats = ["数码", "家电", "服饰", "食品"]
regions = ["华东", "华北", "华南", "西南"]
rows = []
for i in range(120):
    rows.append({
        "订单号": f"SO{i:04d}",
        "日期": f"2026-{random.randint(1,6):02d}-{random.randint(1,28):02d}",
        "地区": random.choice(regions),
        "品类": random.choice(cats),
        "单价": round(random.uniform(50, 2000), 2),
        "数量": random.randint(1, 20),
    })
detail = pd.DataFrame(rows)
detail.to_csv(DESKTOP / "销售明细.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# 3. 员工信息.xlsx —— 多 sheet，测布尔/日期清洗 + 多 sheet 处理
# ------------------------------------------------------------
employees = pd.DataFrame({
    "姓名": ["张三", "李四", "王五", "赵六", "钱七", "孙八"],
    "部门": ["研发", "研发", "销售", "销售", "运营", "运营"],
    "入职日期": ["2021-03-15", "2022-07-01", "2020-11-20", "2023-01-10", "2021-06-30", "2022-02-14"],
    "薪资": [18000, 20000, 15000, 16000, 12000, 13000],
    "在职": [True, True, False, True, True, False],
})

departments = pd.DataFrame({
    "部门": ["研发", "销售", "运营"],
    "人数": [20, 35, 12],
    "平均薪资": [19000, 15500, 12500],
})

with pd.ExcelWriter(DESKTOP / "员工信息.xlsx") as writer:
    employees.to_excel(writer, sheet_name="员工", index=False)
    departments.to_excel(writer, sheet_name="部门汇总", index=False)

print("已生成：")
for f in ["销售数据.xlsx", "销售明细.csv", "员工信息.xlsx"]:
    p = DESKTOP / f
    print(f"  {p}  ({p.stat().st_size:,} bytes)")
