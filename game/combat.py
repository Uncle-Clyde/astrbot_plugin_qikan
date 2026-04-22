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
from .companions import get_companion_buff, PlayerCompanion
from .troops import calc_troop_damage


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
    player_combo: int = 0         # 连击计数
    player_crit_chance: float = 0.05  # 暴击率
    skill_cooldowns: dict[str, int] = field(default_factory=dict)  # 技能冷却 {action: remaining_rounds}
    enemy_name: str = ""
    enemy_type: str = "monster"  # monster | enemy | player
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_attack: int = 0
    enemy_defense: int = 0
    enemy_stunned: int = 0       # 敌人眩晕回合数
    enemy_weakened: int = 0      # 敌人虚弱回合数
    enemy_realm_name: str = ""
    enemy_intent: str = ""       # 敌人下回合意图
    round_number: int = 0
    max_rounds: int = COMBAT_MAX_ROUNDS
    combat_log: list[str] = field(default_factory=list)
    status: str = "player_turn"  # player_turn | enemy_turn | combat_end
    total_damage_dealt: int = 0  # 累计伤害
    total_damage_taken: int = 0  # 累计受伤

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
            "player_combo": self.player_combo,
            "player_crit_chance": self.player_crit_chance,
            "skill_cooldowns": dict(self.skill_cooldowns),
            "enemy_name": self.enemy_name,
            "enemy_type": self.enemy_type,
            "enemy_hp": self.enemy_hp,
            "enemy_max_hp": self.enemy_max_hp,
            "enemy_attack": self.enemy_attack,
            "enemy_defense": self.enemy_defense,
            "enemy_stunned": self.enemy_stunned,
            "enemy_weakened": self.enemy_weakened,
            "enemy_realm_name": self.enemy_realm_name,
            "enemy_intent": self.enemy_intent,
            "round_number": self.round_number,
            "max_rounds": self.max_rounds,
            "combat_log": list(self.combat_log[-20:]),
            "status": self.status,
        }


class CombatEngine:
    """回合制战斗引擎，处理玩家动作和敌人AI - 骑砍风格。"""

    @staticmethod
    def _calc_damage(atk: int, dfn: int, defending: bool, crit_chance: float = 0, combo: int = 0) -> tuple[int, bool]:
        """基础伤害公式。返回(伤害值, 是否暴击)。"""
        atk = max(0, int(atk or 0))
        dfn = max(0, int(dfn or 0))
        crit_chance = max(0.0, min(1.0, float(crit_chance or 0)))
        combo = max(0, int(combo or 0))

        is_crit = random.random() < crit_chance
        crit_multiplier = 1.5 if is_crit else 1.0

        combo_bonus = 1.0 + (combo * 0.05) if combo > 0 else 1.0

        raw = max(1, int(atk * random.uniform(0.85, 1.15) * crit_multiplier * combo_bonus - dfn * 0.6))
        if defending:
            raw = max(1, raw // 2)
        return raw, is_crit

    @staticmethod
    def _get_combat_bonuses(player) -> dict:
        """计算同伴和部队提供的战斗加成。"""
        attack_bonus = 0
        defense_bonus = 0
        hp_bonus = 0
        crit_bonus = 0.0

        # 同伴加成
        if hasattr(player, 'active_companions'):
            for comp in player.active_companions:
                if isinstance(comp, PlayerCompanion) and comp.is_active:
                    buff = get_companion_buff(comp)
                    attack_bonus += buff.get("attack", 0)
                    defense_bonus += buff.get("defense", 0)
                    hp_bonus += buff.get("hp", 0)
                    crit_bonus += buff.get("crit", 0)

        # 部队加成
        if hasattr(player, 'troops') and player.troops:
            troop_atk = calc_troop_damage(player.troops)
            attack_bonus += troop_atk

        return {
            "attack": attack_bonus,
            "defense": defense_bonus,
            "hp": hp_bonus,
            "crit": crit_bonus,
        }

    @staticmethod
    def resolve_player_action(
        state: CombatState, action: str, player, data: dict | None = None
    ) -> dict:
        """处理玩家回合动作 - 骑砍风格。

        action: attack | defend | gongfa | item | flee | charge | shield_bash | berserk
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

        # 递减技能冷却
        expired_skills = []
        for skill_name, remaining in state.skill_cooldowns.items():
            if remaining <= 1:
                expired_skills.append(skill_name)
            else:
                state.skill_cooldowns[skill_name] = remaining - 1
        for skill_name in expired_skills:
            del state.skill_cooldowns[skill_name]

        # 检查玩家狂暴状态
        if state.player_berserk > 0:
            state.player_berserk -= 1

        if action == "attack":
            atk_bonus = int(state.player_attack * 0.3) if state.player_berserk > 0 else 0
            
            dmg, is_crit = CombatEngine._calc_damage(
                state.player_attack + atk_bonus, 
                state.enemy_defense, 
                False,
                state.player_crit_chance,
                state.player_combo
            )
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            state.player_combo = min(state.player_combo + 1, 10)
            state.total_damage_dealt += dmg
            
            msg = f"你发动攻击，造成{dmg}点伤害"
            if is_crit:
                msg = f"你发动攻击，造成{dmg}点暴击伤害！"
            if atk_bonus > 0:
                msg += f"（狂暴+{atk_bonus}）"
            if state.player_combo > 1:
                msg += f"（连击x{state.player_combo}）"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg
            result["is_crit"] = is_crit
            result["combo"] = state.player_combo

        elif action == "defend":
            state.player_defending = True
            msg = "你摆出防御姿态，本回合受到伤害减半"
            state.combat_log.append(msg)
            result["message"] = msg

        elif action == "charge":
            if state.skill_cooldowns.get("charge", 0) > 0:
                return {"success": False, "message": f"冲锋冷却中，还需{state.skill_cooldowns['charge']}回合"}
            charge_cost = 20
            if state.player_lingqi < charge_cost:
                return {"success": False, "message": f"体力不足，需要{charge_cost}体力"}
            state.player_lingqi -= charge_cost
            state.skill_cooldowns["charge"] = 2
            
            # 冲锋伤害增加50%
            dmg, _ = CombatEngine._calc_damage(
                state.player_attack, state.enemy_defense, False, state.player_crit_chance, state.player_combo
            )
            dmg = int(dmg * 1.5)
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            state.player_combo = min(state.player_combo + 1, 10)
            state.total_damage_dealt += dmg
            msg = f"你发起冲锋！造成{dmg}点伤害！（消耗{charge_cost}体力，冷却2回合）"
            if state.player_combo > 1:
                msg += f"（连击x{state.player_combo}）"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg

        elif action == "shield_bash":
            if state.skill_cooldowns.get("shield_bash", 0) > 0:
                return {"success": False, "message": f"盾击冷却中，还需{state.skill_cooldowns['shield_bash']}回合"}
            shield_cost = 15
            if state.player_lingqi < shield_cost:
                return {"success": False, "message": f"体力不足，需要{shield_cost}体力"}
            state.player_lingqi -= shield_cost
            state.skill_cooldowns["shield_bash"] = 2
            
            dmg, _ = CombatEngine._calc_damage(
                state.player_attack, state.enemy_defense, False, state.player_crit_chance, state.player_combo
            )
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            state.enemy_stunned = 1
            state.player_combo = min(state.player_combo + 1, 10)
            state.total_damage_dealt += dmg
            msg = f"你用盾牌猛击！造成{dmg}点伤害，敌人眩晕1回合！（消耗{shield_cost}体力，冷却2回合）"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg

        elif action == "berserk":
            if state.skill_cooldowns.get("berserk", 0) > 0:
                return {"success": False, "message": f"狂暴冷却中，还需{state.skill_cooldowns['berserk']}回合"}
            berserk_cost = 25
            if state.player_lingqi < berserk_cost:
                return {"success": False, "message": f"体力不足，需要{berserk_cost}体力"}
            state.player_lingqi -= berserk_cost
            state.skill_cooldowns["berserk"] = 3
            
            state.player_berserk = 2  # 持续2回合
            state.player_defending = True  # 狂暴时自动防御
            msg = f"你进入狂暴状态！接下来2回合攻击+30%，但会自动防御！（消耗{berserk_cost}体力）"
            state.combat_log.append(msg)
            result["message"] = msg

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

        # 虚弱状态处理 - 降低敌人攻击力
        if state.enemy_weakened > 0:
            state.enemy_weakened -= 1
        effective_enemy_atk = state.enemy_attack
        if state.enemy_weakened > 0:
            effective_enemy_atk = int(effective_enemy_atk * 0.75)  # 敌人攻击降低25%

        # 敌人AI - 自适应策略
        enemy_hp_pct = state.enemy_hp / state.enemy_max_hp if state.enemy_max_hp > 0 else 1.0
        player_hp_pct = state.player_hp / state.player_max_hp if state.player_max_hp > 0 else 1.0
        
        # 低血量时提高防御概率
        if enemy_hp_pct < 0.15:
            # 濒死时30%概率防御
            roll = random.random()
            if roll < 0.5:
                action_choice = "attack"
            elif roll < 0.8:
                action_choice = "defend"
            else:
                action_choice = "special"
        elif enemy_hp_pct < 0.3:
            # 低血量时提高防御
            roll = random.random()
            if roll < 0.5:
                action_choice = "attack"
            elif roll < 0.85:
                action_choice = "defend"
            else:
                action_choice = "special"
        elif state.player_defending:
            # 玩家防御时提高特殊攻击概率
            roll = random.random()
            if roll < 0.5:
                action_choice = "attack"
            elif roll < 0.7:
                action_choice = "defend"
            else:
                action_choice = "special"
        else:
            # 正常状态
            roll = random.random()
            if roll < 0.7:
                action_choice = "attack"
            elif roll < 0.9:
                action_choice = "defend"
            else:
                action_choice = "special"
        
        # 显示敌人意图
        state.enemy_intent = action_choice
        
        # 执行敌人行动
        if action_choice == "attack":
            dmg, _ = CombatEngine._calc_damage(
                effective_enemy_atk, state.player_defense, state.player_defending
            )
            state.player_hp = max(0, state.player_hp - dmg)
            state.total_damage_taken += dmg
            msg = f"{state.enemy_name}发动攻击，造成{dmg}点伤害"
            state.combat_log.append(msg)
            result["message"] = msg
            result["damage"] = dmg
            state.player_combo = 0
        elif action_choice == "defend":
            msg = f"{state.enemy_name}摆出防御姿态"
            state.combat_log.append(msg)
            result["message"] = msg
        else:
            special_dmg, _ = CombatEngine._calc_damage(
                effective_enemy_atk, state.player_defense, False
            )
            special_dmg = int(special_dmg * 1.3)
            state.player_hp = max(0, state.player_hp - special_dmg)
            state.total_damage_taken += special_dmg
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
            dmg, is_crit = CombatEngine._calc_damage(
                state.player_attack + int(bonus["attack_bonus"] * 1.5),
                state.enemy_defense, False, state.player_crit_chance, state.player_combo
            )
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            state.player_combo = min(state.player_combo + 1, 10)
            state.total_damage_dealt += dmg
            crit_msg = "暴击！" if is_crit else ""
            msgs.append(f"技能攻击造成{dmg}点伤害{crit_msg}")

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
        "desc": "高伤害冲锋，消耗20体力，冷却2回合",
        "cost": 20,
        "cooldown": 2,
        "type": "mb_skill",
    },
    "shield_bash": {
        "name": "盾击",
        "name_en": "Shield Bash",
        "desc": "用盾牌眩晕敌人1回合，消耗15体力，冷却2回合",
        "cost": 15,
        "cooldown": 2,
        "type": "mb_skill",
    },
    "berserk": {
        "name": "狂暴",
        "name_en": "Berserk",
        "desc": "2回合内攻击+30%，自动防御，消耗25体力，冷却3回合",
        "cost": 25,
        "cooldown": 3,
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
