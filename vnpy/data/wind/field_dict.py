# encoding: UTF-8
"""数据字典,解决wind数据字段名称和vnpy标准数据字段名称的对应关系"""


# key: vnpy合约名称（不含日期）
# value：[对应的wind合约名称, 交易所代码]
WIND_FIELD_DICT = {
    "T": ["T", "CFE"],    # 十年国债
    "rb": ["RB", "SHF"],  # 螺纹钢
    "j": ["J", "DCE"],  # 焦炭
    "hc": ["HC", "SHF"]     # 热卷
}
