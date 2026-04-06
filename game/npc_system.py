"""
NPC系统 - 骑砍英雄传

定义据点内的NPC、对话树系统、好感度管理。
与现有礼物系统(village_system.py)深度集成。
"""

from __future__ import annotations

import json
import os
import time
import random
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from .village_system import (
    GIFT_ITEMS, calculate_gift_value,
    get_gift_category, get_favor_status, get_favor_benefits,
)

# ══════════════════════════════════════════════════════════════
# 对话配置加载
# ══════════════════════════════════════════════════════════════

_DIALOG_CONFIG_CACHE: dict | None = None

def _find_dialog_config_path() -> str | None:
    """查找对话配置文件路径。"""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "static", "dialogs", "config.json"),
        os.path.join(os.path.dirname(__file__), "static", "dialogs", "config.json"),
        os.path.join("static", "dialogs", "config.json"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None


def load_dialog_config() -> dict:
    """加载对话配置（带缓存）。"""
    global _DIALOG_CONFIG_CACHE
    if _DIALOG_CONFIG_CACHE is not None:
        return _DIALOG_CONFIG_CACHE
    
    config_path = _find_dialog_config_path()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _DIALOG_CONFIG_CACHE = json.load(f)
            return _DIALOG_CONFIG_CACHE  # type: ignore
        except Exception:
            pass
    
    _DIALOG_CONFIG_CACHE = {}
    return _DIALOG_CONFIG_CACHE  # type: ignore


def reload_dialog_config() -> dict:
    """强制重新加载对话配置。"""
    global _DIALOG_CONFIG_CACHE
    _DIALOG_CONFIG_CACHE = None
    return load_dialog_config()


def get_npc_dialog_from_config(npc_id: str) -> dict | None:
    """从配置中获取NPC的对话数据。"""
    config = load_dialog_config()
    npcs = config.get("npcs", {})
    npc_config = npcs.get(npc_id)
    if npc_config and "dialog" in npc_config:
        return npc_config["dialog"]
    return None


def get_all_npc_configs() -> dict:
    """获取所有NPC配置。"""
    config = load_dialog_config()
    return config.get("npcs", {})


def save_dialog_config(config: dict) -> bool:
    """保存对话配置到文件。"""
    global _DIALOG_CONFIG_CACHE
    config_path = _find_dialog_config_path()
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "..", "static", "dialogs", "config.json")
        config_path = os.path.abspath(config_path)
    
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        _DIALOG_CONFIG_CACHE = config
        return True
    except Exception:
        return False


def _parse_dialog_node(node_data: dict) -> DialogNode:
    """从JSON数据解析对话节点。"""
    options = []
    for opt_data in node_data.get("options", []):
        options.append(DialogOption(
            option_id=opt_data.get("option_id", ""),
            text=opt_data.get("text", ""),
            next_node=opt_data.get("next_node", ""),
            action=opt_data.get("action", "none"),
            action_data=opt_data.get("action_data", {}),
            min_favor=opt_data.get("min_favor", 0),
        ))
    return DialogNode(
        node_id=node_data.get("node_id", ""),
        text=node_data.get("text", ""),
        options=options,
    )


def create_dialog_for_npc(npc: NPC, location_name: str = "", location_desc: str = "") -> dict[str, DialogNode]:
    """根据NPC创建对话树（优先使用JSON配置）。"""
    dialog_data = get_npc_dialog_from_config(npc.npc_id)
    if dialog_data:
        result = {}
        for node_id, node_data in dialog_data.items():
            result[node_id] = _parse_dialog_node(node_data)
        return result
    
    npc_type = npc.npc_type
    
    if npc_type == "mayor":
        return create_mayor_dialog(location_name, location_desc)
    elif npc_type == "merchant":
        return create_merchant_dialog(location_name)
    elif npc_type == "blacksmith":
        return create_blacksmith_dialog(location_name)
    elif npc_type == "tavern_keeper":
        return create_tavern_dialog(location_name)
    elif npc_type == "guard_captain":
        return create_guard_dialog(location_name)
    elif npc_type == "village_elder":
        return create_village_elder_dialog(location_name)
    elif npc_type == "villager":
        return create_villager_dialog(location_name)
    elif npc_type == "horse_trader":
        return create_horse_trader_dialog(location_name)
    else:
        return create_villager_dialog(location_name)


# ══════════════════════════════════════════════════════════════
# NPC好感度等级
# ══════════════════════════════════════════════════════════════

NPC_FAVOR_LEVELS: list[tuple[int, str, str]] = [
    (0, "陌生人", "冷漠"),
    (10, "点头之交", "礼貌"),
    (25, "熟悉", "友善"),
    (45, "信任", "信任"),
    (65, "好友", "热情"),
    (85, "至交", "挚友"),
]


def get_npc_favor_level(favor: int) -> tuple[str, str]:
    """根据好感度获取等级和态度。"""
    current_name, current_attitude = "陌生人", "冷漠"
    for threshold, name, attitude in NPC_FAVOR_LEVELS:
        if favor >= threshold:
            current_name, current_attitude = name, attitude
        else:
            break
    return current_name, current_attitude


def get_npc_favor_next_threshold(favor: int) -> Optional[int]:
    """获取下一个好感度阈值。"""
    for threshold, _, _ in NPC_FAVOR_LEVELS:
        if favor < threshold:
            return threshold
    return None


# ══════════════════════════════════════════════════════════════
# NPC定义
# ══════════════════════════════════════════════════════════════

@dataclass
class NPC:
    """NPC定义。"""
    npc_id: str
    name: str
    title: str
    icon: str
    description: str
    location_ids: list[str]  # 所在据点ID列表
    npc_type: str  # mayor, merchant, blacksmith, etc.
    personality: str = "neutral"  # friendly, neutral, grumpy


# 城镇NPC
TOWN_NPCS: dict[str, NPC] = {
    "mayor_suno": NPC(
        npc_id="mayor_suno", name="海尔姆", title="苏诺城镇长",
        icon="👨‍💼", description="一位睿智的长者，管理着这座商业城市",
        location_ids=["town_suno"], npc_type="mayor", personality="friendly",
    ),
    "mayor_reyvadin": NPC(
        npc_id="mayor_reyvadin", name="格伦", title="瑞瓦迪恩军事长官",
        icon="👨‍✈️", description="曾经的骑士团长，现在是城镇的军事负责人",
        location_ids=["town_reyvadin"], npc_type="mayor", personality="neutral",
    ),
    "mayor_curin": NPC(
        npc_id="mayor_curin", name="布朗", title="库里姆矿业主",
        icon="👨‍💼", description="掌握着罗多克王国的矿业命脉",
        location_ids=["town_curin"], npc_type="mayor", personality="neutral",
    ),
    "mayor_jelkala": NPC(
        npc_id="mayor_jelkala", name="伊莎贝拉", title="贾尔卡拉女爵",
        icon="👩‍💼", description="罗多克王国的贵族，负责首都事务",
        location_ids=["town_jelkala"], npc_type="mayor", personality="friendly",
    ),
    "mayor_dhirim": NPC(
        npc_id="mayor_dhirim", name="凯恩", title="迪林姆执政官",
        icon="👨‍💼", description="管理着斯瓦迪亚的农业中心",
        location_ids=["town_dhirim"], npc_type="mayor", personality="friendly",
    ),
    "mayor_sargoth": NPC(
        npc_id="mayor_sargoth", name="奥拉夫", title="萨戈斯港口守卫",
        icon="🧔", description="诺德王国的港口城市管理者",
        location_ids=["town_sargoth"], npc_type="mayor", personality="neutral",
    ),
    "mayor_pravend": NPC(
        npc_id="mayor_pravend", name="皮埃尔", title="普拉文德葡萄酒商",
        icon="👨‍🌾", description="斯瓦迪亚的葡萄酒贸易商人",
        location_ids=["town_pravend"], npc_type="mayor", personality="friendly",
    ),
    "mayor_uxkhal": NPC(
        npc_id="mayor_uxkhal", name="帖木儿", title="乌克斯哈尔部落首领",
        icon="🧑‍🦱", description="库吉特汗国的草原部落首领",
        location_ids=["town_uxkhal"], npc_type="mayor", personality="neutral",
    ),
    "mayor_yalen": NPC(
        npc_id="mayor_yalen", name="穆罕默德", title="亚伦香料商人",
        icon="🧔", description="萨兰德苏丹国的商业巨头",
        location_ids=["town_yalen"], npc_type="mayor", personality="friendly",
    ),
    "mayor_desh_shapuri": NPC(
        npc_id="mayor_desh_shapuri", name="阿米尔", title="德什沙普里执政官",
        icon="👳", description="沙漠绿洲城市的统治者",
        location_ids=["town_desh_shapuri"], npc_type="mayor", personality="neutral",
    ),
    "merchant_town": NPC(
        npc_id="merchant_town", name="法提玛", title="城镇商人",
        icon="🛒", description="来自远方的精明商人，商品琳琅满目",
        location_ids=["town_suno", "town_reyvadin", "town_curin", "town_jelkala",
                      "town_dhirim", "town_sargoth", "town_pravend", "town_uxkhal",
                      "town_yalen", "town_desh_shapuri"],
        npc_type="merchant", personality="friendly",
    ),
    "blacksmith_town": NPC(
        npc_id="blacksmith_town", name="安德森", title="铁匠",
        icon="🔨", description="技艺精湛的铁匠，能修理和强化装备",
        location_ids=["town_suno", "town_reyvadin", "town_curin", "town_jelkala",
                      "town_dhirim", "town_sargoth", "town_pravend", "town_uxkhal",
                      "town_yalen", "town_desh_shapuri"],
        npc_type="blacksmith", personality="neutral",
    ),
    "tavern_town": NPC(
        npc_id="tavern_town", name="罗莎", title="酒馆老板",
        icon="🍺", description="热情开朗的酒馆老板，消息灵通",
        location_ids=["town_suno", "town_reyvadin", "town_curin", "town_jelkala",
                      "town_dhirim", "town_sargoth", "town_pravend", "town_uxkhal",
                      "town_yalen", "town_desh_shapuri"],
        npc_type="tavern_keeper", personality="friendly",
    ),
    "guard_town": NPC(
        npc_id="guard_town", name="雷纳德", title="守卫队长",
        icon="🛡️", description="严肃的守卫队长，负责城镇安全",
        location_ids=["town_suno", "town_reyvadin", "town_curin", "town_jelkala",
                      "town_dhirim", "town_sargoth", "town_pravend", "town_uxkhal",
                      "town_yalen", "town_desh_shapuri"],
        npc_type="guard_captain", personality="grumpy",
    ),
}

# 村庄NPC
VILLAGE_NPCS: dict[str, NPC] = {
    "elder_village": NPC(
        npc_id="elder_village", name="村长", title="村长",
        icon="👴", description="德高望重的村长，管理着这个村庄",
        location_ids=[
            "village_chambers", "village_teona", "village_bismar",
            "village_nord_farmers", "village_talmur", "village_ogre_C",
            "village_egrent", "village_Khergit_f", "village_Rhadegund",
            "village_Zaikes",
        ],
        npc_type="village_elder", personality="friendly",
    ),
    "villager_generic": NPC(
        npc_id="villager_generic", name="村民", title="村民",
        icon="🧑‍🌾", description="勤劳的村民，正在田间劳作",
        location_ids=[
            "village_chambers", "village_teona", "village_bismar",
            "village_nord_farmers", "village_talmur", "village_ogre_C",
            "village_egrent", "village_Khergit_f", "village_Rhadegund",
            "village_Zaikes",
        ],
        npc_type="villager", personality="friendly",
    ),
    "horse_trader_village": NPC(
        npc_id="horse_trader_village", name="巴图", title="马商",
        icon="🐴", description="草原来的马商，带来优良的马匹",
        location_ids=["village_Khergit_f", "village_chambers", "village_teona"],
        npc_type="horse_trader", personality="neutral",
    ),
    "blacksmith_village": NPC(
        npc_id="blacksmith_village", name="老铁匠", title="铁匠",
        icon="🔨", description="村里唯一的铁匠，手艺还不错",
        location_ids=["village_Rhadegund", "village_talmur", "village_ogre_C"],
        npc_type="blacksmith", personality="grumpy",
    ),
}


def get_npcs_for_location(location_id: str) -> list[NPC]:
    """获取指定据点的所有NPC。"""
    result = []
    for npc in list(TOWN_NPCS.values()) + list(VILLAGE_NPCS.values()):
        if location_id in npc.location_ids:
            result.append(npc)
    return result


def get_npc_by_id(npc_id: str) -> Optional[NPC]:
    """根据ID获取NPC。"""
    all_npcs = {**TOWN_NPCS, **VILLAGE_NPCS}
    return all_npcs.get(npc_id)


# ══════════════════════════════════════════════════════════════
# 对话树系统
# ══════════════════════════════════════════════════════════════

@dataclass
class DialogOption:
    """对话选项。"""
    option_id: str
    text: str
    next_node: str
    action: str = "none"  # none, show_quests, show_info, show_gift_selector, open_shop, open_blacksmith, rest, close
    action_data: dict = field(default_factory=dict)
    min_favor: int = 0  # 需要的最低好感度
    condition: str = ""  # 额外条件


@dataclass
class DialogNode:
    """对话节点。"""
    node_id: str
    text: str
    options: list[DialogOption] = field(default_factory=list)


# 镇长对话树模板
def create_mayor_dialog(location_name: str, location_desc: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"欢迎来到{location_name}，冒险者。{location_desc}",
            options=[
                DialogOption("opt_quests", "有什么任务吗？", "quest_menu", "show_quests"),
                DialogOption("opt_info", "介绍一下这里", "location_info", "show_info"),
                DialogOption("opt_gift", "这是一点心意", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "quest_menu": DialogNode(
            node_id="quest_menu",
            text="我这里有几个任务，你看看能帮上忙吗？完成任务会有丰厚的奖励。",
            options=[
                DialogOption("opt_back", "让我看看", "quest_list", "show_quest_list"),
                DialogOption("opt_back_greet", "先不了", "greeting", "none"),
            ],
        ),
        "quest_list": DialogNode(
            node_id="quest_list",
            text="这是目前可接的任务列表，选择一个你感兴趣的吧。",
            options=[
                DialogOption("opt_back_greet", "好的，我知道了", "greeting", "none"),
            ],
        ),
        "location_info": DialogNode(
            node_id="location_info",
            text=f"{location_name}是这片土地上重要的据点。这里商业繁荣，往来商人络绎不绝。",
            options=[
                DialogOption("opt_back_greet", "谢谢介绍", "greeting", "none"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="感谢你的帮助，我们的关系越来越好了。希望以后能继续合作。",
            options=[
                DialogOption("opt_back_greet", "我会继续努力的", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？你要送我什么？",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，没什么", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="太感谢了！这正是我喜欢的！我们的关系更近了。",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢你的礼物，我收下了。",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="嗯...这个...谢谢你的好意。",
            options=[
                DialogOption("opt_back_greet", "抱歉，下次我会注意", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="祝你好运，冒险者。愿卡拉迪亚的风指引你的道路。",
            options=[],
        ),
    }


# 商人对话树
def create_merchant_dialog(location_name: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"欢迎来到我的商店，朋友！{location_name}最好的商品都在这里。",
            options=[
                DialogOption("opt_shop", "看看你的商品", "shop_view", "open_shop"),
                DialogOption("opt_gift", "这是一点心意", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "shop_view": DialogNode(
            node_id="shop_view",
            text="请随意挑选，价格好商量！",
            options=[
                DialogOption("opt_back", "让我看看", "shop_open", "open_shop"),
                DialogOption("opt_back_greet", "先不了", "greeting", "none"),
            ],
        ),
        "shop_open": DialogNode(
            node_id="shop_open",
            text="这是当前的商品列表。",
            options=[
                DialogOption("opt_back_greet", "好的，我知道了", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？你要送我什么？",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，没什么", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="太棒了！作为回报，我可以给你一些折扣！",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢你的礼物。",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="嗯...这个...好吧，谢谢。",
            options=[
                DialogOption("opt_back_greet", "抱歉", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="我们的关系不错！如果你经常光顾我的店，我会给你更好的价格。",
            options=[
                DialogOption("opt_back_greet", "我会的", "greeting", "none"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="下次再来啊！我会有更多好货！",
            options=[],
        ),
    }


# 铁匠对话树
def create_blacksmith_dialog(location_name: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"{location_name}的铁匠铺。武器和装备的修理、强化都可以找我。",
            options=[
                DialogOption("opt_repair", "修理装备", "repair_view", "open_blacksmith"),
                DialogOption("opt_enhance", "强化装备", "enhance_view", "open_blacksmith"),
                DialogOption("opt_gift", "这是一点心意", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "repair_view": DialogNode(
            node_id="repair_view",
            text="把损坏的装备拿来，我帮你修好。",
            options=[
                DialogOption("opt_back", "好的", "repair_open", "open_blacksmith"),
                DialogOption("opt_back_greet", "先不了", "greeting", "none"),
            ],
        ),
        "repair_open": DialogNode(
            node_id="repair_open",
            text="选择需要修理的装备。",
            options=[
                DialogOption("opt_back_greet", "知道了", "greeting", "none"),
            ],
        ),
        "enhance_view": DialogNode(
            node_id="enhance_view",
            text="强化装备需要一些材料，你准备好了吗？",
            options=[
                DialogOption("opt_back", "准备好了", "enhance_open", "open_blacksmith"),
                DialogOption("opt_back_greet", "下次吧", "greeting", "none"),
            ],
        ),
        "enhance_open": DialogNode(
            node_id="enhance_open",
            text="选择要强化的装备。",
            options=[
                DialogOption("opt_back_greet", "知道了", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？你要送我什么？",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，没什么", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="好礼物！下次来修理我给你打折！",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢。",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="哼...勉强收下吧。",
            options=[
                DialogOption("opt_back_greet", "抱歉", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="我们的关系不错。你的装备我会用心修理的。",
            options=[
                DialogOption("opt_back_greet", "拜托了", "greeting", "none"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="武器保养好，战场上才能保命。再见。",
            options=[],
        ),
    }


# 酒馆老板对话树
def create_tavern_dialog(location_name: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"欢迎来到{location_name}的酒馆！来一杯？消息和美酒这里都有。",
            options=[
                DialogOption("opt_rest", "休息一下", "rest_view", "rest"),
                DialogOption("opt_rumor", "有什么消息吗？", "rumor_view", "show_rumor"),
                DialogOption("opt_gift", "请你喝一杯", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "rest_view": DialogNode(
            node_id="rest_view",
            text="好好休息，恢复体力。一杯麦酒只要几个第纳尔。",
            options=[
                DialogOption("opt_rest_confirm", "来一杯", "rest_confirm", "rest"),
                DialogOption("opt_back_greet", "先不了", "greeting", "none"),
            ],
        ),
        "rest_confirm": DialogNode(
            node_id="rest_confirm",
            text="干杯！感觉好多了吧？",
            options=[
                DialogOption("opt_back_greet", "确实", "greeting", "none"),
            ],
        ),
        "rumor_view": DialogNode(
            node_id="rumor_view",
            text="我听说最近有些不太平...具体嘛，你懂的。",
            options=[
                DialogOption("opt_back_greet", "谢谢", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？请我喝什么？",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，下次吧", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="太棒了！这酒真不错！来，我告诉你一些内部消息！",
            options=[
                DialogOption("opt_back_greet", "谢谢！", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢你的请客！",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="嗯...这个口味有点特别...谢谢。",
            options=[
                DialogOption("opt_back_greet", "抱歉", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="我们是好朋友了！以后来我这里，我给你最好的酒！",
            options=[
                DialogOption("opt_back_greet", "太好了", "greeting", "none"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="慢走啊！下次再来喝酒！",
            options=[],
        ),
    }


# 守卫队长对话树
def create_guard_dialog(location_name: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"{location_name}的守卫。保持警惕，这里并不太平。",
            options=[
                DialogOption("opt_info", "周边安全情况如何？", "security_info", "show_info"),
                DialogOption("opt_gift", "这是一点心意", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "security_info": DialogNode(
            node_id="security_info",
            text="最近劫匪活动频繁，外出要小心。我会加强巡逻的。",
            options=[
                DialogOption("opt_back_greet", "谢谢提醒", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？你要送我什么？",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，没什么", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="好！我会记住你的。有需要帮忙的时候尽管说。",
            options=[
                DialogOption("opt_back_greet", "谢谢", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢。",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="哼...不需要这些。",
            options=[
                DialogOption("opt_back_greet", "抱歉", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="我们是战友了。在{location_name}，你可以信任我。",
            options=[
                DialogOption("opt_back_greet", "谢谢", "greeting", "none"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="注意安全，冒险者。",
            options=[],
        ),
    }


# 村长对话树
def create_village_elder_dialog(location_name: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"欢迎来到{location_name}，远方的客人。我们是个小村庄，但村民们都很热情。",
            options=[
                DialogOption("opt_quests", "有什么需要帮忙的吗？", "quest_menu", "show_quests"),
                DialogOption("opt_info", "介绍一下村庄", "village_info", "show_info"),
                DialogOption("opt_gift", "这是一点心意", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "quest_menu": DialogNode(
            node_id="quest_menu",
            text="村庄确实需要帮助。你看看这些任务，能帮上忙吗？",
            options=[
                DialogOption("opt_back", "让我看看", "quest_list", "show_quest_list"),
                DialogOption("opt_back_greet", "先不了", "greeting", "none"),
            ],
        ),
        "quest_list": DialogNode(
            node_id="quest_list",
            text="这是村庄目前的困难，选择一个你能帮忙的吧。",
            options=[
                DialogOption("opt_back_greet", "好的，我知道了", "greeting", "none"),
            ],
        ),
        "village_info": DialogNode(
            node_id="village_info",
            text=f"{location_name}虽然不大，但村民们团结一心。我们主要靠农业/畜牧业为生。",
            options=[
                DialogOption("opt_back_greet", "谢谢介绍", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？你要送我们礼物？太客气了。",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，没什么", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="太感谢了！村民们会记住你的善举的！",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢你的心意。",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="嗯...这个...谢谢你的好意。",
            options=[
                DialogOption("opt_back_greet", "抱歉", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="你是我们的好朋友！村庄永远欢迎你的到来。",
            options=[
                DialogOption("opt_back_greet", "谢谢", "greeting", "none"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="一路平安，朋友。愿丰收之神保佑你。",
            options=[],
        ),
    }


# 村民对话树
def create_villager_dialog(location_name: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"你好啊！我是{location_name}的村民。今天天气不错，适合干活。",
            options=[
                DialogOption("opt_info", "村里最近怎么样？", "village_news", "show_info"),
                DialogOption("opt_gift", "这是一点心意", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "village_news": DialogNode(
            node_id="village_news",
            text="最近还不错，收成挺好。就是偶尔有劫匪出没，有点担心。",
            options=[
                DialogOption("opt_back_greet", "我会注意的", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？送我的？太客气了！",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，没什么", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="哇！太棒了！谢谢你！你是我见过最好的人！",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢你的礼物！",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="嗯...这个...好吧，谢谢。",
            options=[
                DialogOption("opt_back_greet", "抱歉", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="我们是好朋友啦！有空常来玩！",
            options=[
                DialogOption("opt_back_greet", "一定", "greeting", "none"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="再见啦！有空再来玩！",
            options=[],
        ),
    }


# 马商对话树
def create_horse_trader_dialog(location_name: str) -> dict[str, DialogNode]:
    return {
        "greeting": DialogNode(
            node_id="greeting",
            text=f"嘿！来看看我的马！{location_name}最好的马都在这里。",
            options=[
                DialogOption("opt_shop", "看看你的马", "shop_view", "open_shop"),
                DialogOption("opt_gift", "这是一点心意", "gift_prompt", "show_gift_selector"),
                DialogOption("opt_favor", "我们关系如何？", "favor_info", "show_favor_info", min_favor=10),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "shop_view": DialogNode(
            node_id="shop_view",
            text="这些都是好马！从草原来的，体格健壮，跑得快！",
            options=[
                DialogOption("opt_back", "让我看看", "shop_open", "open_shop"),
                DialogOption("opt_back_greet", "先不了", "greeting", "none"),
            ],
        ),
        "shop_open": DialogNode(
            node_id="shop_open",
            text="选好了吗？",
            options=[
                DialogOption("opt_back_greet", "再看看", "greeting", "none"),
            ],
        ),
        "gift_prompt": DialogNode(
            node_id="gift_prompt",
            text="哦？你要送我什么？",
            options=[
                DialogOption("opt_gift_select", "[打开礼物列表]", "gift_selection", "open_gift_selector"),
                DialogOption("opt_back_greet", "算了，没什么", "greeting", "none"),
            ],
        ),
        "gift_selection": DialogNode(
            node_id="gift_selection",
            text="请选择要赠送的礼物...",
            options=[
                DialogOption("opt_back_gift", "稍后再说", "gift_prompt", "none"),
            ],
        ),
        "gift_received_good": DialogNode(
            node_id="gift_received_good",
            text="好！下次买马我给你优惠！",
            options=[
                DialogOption("opt_back_greet", "谢谢", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_normal": DialogNode(
            node_id="gift_received_normal",
            text="谢谢。",
            options=[
                DialogOption("opt_back_greet", "不客气", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "gift_received_bad": DialogNode(
            node_id="gift_received_bad",
            text="嗯...不太需要这个。",
            options=[
                DialogOption("opt_back_greet", "抱歉", "greeting", "none"),
                DialogOption("opt_leave", "再见", "farewell", "close"),
            ],
        ),
        "favor_info": DialogNode(
            node_id="favor_info",
            text="我们是朋友了！以后买马找我，给你最低价！",
            options=[
                DialogOption("opt_back_greet", "太好了", "greeting", "none"),
            ],
        ),
        "farewell": DialogNode(
            node_id="farewell",
            text="再见！需要马的时候记得来找我！",
            options=[],
        ),
    }


# ══════════════════════════════════════════════════════════════
# NPC好感度管理
# ══════════════════════════════════════════════════════════════

@dataclass
class NPCFavorState:
    """NPC好感度状态。"""
    user_id: str
    npc_id: str
    favor: int = 0
    total_gifts_given: int = 0
    total_gift_value: int = 0
    last_interaction_time: float = 0.0
    last_interaction_date: str = ""


def get_npc_favor_state(
    player_states: dict, user_id: str, npc_id: str
) -> NPCFavorState:
    """获取或创建玩家-NPC好感度状态。"""
    key = f"{user_id}_{npc_id}"
    if key not in player_states:
        player_states[key] = NPCFavorState(
            user_id=user_id,
            npc_id=npc_id,
        )
    return player_states[key]


def give_gift_to_npc(
    player_states: dict,
    user_id: str,
    npc_id: str,
    gift_id: str,
    player_inventory: list[str] | None = None,
) -> dict:
    """
    赠送礼物给NPC。好感度增益纯基于礼物价值。
    
    Args:
        player_states: 玩家好感度状态字典
        user_id: 玩家ID
        npc_id: NPC ID
        gift_id: 礼物ID
        player_inventory: 玩家背包物品ID列表
    
    Returns:
        dict: 赠送结果
    """
    gift = GIFT_ITEMS.get(gift_id)
    if not gift:
        return {"success": False, "message": "礼物不存在"}
    
    npc = get_npc_by_id(npc_id)
    if not npc:
        return {"success": False, "message": "NPC不存在"}
    
    if player_inventory is not None and gift_id not in player_inventory:
        return {"success": False, "message": "你没有这个礼物"}
    
    state = get_npc_favor_state(player_states, user_id, npc_id)
    
    # 纯价值判定：好感度增益 = 礼物价值 / 10
    favor_gain = max(1, gift.value // 10)
    
    state.favor = min(100, state.favor + favor_gain)
    state.total_gifts_given += 1
    state.total_gift_value += gift.value
    state.last_interaction_time = time.time()
    state.last_interaction_date = datetime.now().strftime("%Y-%m-%d")
    
    # 基于礼物价值的反应判定
    if gift.value >= 100:
        reaction = "good"
        reaction_text = f"{npc.name}非常高兴：\"这份厚礼我收下了！非常感谢！\""
    elif gift.value >= 30:
        reaction = "normal"
        reaction_text = f"{npc.name}微笑着收下：\"谢谢你的礼物。\""
    else:
        reaction = "polite"
        reaction_text = f"{npc.name}礼貌地收下：\"谢谢你的心意。\""
    
    favor_level, favor_attitude = get_npc_favor_level(state.favor)
    
    return {
        "success": True,
        "message": reaction_text,
        "favor_gain": favor_gain,
        "new_favor": state.favor,
        "favor_level": favor_level,
        "favor_attitude": favor_attitude,
        "reaction": reaction,
        "gift_name": gift.name,
        "gift_value": gift.value,
    }


def apply_npc_favor_decay(state: NPCFavorState, current_date: str) -> int:
    """应用NPC好感度衰减。"""
    if state.favor <= 0:
        return 0
    
    if state.last_interaction_date == current_date:
        return 0
    
    days_since = 0
    if state.last_interaction_date:
        try:
            parts = state.last_interaction_date.split("-")
            last_y, last_m, last_d = int(parts[0]), int(parts[1]), int(parts[2])
            cur_parts = current_date.split("-")
            cur_y, cur_m, cur_d = int(cur_parts[0]), int(cur_parts[1]), int(cur_parts[2])
            
            days_last = last_y * 365 + last_m * 30 + last_d
            days_cur = cur_y * 365 + cur_m * 30 + cur_d
            days_since = days_cur - days_last
        except Exception:
            days_since = 0
    
    if days_since >= 14:
        decay = min(state.favor, (days_since - 13) // 2)
        state.favor = max(0, state.favor - decay)
        return decay
    
    return 0


def get_npc_list_for_location(
    player_states: dict, user_id: str, location_id: str, location_name: str = "", location_desc: str = ""
) -> list[dict]:
    """获取据点内所有NPC的信息（含好感度）。"""
    npcs = get_npcs_for_location(location_id)
    result = []
    
    for npc in npcs:
        state = get_npc_favor_state(player_states, user_id, npc.npc_id)
        favor_level, favor_attitude = get_npc_favor_level(state.favor)
        
        result.append({
            "npc_id": npc.npc_id,
            "name": npc.name,
            "title": npc.title,
            "icon": npc.icon,
            "description": npc.description,
            "npc_type": npc.npc_type,
            "personality": npc.personality,
            "favor": state.favor,
            "favor_level": favor_level,
            "favor_attitude": favor_attitude,
            "total_gifts_given": state.total_gifts_given,
            "total_gift_value": state.total_gift_value,
        })
    
    return result


def get_npc_dialog_data(
    player_states: dict, user_id: str, npc_id: str,
    location_name: str = "", location_desc: str = ""
) -> dict:
    """获取NPC对话数据。"""
    npc = get_npc_by_id(npc_id)
    if not npc:
        return {"success": False, "message": "NPC不存在"}
    
    state = get_npc_favor_state(player_states, user_id, npc_id)
    dialog_tree = create_dialog_for_npc(npc, location_name, location_desc)
    
    dialog_data = {}
    for node_id, node in dialog_tree.items():
        dialog_data[node_id] = {
            "node_id": node.node_id,
            "text": node.text,
            "options": [
                {
                    "option_id": opt.option_id,
                    "text": opt.text,
                    "next_node": opt.next_node,
                    "action": opt.action,
                    "action_data": opt.action_data,
                    "min_favor": opt.min_favor,
                    "available": state.favor >= opt.min_favor,
                }
                for opt in node.options
            ],
        }
    
    return {
        "success": True,
        "npc_id": npc_id,
        "npc_name": npc.name,
        "npc_title": npc.title,
        "npc_icon": npc.icon,
        "favor": state.favor,
        "favor_level": get_npc_favor_level(state.favor)[0],
        "dialog_tree": dialog_data,
        "start_node": "greeting",
    }


# ══════════════════════════════════════════════════════════════
# 兼容性函数（供engine.py调用）
# ══════════════════════════════════════════════════════════════

_npc_favor_states: dict = {}


def get_favor_level(favor: int) -> str:
    """兼容性函数：获取好感度等级名称。"""
    name, _ = get_npc_favor_level(favor)
    return name


FAVOR_LEVELS = {
    threshold: name for threshold, name, _ in NPC_FAVOR_LEVELS
}


def get_dialog_for_npc(npc: NPC, location_name: str = "", favor: int = 0) -> dict[str, DialogNode]:
    """兼容性函数：获取NPC对话树（根据好感度过滤选项）。"""
    dialog_tree = create_dialog_for_npc(npc, location_name)
    
    filtered = {}
    for node_id, node in dialog_tree.items():
        filtered_options = [opt for opt in node.options if favor >= opt.min_favor]
        filtered[node_id] = DialogNode(
            node_id=node.node_id,
            text=node.text,
            options=filtered_options,
        )
    
    return filtered


def give_gift_to_npc_compat(
    user_id: str,
    npc_id: str,
    gift_id: str,
    gift_value: int = 0,
    player_inventory: list[str] | None = None,
) -> dict:
    """
    兼容性函数：赠送礼物给NPC（供engine.py调用）。
    使用全局状态字典管理好感度。纯价值判定。
    """
    global _npc_favor_states
    
    gift = GIFT_ITEMS.get(gift_id)
    if not gift:
        return {"success": False, "message": "礼物不存在"}
    
    npc = get_npc_by_id(npc_id)
    if not npc:
        return {"success": False, "message": "NPC不存在"}
    
    if player_inventory is not None and gift_id not in player_inventory:
        return {"success": False, "message": "你没有这个礼物"}
    
    state = get_npc_favor_state(_npc_favor_states, user_id, npc_id)
    
    # 纯价值判定
    favor_gain = max(1, gift.value // 10)
    
    state.favor = min(100, state.favor + favor_gain)
    state.total_gifts_given += 1
    state.total_gift_value += gift.value
    state.last_interaction_time = time.time()
    state.last_interaction_date = datetime.now().strftime("%Y-%m-%d")
    
    if gift.value >= 100:
        reaction = "good"
        reaction_text = f"{npc.name}非常高兴：\"这份厚礼我收下了！非常感谢！\""
    elif gift.value >= 30:
        reaction = "normal"
        reaction_text = f"{npc.name}微笑着收下：\"谢谢你的礼物。\""
    else:
        reaction = "polite"
        reaction_text = f"{npc.name}礼貌地收下：\"谢谢你的心意。\""
    
    favor_level, favor_attitude = get_npc_favor_level(state.favor)
    
    return {
        "success": True,
        "message": reaction_text,
        "favor_gain": favor_gain,
        "new_favor": state.favor,
        "favor_level": favor_level,
        "favor_attitude": favor_attitude,
        "reaction": reaction,
        "gift_name": gift.name,
        "gift_value": gift.value,
    }


# engine.py compatibility alias
give_gift_to_npc = give_gift_to_npc_compat
