"""竞技场系统 - 骑砍风格。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TournamentOpponent:
    """竞技场对手。"""
    opponent_id: str
    name: str
    title: str
    level: int            # 难度等级 1-5
    attack: int
    defense: int
    hp: int
    reward_gold: int      # 胜利奖金
    reward_dao_yun: int   # 胜利声望
    description: str


# 竞技场对手池
TOURNAMENT_OPPONENTS: dict[str, TournamentOpponent] = {
    # 难度1
    "t1_farmboy": TournamentOpponent(
        opponent_id="t1_farmboy", name="汤姆", title="农家小子", level=1,
        attack=10, defense=5, hp=50,
        reward_gold=50, reward_dao_yun=5,
        description="第一次参加竞技场的年轻人。",
    ),
    "t1_merc": TournamentOpponent(
        opponent_id="t1_merc", name="巴克", title="雇佣兵", level=1,
        attack=15, defense=8, hp=60,
        reward_gold=60, reward_dao_yun=6,
        description="为了钱来竞技场的雇佣兵。",
    ),
    # 难度2
    "t2_soldier": TournamentOpponent(
        opponent_id="t2_soldier", name="哈里斯", title="退役士兵", level=2,
        attack=25, defense=15, hp=80,
        reward_gold=100, reward_dao_yun=10,
        description="经验丰富的退役老兵。",
    ),
    "t2_gladiator": TournamentOpponent(
        opponent_id="t2_gladiator", name="克里昂", title="角斗士", level=2,
        attack=30, defense=12, hp=90,
        reward_gold=120, reward_dao_yun=12,
        description="竞技场常驻的职业角斗士。",
    ),
    # 难度3
    "t3_knight": TournamentOpponent(
        opponent_id="t3_knight", name="雷纳德", title="流浪骑士", level=3,
        attack=45, defense=30, hp=120,
        reward_gold=200, reward_dao_yun=20,
        description="失去领地的流浪骑士。",
    ),
    "t3_champion": TournamentOpponent(
        opponent_id="t3_champion", name="加尔文", title="竞技场冠军", level=3,
        attack=50, defense=25, hp=130,
        reward_gold=250, reward_dao_yun=25,
        description="上届竞技场的冠军。",
    ),
    # 难度4
    "t4_veteran": TournamentOpponent(
        opponent_id="t4_veteran", name="乌尔班", title="身经百战", level=4,
        attack=70, defense=45, hp=180,
        reward_gold=400, reward_dao_yun=40,
        description="从无数战斗中存活下来的战士。",
    ),
    "t4_legend": TournamentOpponent(
        opponent_id="t4_legend", name="阿瑞斯", title="传说战士", level=4,
        attack=80, defense=40, hp=200,
        reward_gold=500, reward_dao_yun=50,
        description="传说中从未败北的战士。",
    ),
    # 难度5
    "t5_warlord": TournamentOpponent(
        opponent_id="t5_warlord", name="蒙楚格", title="草原战神", level=5,
        attack=120, defense=60, hp=300,
        reward_gold=800, reward_dao_yun=80,
        description="来自东方的草原战神。",
    ),
    "t5_champion_king": TournamentOpponent(
        opponent_id="t5_champion_king", name="雷萨里特", title="竞技场之王", level=5,
        attack=150, defense=80, hp=350,
        reward_gold=1000, reward_dao_yun=100,
        description="竞技场的终极挑战者。",
    ),
}

# 连胜奖励
WIN_STREAK_REWARDS = {
    3: {"gold": 200, "dao_yun": 20, "title": "三连胜"},
    5: {"gold": 500, "dao_yun": 50, "title": "五连胜"},
    10: {"gold": 1500, "dao_yun": 150, "title": "十连胜"},
}

# 报名费
ENTRY_FEE = 30


def get_opponent(opponent_id: str) -> Optional[TournamentOpponent]:
    """获取对手定义。"""
    return TOURNAMENT_OPPONENTS.get(opponent_id)


def get_opponents_by_level(level: int) -> list[TournamentOpponent]:
    """获取指定难度的对手。"""
    return [o for o in TOURNAMENT_OPPONENTS.values() if o.level == level]


def get_tournament_opponents() -> list[TournamentOpponent]:
    """获取所有竞技场对手。"""
    return list(TOURNAMENT_OPPONENTS.values())


def generate_daily_opponents(player_level: int) -> list[str]:
    """为玩家生成今日可选的对手列表。
    
    根据玩家等级生成3个难度递增的对手。
    """
    # 基础难度根据玩家等级
    base_level = max(1, min(5, (player_level + 4) // 5))
    
    # 选择3个对手，难度递增
    available = []
    for lvl in range(base_level, min(base_level + 3, 6)):
        opponents = get_opponents_by_level(lvl)
        if opponents:
            available.append(random.choice(opponents).opponent_id)
    
    # 如果不够3个，随机补充
    while len(available) < 3:
        all_ids = list(TOURNAMENT_OPPONENTS.keys())
        choice = random.choice(all_ids)
        if choice not in available:
            available.append(choice)
    
    return available


def get_win_streak_reward(streak: int) -> Optional[dict]:
    """获取连胜奖励。"""
    return WIN_STREAK_REWARDS.get(streak)
