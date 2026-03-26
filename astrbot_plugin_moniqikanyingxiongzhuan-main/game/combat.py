"""回合制战斗引擎 - 骑砍风格。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .constants import (
    GONGFA_REGISTRY, ITEM_REGISTRY, COMBAT_MAX_ROUNDS,
    get_gongfa_bonus, get_heart_method_bonus,
    get_total_gongfa_bonus,
)
from .inventory import add_item


@dataclass
class CombatState:
    """战斗状态快照。"""
    player_hp: int
    player_max_hp: int
    player_attack: int
    player_defense: int
    player_lingqi: int
    player_max_lingqi: int
    player_defending: bool = False
    player_shield_stun: int = 0  # 盾击眩晕回合数
    player_berserk: int = 0      # 狂暴状态持续回合
    player_weakened: int = 0     # 虚弱状态持续回合
    enemy_name: str = ""
    enemy_type: str = "monster"  # monster | enemy | player
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_attack: int = 0
    enemy_defense: int = 0
    enemy_stunned: int = 0       # 敌人眩晕回合数
    enemy_weakened: int = 0      # 敌人虚弱回合数
    enemy_realm_name: str = ""
    round_number: int = 0
    max_rounds: int = COMBAT_MAX_ROUNDS
    combat_log: list[str] = field(default_factory=list)
    status: str = "player_turn"  # player_turn | enemy_turn | combat_end

    def to_dict(self) -> dict:
        return {
            "player_hp": self.player_hp,
            "player_max_hp": self.player_max_hp,
            "player_attack": self.player_attack,
            "player_defense": self.player_defense,
            "player_lingqi": self.player_lingqi,
            "player_max_lingqi": self.player_max_lingqi,
            "player_defending": self.player_defending,
            "player_shield_stun": self.player_shield_stun,
            "player_berserk": self.player_berserk,
            "player_weakened": self.player_weakened,
            "enemy_name": self.enemy_name,
            "enemy_type": self.enemy_type,
            "enemy_hp": self.enemy_hp,
            "enemy_max_hp": self.enemy_max_hp,
            "enemy_attack": self.enemy_attack,
            "enemy_defense": self.enemy_defense,
            "enemy_stunned": self.enemy_stunned,
            "enemy_weakened": self.enemy_weakened,
            "enemy_realm_name": self.enemy_realm_name,
            "round_number": self.round_number,
            "max_rounds": self.max_rounds,
            "combat_log": list(self.combat_log[-20:]),
            "status": self.status,
        }


class CombatEngine:
    """回合制战斗引擎，处理玩家动作和敌人AI - 骑砍风格。"""

    @staticmethod
    def _calc_damage(atk: int, dfn: int, defending: bool) -> int:
        """基础伤害公式。"""
        raw = max(1, int(atk * random.uniform(0.85, 1.15) - dfn * 0.6))
        if defending:
            raw = max(1, raw // 2)
        return raw

    @staticmethod
    def resolve_player_action(
        state: CombatState, action: str, player, data: dict | None = None
    ) -> dict:
        """处理玩家回合动作 - 骑砍风格。

        action: attack | defend | gongfa | item | flee | charge | shield_bash | battle_cry | berserk | feint
        返回 {"success": bool, "message": str, "combat_end": bool, ...}
        """
        if state.status != "player_turn":
            return {"success": False, "message": "当前不是你的回合"}

        data = data or {}
        if action == "skill":
            action = "gongfa"
        state.player_defending = False
        result: dict = {"success": True, "combat_end": False, "message": ""}

        # 检查敌人是否眩晕
        if state.enemy_stunned > 0:
            state.enemy_stunned -= 1
            msg = f"敌人仍然眩晕中，无法行动！"
            state.combat_log.append(msg)
            result["message"] = msg
            state.status = "enemy_turn"
            return result

        # 检查玩家狂暴状态
        if state.player_berserk > 0:
            state.player_berserk -= 1

        if action == "attack":
            # 狂暴状态加成
            atk_bonus = int(state.player_attack * 0.3) if state.player_berserk > 0 else 0
            dmg = CombatEngine._calc_damage(
                state.player_attack + atk_bonus, state.enemy_defense, False
            )
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            msg = f"你发动攻击，造成{dmg}点伤害"
            if atk_bonus > 0:
                msg += f"（狂暴加成+{atk_bonus}）"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg

        elif action == "defend":
            state.player_defending = True
            msg = "你摆出防御姿态，本回合受到伤害减半"
            state.combat_log.append(msg)
            result["message"] = msg

        elif action == "charge":
            # 冲锋 - 高伤害但消耗体力
            charge_cost = 20
            if state.player_lingqi < charge_cost:
                return {"success": False, "message": f"体力不足，需要{charge_cost}体力"}
            state.player_lingqi -= charge_cost
            
            # 冲锋伤害增加50%
            dmg = int(CombatEngine._calc_damage(
                state.player_attack, state.enemy_defense, False
            ) * 1.5)
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            msg = f"你发起冲锋！造成{dmg}点伤害！（消耗{charge_cost}体力）"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg

        elif action == "shield_bash":
            # 盾击 - 眩晕敌人
            shield_cost = 15
            if state.player_lingqi < shield_cost:
                return {"success": False, "message": f"体力不足，需要{shield_cost}体力"}
            state.player_lingqi -= shield_cost
            
            dmg = CombatEngine._calc_damage(
                state.player_attack, state.enemy_defense, False
            )
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            state.enemy_stunned = 1  # 眩晕1回合
            msg = f"你用盾牌猛击！造成{dmg}点伤害，敌人眩晕1回合！（消耗{shield_cost}体力）"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg

        elif action == "battle_cry":
            # 战吼 - 降低敌人防御
            cry_cost = 18
            if state.player_lingqi < cry_cost:
                return {"success": False, "message": f"体力不足，需要{cry_cost}体力"}
            state.player_lingqi -= cry_cost
            
            weaken = int(state.enemy_defense * 0.25)
            state.enemy_weakened = 2  # 虚弱2回合
            msg = f"你发出震天的战吼！敌人防御力下降{weaken}点！（消耗{cry_cost}体力）"
            state.combat_log.append(msg)
            result["message"] = msg

        elif action == "berserk":
            # 狂暴 - 大幅提升攻击，降低防御
            berserk_cost = 25
            if state.player_lingqi < berserk_cost:
                return {"success": False, "message": f"体力不足，需要{berserk_cost}体力"}
            state.player_lingqi -= berserk_cost
            
            state.player_berserk = 2  # 持续2回合
            state.player_defending = True  # 狂暴时自动防御
            msg = f"你进入狂暴状态！接下来2回合攻击+30%，但会自动防御！（消耗{berserk_cost}体力）"
            state.combat_log.append(msg)
            result["message"] = msg

        elif action == "feint":
            # 虚晃 - 闪避敌人攻击
            feint_cost = 12
            if state.player_lingqi < feint_cost:
                return {"success": False, "message": f"体力不足，需要{feint_cost}体力"}
            state.player_lingqi -= feint_cost
            
            msg = f"你虚晃一招，敌人扑空！下回合必定闪避攻击！（消耗{feint_cost}体力）"
            state.combat_log.append(msg)
            result["message"] = msg
            result["feint_success"] = True

        elif action == "gongfa":
            gf_result = CombatEngine._apply_gongfa_effect(state, player, data)
            result.update(gf_result)
            if not gf_result["success"]:
                return result

        elif action == "item":
            item_result = CombatEngine._apply_item(state, player, data)
            result.update(item_result)
            if not item_result["success"]:
                return result

        elif action == "flee":
            flee_result = CombatEngine._try_flee(state, data.get("layer", 0))
            result.update(flee_result)
            if flee_result.get("fled"):
                state.status = "combat_end"
                result["combat_end"] = True
                result["outcome"] = "flee"
                return result

        else:
            return {"success": False, "message": f"未知动作: {action}"}

        # 检查敌人是否死亡
        if state.enemy_hp <= 0:
            state.status = "combat_end"
            msg = f"你击败了{state.enemy_name}！"
            state.combat_log.append(msg)
            result["combat_end"] = True
            result["outcome"] = "win"
            result["message"] += f"\n{msg}" if result["message"] else msg
            return result

        # 切换到敌人回合
        state.status = "enemy_turn"
        return result

    @staticmethod
    def resolve_enemy_turn(state: CombatState) -> dict:
        """处理敌人回合 - 骑砍风格。"""
        if state.status != "enemy_turn":
            return {"success": False, "message": "当前不是敌人回合"}

        state.round_number += 1
        result: dict = {"success": True, "combat_end": False}

        # 检查玩家是否眩晕
        if state.player_shield_stun > 0:
            state.player_shield_stun -= 1
            msg = f"你被眩晕，无法行动！"
            state.combat_log.append(msg)
            result["message"] = msg
            state.status = "player_turn"
            return result

        # 虚弱状态处理
        if state.enemy_weakened > 0:
            state.enemy_weakened -= 1
        effective_def = state.player_defense
        if state.enemy_weakened > 0:
            effective_def = int(effective_def * 1.25)  # 虚弱时防御增加

        # 敌人AI: 70%攻击, 20%防御, 10%特殊动作
        roll = random.random()
        if roll < 0.7:
            dmg = CombatEngine._calc_damage(
                state.enemy_attack, effective_def, state.player_defending
            )
            state.player_hp = max(0, state.player_hp - dmg)
            msg = f"{state.enemy_name}发动攻击，造成{dmg}点伤害"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg
        elif roll < 0.9:
            msg = f"{state.enemy_name}摆出防御姿态"
            state.combat_log.append(msg)
            result["message"] = msg
        else:
            # 敌人特殊攻击
            special_dmg = int(CombatEngine._calc_damage(
                state.enemy_attack, effective_def, False
            ) * 1.3)
            state.player_hp = max(0, state.player_hp - special_dmg)
            msg = f"{state.enemy_name}使出强力攻击！造成{special_dmg}点伤害！"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = special_dmg

        # 重置玩家状态
        state.player_defending = False

        # 检查玩家是否死亡
        if state.player_hp <= 0:
            state.status = "combat_end"
            msg = f"你被{state.enemy_name}击败了……"
            state.combat_log.append(msg)
            result["combat_end"] = True
            result["outcome"] = "lose"
            result["message"] += f"\n{msg}"
            return result

        # 检查回合上限
        if state.round_number >= state.max_rounds:
            state.status = "combat_end"
            msg = "战斗超时，双方脱离战斗"
            state.combat_log.append(msg)
            result["combat_end"] = True
            result["outcome"] = "timeout"
            result["message"] += f"\n{msg}"
            return result

        state.status = "player_turn"
        return result

    @staticmethod
    def _apply_gongfa_effect(
        state: CombatState, player, data: dict
    ) -> dict:
        """施展战斗技能效果 - 骑砍风格。"""
        gongfa_slot = data.get("gongfa_slot", "")
        if gongfa_slot not in ("gongfa_1", "gongfa_2", "gongfa_3"):
            return {"success": False, "message": "无效的战斗技能槽位"}

        gongfa_id = getattr(player, gongfa_slot, "无")
        if not gongfa_id or gongfa_id == "无":
            return {"success": False, "message": "该槽位没有装备战斗技能"}

        gf = GONGFA_REGISTRY.get(gongfa_id)
        if not gf:
            return {"success": False, "message": "战斗技能数据异常"}

        # 体力消耗检查（恢复类技能免费）
        is_regen = gf.attack_bonus == 0 and gf.defense_bonus == 0 and gf.hp_regen == 0
        if not is_regen and state.player_lingqi < gf.lingqi_cost:
            return {
                "success": False,
                "message": f"体力不足，需要{gf.lingqi_cost}，当前{state.player_lingqi}",
            }

        if not is_regen:
            state.player_lingqi -= gf.lingqi_cost

        mastery = getattr(player, f"{gongfa_slot}_mastery", 0)
        bonus = get_gongfa_bonus(gongfa_id, mastery, player.realm)
        msgs: list[str] = []

        # 攻击效果
        if bonus["attack_bonus"] > 0:
            dmg = CombatEngine._calc_damage(
                state.player_attack + int(bonus["attack_bonus"] * 1.5),
                state.enemy_defense, False,
            )
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            msgs.append(f"技能攻击造成{dmg}点伤害")

        # 防御效果
        if bonus["defense_bonus"] > 0:
            shield = int(bonus["defense_bonus"] * 2)
            state.player_defending = True
            msgs.append(f"获得{shield}点护盾（本回合减伤）")

        # 回血效果
        if bonus["hp_regen"] > 0:
            heal = int(bonus["hp_regen"] * 3)
            old_hp = state.player_hp
            state.player_hp = min(state.player_max_hp, state.player_hp + heal)
            actual = state.player_hp - old_hp
            msgs.append(f"恢复{actual}点HP")

        # 回体力效果
        if bonus["lingqi_regen"] > 0:
            regen = int(bonus["lingqi_regen"] * 2)
            state.player_lingqi = min(
                state.player_max_lingqi, state.player_lingqi + regen
            )
            msgs.append(f"恢复{regen}点体力")

        if not msgs:
            msgs.append("战斗技能施展完毕")

        cost_msg = f"（消耗{gf.lingqi_cost}体力）" if not is_regen else "（免费）"
        full_msg = f"施展【{gf.name}】{cost_msg}：{'，'.join(msgs)}"
        state.combat_log.append(full_msg)
        return {"success": True, "message": full_msg}

    @staticmethod
    def _apply_item(state: CombatState, player, data: dict) -> dict:
        """战斗中使用物品（药剂）- 骑砍风格。"""
        item_id = data.get("item_id", "")
        if not item_id:
            return {"success": False, "message": "未指定物品"}

        item_def = ITEM_REGISTRY.get(item_id)
        if not item_def:
            return {"success": False, "message": "物品不存在"}

        count = player.inventory.get(item_id, 0)
        if count <= 0:
            return {"success": False, "message": "背包中没有该物品"}

        # 消耗物品
        player.inventory[item_id] = count - 1
        if player.inventory[item_id] <= 0:
            del player.inventory[item_id]

        # 处理物品效果
        heal = 0
        effect = item_def.effect or {}
        if "heal_hp" in effect:
            heal = int(effect["heal_hp"])
        elif "exp_bonus" in effect:
            # 经验物品不适用于战斗
            heal = 0
        
        if heal <= 0:
            heal = max(1, state.player_max_hp // 5)

        old_hp = state.player_hp
        state.player_hp = min(state.player_max_hp, state.player_hp + heal)
        actual = state.player_hp - old_hp
        msg = f"使用【{item_def.name}】，恢复{actual}点HP"
        state.combat_log.append(msg)
        return {"success": True, "message": msg}

    @staticmethod
    def _try_flee(state: CombatState, layer: int) -> dict:
        """尝试投降（骑砍风格）"""
        from .constants import FLEE_BASE_RATES
        layer = max(0, min(layer, len(FLEE_BASE_RATES) - 1))
        flee_rate = FLEE_BASE_RATES[layer]
        if random.random() < flee_rate:
            msg = "你成功逃离了战斗！"
            state.combat_log.append(msg)
            return {"success": True, "fled": True, "message": msg}
        else:
            msg = "投降失败！"
            state.combat_log.append(msg)
            return {"success": True, "fled": False, "message": msg}


# ══════════════════════════════════════════════════════════════
# 骑砍风格战斗动作列表
# ══════════════════════════════════════════════════════════════

MB_COMBAT_ACTIONS = {
    "attack": {
        "name": "攻击",
        "name_en": "Attack",
        "desc": "普通攻击",
        "cost": 0,
        "type": "basic",
    },
    "defend": {
        "name": "防御",
        "name_en": "Defend",
        "desc": "本回合伤害减半",
        "cost": 0,
        "type": "basic",
    },
    "charge": {
        "name": "冲锋",
        "name_en": "Charge",
        "desc": "高伤害冲锋，消耗20体力",
        "cost": 20,
        "type": "mb_skill",
    },
    "shield_bash": {
        "name": "盾击",
        "name_en": "Shield Bash",
        "desc": "用盾牌眩晕敌人1回合，消耗15体力",
        "cost": 15,
        "type": "mb_skill",
    },
    "battle_cry": {
        "name": "战吼",
        "name_en": "Battle Cry",
        "desc": "降低敌人防御2回合，消耗18体力",
        "cost": 18,
        "type": "mb_skill",
    },
    "berserk": {
        "name": "狂暴",
        "name_en": "Berserk",
        "desc": "2回合内攻击+30%，自动防御，消耗25体力",
        "cost": 25,
        "type": "mb_skill",
    },
    "feint": {
        "name": "虚晃",
        "name_en": "Feint",
        "desc": "下回合必定闪避，消耗12体力",
        "cost": 12,
        "type": "mb_skill",
    },
    "flee": {
        "name": "投降",
        "name_en": "Flee",
        "desc": "尝试逃离战斗",
        "cost": 0,
        "type": "escape",
    },
    "item": {
        "name": "使用药剂",
        "name_en": "Use Item",
        "desc": "使用背包中的药剂",
        "cost": 0,
        "type": "utility",
    },
    "gongfa": {
        "name": "战斗技能",
        "name_en": "Combat Skill",
        "desc": "使用已装备的战斗技能",
        "cost": 0,
        "type": "skill",
    },
}


def get_combat_actions() -> dict:
    """获取所有可用战斗动作。"""
    return MB_COMBAT_ACTIONS


def get_action_info(action: str) -> dict | None:
    """获取动作信息。"""
    return MB_COMBAT_ACTIONS.get(action)
