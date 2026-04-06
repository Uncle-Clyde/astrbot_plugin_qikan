"""
跑商系统 - Mount & Blade 风格

玩家在各城镇和村庄之间买卖商品赚取差价。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TradeGood:
    """商品定义"""
    good_id: str
    name: str
    description: str
    base_price: int
    weight: float = 1.0  # 重量 (用于背包)
    category: str = "普通"  # 普通/粮食/工艺品/奢侈品


# 商品定义
GOODS: dict[str, TradeGood] = {
    # 粮食类
    "grain": TradeGood("grain", "谷物", "最基本的粮食", base_price=10, category="粮食"),
    "wheat": TradeGood("wheat", "小麦", "优质小麦", base_price=15, category="粮食"),
    "barley": TradeGood("barley", "大麦", "酿酒原料", base_price=12, category="粮食"),
    "cattle": TradeGood("cattle", "牛", "可买卖的牛", base_price=50, weight=50, category="粮食"),
    "sheep": TradeGood("sheep", "羊", "可买卖的羊", base_price=30, weight=20, category="粮食"),
    "horse": TradeGood("horse", "马", "战马/驮马", base_price=100, weight=80, category="粮食"),
    "fish": TradeGood("fish", "鱼", "新鲜的海鱼", base_price=20, weight=5, category="粮食"),
    
    # 矿产类
    "iron": TradeGood("iron", "铁矿", "锻造原料", base_price=30, weight=10, category="矿产"),
    "silver": TradeGood("silver", "银矿", "贵金属", base_price=80, weight=5, category="矿产"),
    "gold": TradeGood("gold", "金矿", "稀有贵金属", base_price=200, weight=2, category="矿产"),
    
    # 原料类
    "wool": TradeGood("wool", "羊毛", "纺织原料", base_price=15, weight=5, category="原料"),
    "cloth": TradeGood("cloth", "布匹", "织好的布", base_price=25, weight=5, category="原料"),
    "timber": TradeGood("timber", "木材", "建筑/锻造材料", base_price=20, weight=15, category="原料"),
    "leather": TradeGood("leather", "皮革", "制作皮甲材料", base_price=35, weight=8, category="原料"),
    
    # 工艺品
    "wine": TradeGood("wine", "葡萄酒", "斯瓦迪亚特产", base_price=40, weight=3, category="工艺品"),
    "weapons": TradeGood("weapons", "武器", "城镇打造的武器", base_price=100, weight=15, category="工艺品"),
    "armor": TradeGood("armor", "盔甲", "城镇打造的盔甲", base_price=120, weight=20, category="工艺品"),
    
    # 奢侈品
    "spices": TradeGood("spices", "香料", "东方传来的香料", base_price=60, weight=2, category="奢侈品"),
    "silk": TradeGood("silk", "丝绸", "高级丝绸", base_price=80, weight=2, category="奢侈品"),
    "dates": TradeGood("dates", "椰枣", "沙漠特产", base_price=25, weight=5, category="奢侈品"),
    "luxury_goods": TradeGood("luxury_goods", "奢侈品", "精美的奢侈品", base_price=150, weight=3, category="奢侈品"),
}


# 地点的商品配置
class LocationTrade:
    """地点的商品交易配置"""
    def __init__(
        self,
        produces: list[str] = None,  # 产地 (低价出售)
        demands: list[str] = None,   # 需求 (高价收购)
        trades: list[str] = None,     # 普通商品 (平价)
    ):
        self.produces = produces or []
        self.demands = demands or []
        self.trades = trades or []


# 城镇商品配置
TOWN_TRADE: dict[str, LocationTrade] = {
    # 斯瓦迪亚城镇
    "town_reyvadin": LocationTrade(
        produces=["iron", "weapons", "armor"],
        demands=["wine", "spices", "luxury_goods"],
        trades=["grain", "cattle", "cloth"],
    ),
    "town_dhirim": LocationTrade(
        produces=["grain", "cattle", "cloth"],
        demands=["iron", "weapons", "silver"],
        trades=["wine", "timber"],
    ),
    "town_pravend": LocationTrade(
        produces=["wine", "grain", "cattle"],
        demands=["iron", "spices", "luxury_goods"],
        trades=["cloth", "leather"],
    ),
    
    # 维吉亚城镇
    "town_suno": LocationTrade(
        produces=["grain", "iron", "cloth"],
        demands=["wine", "horses", "luxury_goods"],
        trades=["silver", "timber"],
    ),
    
    # 诺德城镇
    "town_sargoth": LocationTrade(
        produces=["fish", "iron", "timber"],
        demands=["wine", "spices", "silk"],
        trades=["grain", "cattle"],
    ),
    
    # 罗多克城镇
    "town_curin": LocationTrade(
        produces=["iron", "silver", "weapons"],
        demands=["wine", "horses", "luxury_goods"],
        trades=["grain", "leather"],
    ),
    "town_jelkala": LocationTrade(
        produces=["luxury_goods", "iron", "cloth"],
        demands=["fish", "cattle", "horses"],
        trades=["silver", "spices"],
    ),
    
    # 库吉特城镇
    "town_uxkhal": LocationTrade(
        produces=["horses", "wool", "spices"],
        demands=["iron", "weapons", "silver"],
        trades=["cattle", "leather", "grain"],
    ),
    
    # 萨兰德城镇
    "town_yalen": LocationTrade(
        produces=["spices", "silk", "dates"],
        demands=["iron", "cattle", "timber"],
        trades=["cloth", "luxury_goods"],
    ),
    "town_desh_shapuri": LocationTrade(
        produces=["spices", "silk", "gold"],
        demands=["cattle", "horses", "iron"],
        trades=["luxury_goods", "weapons"],
    ),
}


# 村庄商品配置 (村庄只出售原料)
VILLAGE_TRADE: dict[str, LocationTrade] = {
    # 农业村 - 低价出售粮食
    "village_talmur": LocationTrade(produces=["wheat", "grain"], demands=[], trades=[]),
    "village_nord_farmers": LocationTrade(produces=["barley", "grain"], demands=[], trades=[]),
    "village_chambers": LocationTrade(produces=["wheat", "cattle"], demands=[], trades=[]),
    
    # 渔村 - 低价出售鱼
    "village_teona": LocationTrade(produces=["fish"], demands=[], trades=[]),
    "village_bismar": LocationTrade(produces=["fish"], demands=[], trades=[]),
    
    # 畜牧村 - 低价出售牛羊
    "village_ogre_C": LocationTrade(produces=["cattle", "sheep"], demands=[], trades=[]),
    "village_Khergit_f": LocationTrade(produces=["horses", "sheep"], demands=[], trades=[]),
    
    # 矿村 - 低价出售矿产
    "village_Rhadegund": LocationTrade(produces=["iron"], demands=[], trades=[]),
    
    # 果园村 - 低价出售葡萄/椰枣
    "village_egrent": LocationTrade(produces=["wine", "grain"], demands=[], trades=[]),
    "village_Zaikes": LocationTrade(produces=["dates"], demands=[], trades=[]),
}


def get_good(good_id: str) -> Optional[TradeGood]:
    """获取商品定义"""
    return GOODS.get(good_id)


def get_all_goods() -> list[TradeGood]:
    """获取所有商品"""
    return list(GOODS.values())


def get_location_trade(location_id: str) -> LocationTrade:
    """获取地点的交易配置"""
    if location_id in TOWN_TRADE:
        return TOWN_TRADE[location_id]
    if location_id in VILLAGE_TRADE:
        return VILLAGE_TRADE[location_id]
    return LocationTrade()


def calculate_price(location_id: str, good_id: str, is_buying: bool) -> int:
    """
    计算商品价格
    
    Args:
        location_id: 地点ID
        good_id: 商品ID
        is_buying: True=玩家买入, False=玩家卖出
    
    Returns:
        价格 (int)
    """
    good = get_good(good_id)
    if not good:
        return 0
    
    trade = get_location_trade(location_id)
    
    # 基础价格
    price = good.base_price
    
    # 地点加成
    if is_buying:
        # 玩家买入价格
        if good_id in trade.produces:
            # 产地，便宜 30-50%
            price = int(price * random.uniform(0.5, 0.7))
        elif good_id in trade.demands:
            # 需求地，贵 30-50%
            price = int(price * random.uniform(1.3, 1.5))
        else:
            # 普通商品
            price = int(price * random.uniform(0.9, 1.1))
    else:
        # 玩家卖出价格
        if good_id in trade.produces:
            # 产地，便宜 30-50% (玩家低价卖出)
            price = int(price * random.uniform(0.3, 0.5))
        elif good_id in trade.demands:
            # 需求地，高价收购
            price = int(price * random.uniform(1.5, 2.0))
        else:
            # 普通商品
            price = int(price * random.uniform(0.7, 0.9))
    
    return max(1, price)


def get_location_goods(location_id: str, is_buying: bool = True) -> list[dict]:
    """
    获取地点可交易的商品列表
    
    Args:
        location_id: 地点ID
        is_buying: True=显示买入商品, False=显示卖出商品
    
    Returns:
        商品列表 [{good_id, name, price, category, is_cheap/is_expensive}]
    """
    trade = get_location_trade(location_id)
    goods_list = []
    
    # 获取该地点所有可能的商品
    all_goods = set(trade.produces + trade.demands + trade.trades)
    
    # 如果是村庄，添加所有基础商品
    if location_id in VILLAGE_TRADE:
        all_goods.update(["grain", "wheat", "barley", "fish", "cattle", "sheep", "iron", "wine", "dates"])
    
    # 如果是城镇，添加更多商品
    if location_id in TOWN_TRADE:
        all_goods.update(GOODS.keys())
    
    for good_id in all_goods:
        good = get_good(good_id)
        if not good:
            continue
        
        price = calculate_price(location_id, good_id, is_buying)
        
        # 标记价格类型
        is_cheap = False
        is_expensive = False
        if is_buying:
            is_cheap = good_id in trade.produces
            is_expensive = good_id in trade.demands
        else:
            is_cheap = good_id in trade.demands
            is_expensive = good_id in trade.produces
        
        goods_list.append({
            "good_id": good_id,
            "name": good.name,
            "price": price,
            "category": good.category,
            "is_cheap": is_cheap,
            "is_expensive": is_expensive,
        })
    
    # 按价格排序
    goods_list.sort(key=lambda x: x["price"])
    return goods_list


class PlayerTradeInventory:
    """玩家背包商品"""
    def __init__(self, goods: dict[str, int] = None):
        self.goods = goods or {}  # {good_id: count}
    
    def add(self, good_id: str, count: int = 1):
        """添加商品"""
        self.goods[good_id] = self.goods.get(good_id, 0) + count
    
    def remove(self, good_id: str, count: int = 1) -> bool:
        """移除商品"""
        current = self.goods.get(good_id, 0)
        if current < count:
            return False
        self.goods[good_id] = current - count
        if self.goods[good_id] <= 0:
            del self.goods[good_id]
        return True
    
    def get_count(self, good_id: str) -> int:
        """获取商品数量"""
        return self.goods.get(good_id, 0)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return self.goods.copy()
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlayerTradeInventory":
        """从字典创建"""
        return cls(data.copy() if data else {})


def buy_good(player, location_id: str, good_id: str, count: int = 1) -> dict:
    """
    玩家买入商品
    
    Returns:
        {"success": bool, "message": str}
    """
    if count < 1:
        return {"success": False, "message": "数量必须大于0"}
    
    good = get_good(good_id)
    if not good:
        return {"success": False, "message": "未知的商品"}
    
    price = calculate_price(location_id, good_id, True)
    total_cost = price * count
    
    if not hasattr(player, 'trade_inventory'):
        player.trade_inventory = PlayerTradeInventory()
    
    inventory = player.trade_inventory
    
    if player.spirit_stones < total_cost:
        return {"success": False, "message": f"金币不足，需要{total_cost}金币，当前只有{player.spirit_stones}金币"}
    
    player.spirit_stones -= total_cost
    inventory.add(good_id, count)
    
    return {
        "success": True,
        "message": f"购买了 {count} 个{good.name}，花费 {total_cost} 金币",
        "cost": total_cost,
        "count": count,
        "good_name": good.name,
        "remaining_gold": player.spirit_stones,
    }


def sell_good(player, location_id: str, good_id: str, count: int = 1) -> dict:
    """
    玩家卖出商品
    
    Returns:
        {"success": bool, "message": str}
    """
    if count < 1:
        return {"success": False, "message": "数量必须大于0"}
    
    good = get_good(good_id)
    if not good:
        return {"success": False, "message": "未知的商品"}
    
    if not hasattr(player, 'trade_inventory'):
        player.trade_inventory = PlayerTradeInventory()
    
    inventory = player.trade_inventory
    
    if inventory.get_count(good_id) < count:
        return {"success": False, "message": f"背包中没有足够的{good.name}"}
    
    price = calculate_price(location_id, good_id, False)
    total_earned = price * count
    
    inventory.remove(good_id, count)
    player.spirit_stones += total_earned
    
    return {
        "success": True,
        "message": f"出售了 {count} 个{good.name}，获得 {total_earned} 金币",
        "earned": total_earned,
        "count": count,
        "good_name": good.name,
        "remaining_gold": player.spirit_stones,
    }


def get_trade_inventory_display(player) -> str:
    """格式化显示背包商品"""
    if not hasattr(player, 'trade_inventory'):
        return "背包商品: (空)"
    
    inventory = player.trade_inventory
    if not inventory.goods:
        return "背包商品: (空)"
    
    lines = ["🎒 背包商品:"]
    for good_id, count in inventory.goods.items():
        good = get_good(good_id)
        if good:
            lines.append(f"  {good.name}: {count}个")
    
    return "\n".join(lines)


def format_trade_list(location_id: str, player, is_buying: bool = True) -> str:
    """格式化商品列表"""
    goods_list = get_location_goods(location_id, is_buying)
    
    if is_buying:
        title = "🛒 商店商品 (可买入):"
    else:
        title = "💰 收购商品 (可卖出):"
    
    lines = [title, ""]
    
    # 按类别分组
    categories = {}
    for g in goods_list:
        cat = g["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(g)
    
    # 显示玩家拥有的数量
    inventory = PlayerTradeInventory()
    if hasattr(player, 'trade_inventory'):
        inventory = player.trade_inventory
    
    for cat, items in categories.items():
        lines.append(f"【{cat}】")
        for item in items:
            owned = inventory.get_count(item["good_id"])
            owned_str = f" (持有{owned})" if owned > 0 else ""
            
            if item["is_cheap"]:
                price_str = f"💚 {item['price']}金"
            elif item["is_expensive"]:
                price_str = f"💛 {item['price']}金"
            else:
                price_str = f"{item['price']}金"
            
            lines.append(f"  {item['name']}: {price_str}{owned_str}")
        lines.append("")
    
    return "\n".join(lines)
