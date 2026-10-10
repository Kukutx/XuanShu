"""Transparent non-generative cultural analysis with auditable chart fields."""
from __future__ import annotations

from .engines import BirthInput, calculate_bazi, calculate_ziwei
from .reference import PALACE_TOPICS


def symbolic_reading(inp: BirthInput) -> dict:
    bazi = calculate_bazi(inp)
    ziwei = calculate_ziwei(inp)
    ming = next(x for x in ziwei['palaces'] if x['is_ming'])
    points = [
        f"八字四柱：{' / '.join(p['text'] for p in bazi['pillars'].values())}。",
        f"日主{bazi['day_master']}（{bazi['day_master_element']}），是十神映射的参照，不是对个人特征的科学判断。",
        '可见干支本气数量：' + '、'.join(f'{name}{count}' for name,count in bazi['surface_five_elements'].items()) + '。',
        f"命宫在{ziwei['ming_palace']}、身宫在{ziwei['shen_palace']}，命宫十四主星：{'、'.join(ming['main_stars']) or '无（空宫）'}。",
        f"紫微局数：{ziwei['five_elements_bureau']}；采用{ziwei['transformation_school']}。",
        '生年四化：' + '、'.join(
            f"{x['star']}{x['type']}（{x['palace_name']}）" for x in ziwei['birth_year_transformations']
        ) + '。',
    ]
    return {
        'type': 'symbolic-non-predictive',
        'summary': '历法计算与传统术数符号说明（非科学预测）',
        'points': points,
        'day_master_hidden_stems': {
            key: value['hidden_stems'] for key, value in bazi['pillars'].items()
        },
        'palace_topics': PALACE_TOPICS,
        'next_questions': [
            '想根据某一宫的星曜和生年四化进一步查看传统含义吗？',
            '想看某一天的节令切换或两张命盘的结构差异吗？',
        ],
        'limitations': [
            '命理缺乏可靠的科学验证，不应作为人生、医疗或财务决策依据。',
            '生年四化表有流派差异，本版本固定采用全书系；不包括完整辅杂星、流年和完整飞星断法。',
            '藏干和五行计数不代表旺衰、喜忌或个性测量。',
        ],
    }
