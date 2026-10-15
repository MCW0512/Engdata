# export_pf_sequences.py
# 说明：运行前请确保安装 pandas 和 openpyxl： pip install pandas openpyxl
import json
import pandas as pd

# 请把文件名改为你上传的文件名（或放在同一目录）
INPUT_XLSX = "Engineering data OFSuzhou_Extract_20260827_090006.xlsx"
SHEET_NAME = 0  # 默认为第一个 sheet；或改为具体 sheet 名称

# 读取 Excel
df = pd.read_excel(INPUT_XLSX, sheet_name=SHEET_NAME, dtype=str)

# 关键字段名（与表头一致）
# 如果表头有轻微差异，请根据实际列名调整下面变量
PF_COL = "Product_Family"
SEQ_COL = "Operational__route__Sequence__"
CYCLE_COL = "Cycle_Time__sec_"
PARTS_COL = "Parts_Processed_per_Cycle"

# 清洗：去除全空的行与转换数值
df = df[[PF_COL, SEQ_COL, CYCLE_COL, PARTS_COL]].copy()

# 去除空白 PF 或 Sequence
df[PF_COL] = df[PF_COL].astype(str).str.strip()
df[SEQ_COL] = df[SEQ_COL].astype(str).str.strip()
df = df[df[PF_COL] != "nan"]
df = df[df[SEQ_COL] != "nan"]

# 转数值，非数值变为 NaN，然后丢弃或按需要处理
def to_float_safe(s):
    try:
        return float(str(s).strip())
    except:
        return float("nan")

df[CYCLE_COL] = df[CYCLE_COL].apply(to_float_safe)
df[PARTS_COL] = df[PARTS_COL].apply(to_float_safe)

# 如果 Sequence 看起来像整数，转为 int（用于排序）
# 先尝试把可转为 int 的值转为 int，其余保留原字符串排序
def seq_key(val):
    try:
        return int(float(val))
    except:
        try:
            return int(val)
        except:
            return val

# 聚合：按 Product Family 和 Sequence 计算平均 Cycle Time 与平均 Parts per Cycle
agg = (
    df
    .groupby([PF_COL, SEQ_COL], dropna=True, as_index=False)
    .agg({CYCLE_COL: "mean", PARTS_COL: "mean",})
)

# 为前端准备结构：每个 PF 对应有序的 sequence 列表
result = {"product_families": [], "data": {}}

product_families = sorted(agg[PF_COL].dropna().unique().tolist())
result["product_families"] = product_families

for pf in product_families:
    sub = agg[agg[PF_COL] == pf].copy()
    # 为排序，尝试把 Sequence 转为数值 key
    try:
        sub["_seq_key"] = sub[SEQ_COL].apply(lambda x: seq_key(x))
        sub = sub.sort_values(by="_seq_key")
    except:
        sub = sub.sort_values(by=SEQ_COL)
    seq_list = []
    for _, row in sub.iterrows():
        seq_list.append({
            "sequence": str(row[SEQ_COL]),
            "sequence_key": row.get("_seq_key", row[SEQ_COL]),
            "cycle_time_sec": None if pd.isna(row[CYCLE_COL]) else float(row[CYCLE_COL]),
            "parts_processed_per_cycle": None if pd.isna(row[PARTS_COL]) else float(row[PARTS_COL])
        })
    result["data"][pf] = seq_list

# 保存为 data.json
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("已生成 data.json，包含 {} 个 Product Family".format(len(product_families)))

