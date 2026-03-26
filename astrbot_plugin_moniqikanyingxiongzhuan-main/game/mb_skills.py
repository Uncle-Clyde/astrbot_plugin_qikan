"""
骑砍技能系统 - Mount & Blade 风格技能
包含被动技能(Heart Methods)和战斗技能(Gongfas)
"""

from .constants import (
    HeartMethodDef, GongfaDef,
    HEART_METHOD_REGISTRY, GONGFA_REGISTRY,
    HeartMethodQuality, GongfaTier,
    RealmLevel,
)


def _hm(method_id: str, name: str, realm: int, quality: int,
         exp_mult: float, atk: int, dfn: int, dao_rate: float,
         desc: str = "", mastery_exp: int = 100) -> HeartMethodDef:
    """被动技能定义快捷构造。"""
    return HeartMethodDef(
        method_id=method_id, name=name, realm=realm, quality=quality,
        exp_multiplier=exp_mult, attack_bonus=atk, defense_bonus=dfn,
        dao_yun_rate=dao_rate, description=desc, mastery_exp=mastery_exp,
    )


def _gf(gongfa_id: str, name: str, tier: int,
         atk: int, dfn: int, hp_r: int, lq_r: int,
         desc: str = "", mastery_exp: int = 200,
         dao_yun_cost: int = 0, recycle_price: int = 1000,
         lingqi_cost: int = 0) -> GongfaDef:
    """战斗技能定义快捷构造。"""
    return GongfaDef(
        gongfa_id=gongfa_id, name=name, tier=tier,
        attack_bonus=atk, defense_bonus=dfn,
        hp_regen=hp_r, lingqi_regen=lq_r,
        description=desc, mastery_exp=mastery_exp,
        dao_yun_cost=dao_yun_cost, recycle_price=recycle_price,
        lingqi_cost=lingqi_cost,
    )


# ══════════════════════════════════════════════════════════════
# 被动技能 - 骑砍技能树 (Heart Methods)
# ══════════════════════════════════════════════════════════════

# ── 强击技能树 (Power Strike) ──────────────────────────────
# 增加近战武器伤害
_MB_POWER_STRIKE = [
    _hm("mb_ps_01", "强击·初级", 0, 0, 0.05, 5, 0, 0.02, "增加近战武器伤害", 80),
    _hm("mb_ps_02", "强击·中级", 1, 0, 0.06, 12, 0, 0.03, "进一步提高伤害", 160),
    _hm("mb_ps_03", "强击·高级", 2, 1, 0.08, 25, 0, 0.04, "大幅增加伤害", 320),
    _hm("mb_ps_04", "强击·大师", 3, 1, 0.10, 50, 5, 0.05, "伤害接近翻倍", 640),
    _hm("mb_ps_05", "强击·宗师", 4, 2, 0.15, 100, 10, 0.08, "毁灭性打击", 1280),
]

# ── 铁骨技能树 (Iron Fist/Health) ─────────────────────────
# 增加生命值上限
_MB_IRON_FIST = [
    _hm("mb_if_01", "铁骨·初级", 0, 0, 0.05, 0, 0, 0.02, "增加生命值上限", 80),
    _hm("mb_if_02", "铁骨·中级", 1, 0, 0.06, 0, 0, 0.03, "进一步提高生命", 160),
    _hm("mb_if_03", "铁骨·高级", 2, 1, 0.08, 0, 0, 0.04, "生命值大幅增加", 320),
    _hm("mb_if_04", "铁骨·大师", 3, 1, 0.10, 5, 10, 0.05, "如钢铁般坚硬", 640),
    _hm("mb_if_05", "铁骨·宗师", 4, 2, 0.15, 10, 20, 0.08, "不死的意志", 1280),
]

# ── 盾击技能树 (Shield Bash) ──────────────────────────────
# 增加盾牌防御和盾击伤害
_MB_SHIELD_BASH = [
    _hm("mb_sb_01", "盾击·初级", 0, 0, 0.05, 2, 5, 0.02, "用盾牌攻击敌人", 80),
    _hm("mb_sb_02", "盾击·中级", 1, 0, 0.06, 5, 10, 0.03, "更有效的盾击", 160),
    _hm("mb_sb_03", "盾击·高级", 2, 1, 0.08, 10, 20, 0.04, "盾牌如战锤", 320),
    _hm("mb_sb_04", "盾击·大师", 3, 1, 0.10, 20, 40, 0.05, "盾击可击晕敌人", 640),
    _hm("mb_sb_05", "盾击·宗师", 4, 2, 0.15, 35, 70, 0.08, "破城锤般的盾击", 1280),
]

# ── 跑动技能树 (Athletics) ────────────────────────────────
# 增加移动速度和闪避
_MB_ATHLETICS = [
    _hm("mb_at_01", "跑动·初级", 0, 0, 0.05, 0, 3, 0.02, "增加移动能力", 80),
    _hm("mb_at_02", "跑动·中级", 1, 0, 0.06, 0, 7, 0.03, "更灵活的移动", 160),
    _hm("mb_at_03", "跑动·高级", 2, 1, 0.08, 3, 14, 0.04, "如风般迅捷", 320),
    _hm("mb_at_04", "跑动·大师", 3, 1, 0.10, 5, 25, 0.05, "闪避能力大增", 640),
    _hm("mb_at_05", "跑动·宗师", 4, 2, 0.15, 8, 45, 0.08, "来去如风", 1280),
]

# ── 骑术技能树 (Riding) ───────────────────────────────────
# 增加骑乘战斗能力
_MB_RIDING = [
    _hm("mb_rd_01", "骑术·初级", 0, 0, 0.05, 3, 2, 0.02, "基础骑乘能力", 80),
    _hm("mb_rd_02", "骑术·中级", 1, 0, 0.06, 7, 5, 0.03, "骑乘战斗技巧", 160),
    _hm("mb_rd_03", "骑术·高级", 2, 1, 0.08, 14, 10, 0.04, "骑兵战术", 320),
    _hm("mb_rd_04", "骑术·大师", 3, 1, 0.10, 25, 18, 0.05, "人马合一", 640),
    _hm("mb_rd_05", "骑术·宗师", 4, 2, 0.15, 45, 32, 0.08, "铁蹄如雷", 1280),
]

# ── 武器大师技能树 (Weapon Master) ────────────────────────
# 加快技能熟练度获取
_MB_WEAPON_MASTER = [
    _hm("mb_wm_01", "武器大师·初级", 0, 0, 0.12, 2, 2, 0.02, "加快武器熟练", 100),
    _hm("mb_wm_02", "武器大师·中级", 1, 0, 0.16, 4, 4, 0.03, "更快的熟练", 200),
    _hm("mb_wm_03", "武器大师·高级", 2, 1, 0.20, 7, 7, 0.04, "武器精通", 400),
    _hm("mb_wm_04", "武器大师·大师", 3, 1, 0.25, 12, 12, 0.05, "武器大师", 800),
    _hm("mb_wm_05", "武器大师·宗师", 4, 2, 0.35, 20, 20, 0.08, "全能武器大师", 1600),
]

# ── 教练技能树 (Trainer) ──────────────────────────────────
# 加快声望获取
_MB_TRAINER = [
    _hm("mb_tr_01", "教练·初级", 0, 0, 0.05, 1, 1, 0.08, "基础训练能力", 80),
    _hm("mb_tr_02", "教练·中级", 1, 0, 0.06, 2, 2, 0.12, "更有效的训练", 160),
    _hm("mb_tr_03", "教练·高级", 2, 1, 0.08, 4, 4, 0.18, "教练大师", 320),
    _hm("mb_tr_04", "教练·大师", 3, 1, 0.10, 7, 7, 0.25, "训练专家", 640),
    _hm("mb_tr_05", "教练·宗师", 4, 2, 0.15, 12, 12, 0.35, "传奇教官", 1280),
]

# ── 掠夺技能树 (Looting) ──────────────────────────────────
# 增加战利品获取
_MB_LOOTING = [
    _hm("mb_lt_01", "掠夺·初级", 0, 0, 0.05, 2, 0, 0.02, "战场掠夺技巧", 80),
    _hm("mb_lt_02", "掠夺·中级", 1, 0, 0.06, 5, 0, 0.03, "更多战利品", 160),
    _hm("mb_lt_03", "掠夺·高级", 2, 1, 0.08, 10, 0, 0.04, "掠夺专家", 320),
    _hm("mb_lt_04", "掠夺·大师", 3, 1, 0.10, 18, 0, 0.05, "战场收割者", 640),
    _hm("mb_lt_05", "掠夺·宗师", 4, 2, 0.15, 30, 0, 0.08, "掠夺之王", 1280),
]

# ── 手术技能树 (Surgery) ─────────────────────────────────
# 战斗中更好的治疗效果
_MB_SURGERY = [
    _hm("mb_su_01", "手术·初级", 0, 0, 0.05, 0, 0, 0.02, "战场急救技术", 80),
    _hm("mb_su_02", "手术·中级", 1, 0, 0.06, 0, 0, 0.03, "更有效的治疗", 160),
    _hm("mb_su_03", "手术·高级", 2, 1, 0.08, 0, 0, 0.04, "救命神医", 320),
    _hm("mb_su_04", "手术·大师", 3, 1, 0.10, 0, 0, 0.05, "起死回生", 640),
    _hm("mb_su_05", "手术·宗师", 4, 2, 0.15, 0, 0, 0.08, "医圣再世", 1280),
]

# ── 急救技能树 (First Aid) ────────────────────────────────
# 快速恢复生命
_MB_FIRST_AID = [
    _hm("mb_fa_01", "急救·初级", 0, 0, 0.05, 0, 0, 0.02, "基础急救", 80),
    _hm("mb_fa_02", "急救·中级", 1, 0, 0.06, 0, 0, 0.03, "更快的恢复", 160),
    _hm("mb_fa_03", "急救·高级", 2, 1, 0.08, 0, 0, 0.04, "战场医疗兵", 320),
    _hm("mb_fa_04", "急救·大师", 3, 1, 0.10, 0, 0, 0.05, "战地医生", 640),
    _hm("mb_fa_05", "急救·宗师", 4, 2, 0.15, 0, 0, 0.08, "生命守护者", 1280),
]

# ── 统治术技能树 (Leadership) ────────────────────────────
# 增加队伍规模和士气
_MB_LEADERSHIP = [
    _hm("mb_ld_01", "统治术·初级", 0, 0, 0.05, 3, 3, 0.03, "基础领导力", 80),
    _hm("mb_ld_02", "统治术·中级", 1, 0, 0.06, 7, 7, 0.04, "队伍管理能力", 160),
    _hm("mb_ld_03", "统治术·高级", 2, 1, 0.08, 14, 14, 0.05, "将领之才", 320),
    _hm("mb_ld_04", "统治术·大师", 3, 1, 0.10, 25, 25, 0.06, "统帅之才", 640),
    _hm("mb_ld_05", "统治术·宗师", 4, 2, 0.15, 45, 45, 0.08, "王者风范", 1280),
]

# ── 战术技能树 (Tactics) ─────────────────────────────────
# 战斗阵型和策略
_MB_TACTICS = [
    _hm("mb_tc_01", "战术·初级", 0, 0, 0.05, 4, 2, 0.02, "基础战术", 80),
    _hm("mb_tc_02", "战术·中级", 1, 0, 0.06, 9, 5, 0.03, "战术运用", 160),
    _hm("mb_tc_03", "战术·高级", 2, 1, 0.08, 18, 10, 0.04, "战术大师", 320),
    _hm("mb_tc_04", "战术·大师", 3, 1, 0.10, 32, 18, 0.05, "运筹帷幄", 640),
    _hm("mb_tc_05", "战术·宗师", 4, 2, 0.15, 55, 32, 0.08, "兵法大家", 1280),
]

# ── 交易技能树 (Trade) ───────────────────────────────────
# 更好的交易价格
_MB_TRADE = [
    _hm("mb_td_01", "交易·初级", 0, 0, 0.05, 1, 1, 0.02, "基础交易技巧", 80),
    _hm("mb_td_02", "交易·中级", 1, 0, 0.06, 2, 2, 0.03, "砍价高手", 160),
    _hm("mb_td_03", "交易·高级", 2, 1, 0.08, 4, 4, 0.04, "商业头脑", 320),
    _hm("mb_td_04", "交易·大师", 3, 1, 0.10, 7, 7, 0.05, "商业大亨", 640),
    _hm("mb_td_05", "交易·宗师", 4, 2, 0.15, 12, 12, 0.08, "富甲一方", 1280),
]

# ── 说服技能树 (Persuasion) ───────────────────────────────
# 更容易说服别人
_MB_PERSUASION = [
    _hm("mb_psn_01", "说服·初级", 0, 0, 0.05, 1, 1, 0.02, "基础口才", 80),
    _hm("mb_psn_02", "说服·中级", 1, 0, 0.06, 2, 2, 0.03, "能言善道", 160),
    _hm("mb_psn_03", "说服·高级", 2, 1, 0.08, 4, 4, 0.04, "辩才无碍", 320),
    _hm("mb_psn_04", "说服·大师", 3, 1, 0.10, 7, 7, 0.05, "舌战群儒", 640),
    _hm("mb_psn_05", "说服·宗师", 4, 2, 0.15, 12, 12, 0.08, "一言之辩", 1280),
]

# ── 锻造技能树 (Smithing) ─────────────────────────────────
# 武器制作和维护
_MB_SMITHING = [
    _hm("mb_sm_01", "锻造·初级", 0, 0, 0.05, 2, 3, 0.02, "基础锻造", 80),
    _hm("mb_sm_02", "锻造·中级", 1, 0, 0.06, 5, 7, 0.03, "武器维护", 160),
    _hm("mb_sm_03", "锻造·高级", 2, 1, 0.08, 10, 14, 0.04, "锻造大师", 320),
    _hm("mb_sm_04", "锻造·大师", 3, 1, 0.10, 18, 25, 0.05, "神兵利器", 640),
    _hm("mb_sm_05", "锻造·宗师", 4, 2, 0.15, 32, 45, 0.08, "铸剑宗师", 1280),
]

# ── 工程学技能树 (Engineering) ────────────────────────────
# 建造攻城器械
_MB_ENGINEERING = [
    _hm("mb_eg_01", "工程学·初级", 0, 0, 0.05, 2, 2, 0.02, "基础工程", 80),
    _hm("mb_eg_02", "工程学·中级", 1, 0, 0.06, 5, 5, 0.03, "攻城器械", 160),
    _hm("mb_eg_03", "工程学·高级", 2, 1, 0.08, 10, 10, 0.04, "工程专家", 320),
    _hm("mb_eg_04", "工程学·大师", 3, 1, 0.10, 18, 18, 0.05, "攻城大师", 640),
    _hm("mb_eg_05", "工程学·宗师", 4, 2, 0.15, 32, 32, 0.08, "工程宗师", 1280),
]


# ══════════════════════════════════════════════════════════════
# 战斗技能 - 骑砍主动技能 (Gongfas)
# ══════════════════════════════════════════════════════════════

# ── 冲锋系 (Charge) ──────────────────────────────────────
# 高伤害冲锋攻击
_MB_CHARGE = [
    _gf("mb_gf_charge_01", "冲锋·初级", 0, 30, 0, 0, 5, "骑枪冲锋，造成大量伤害", 200, 0, 1200, 15),
    _gf("mb_gf_charge_02", "冲锋·中级", 1, 60, 0, 0, 10, "更猛烈的冲锋", 300, 0, 2000, 25),
    _gf("mb_gf_charge_03", "冲锋·高级", 2, 120, 0, 0, 15, "毁灭性冲锋", 400, 0, 3500, 40),
    _gf("mb_gf_charge_04", "冲锋·大师", 3, 200, 0, 0, 25, "如雷贯耳的冲锋", 500, 0, 5000, 60),
]

# ── 盾击系 (Shield Bash) ─────────────────────────────────
# 用盾牌击晕敌人
_MB_SHIELD_BASH_GONGFAS = [
    _gf("mb_gf_sb_01", "盾击·初级", 0, 10, 15, 0, 3, "用盾牌击晕敌人", 200, 0, 1000, 10),
    _gf("mb_gf_sb_02", "盾击·中级", 1, 20, 30, 0, 5, "更强力的盾击", 300, 0, 1800, 18),
    _gf("mb_gf_sb_03", "盾击·高级", 2, 40, 60, 0, 8, "击晕时间更长", 400, 0, 2800, 28),
    _gf("mb_gf_sb_04", "盾击·大师", 3, 70, 100, 0, 12, "破城锤般的一击", 500, 0, 4200, 42),
]

# ── 战吼系 (Battle Cry) ───────────────────────────────────
# 震慑敌人，降低防御
_MB_BATTLE_CRY = [
    _gf("mb_gf_bc_01", "战吼·初级", 0, 5, 0, 0, 8, "震慑敌人，降低其防御", 200, 0, 1100, 12),
    _gf("mb_gf_bc_02", "战吼·中级", 1, 10, 0, 0, 15, "更有效的震慑", 300, 0, 1900, 20),
    _gf("mb_gf_bc_03", "战吼·高级", 2, 20, 0, 0, 25, "敌人闻风丧胆", 400, 0, 3000, 32),
    _gf("mb_gf_bc_04", "战吼·大师", 3, 35, 0, 0, 40, "战神咆哮", 500, 0, 4500, 48),
]

# ── 狂暴系 (Berserk) ──────────────────────────────────────
# 以血换伤，大幅提升攻击
_MB_BERSERK = [
    _gf("mb_gf_bk_01", "狂暴·初级", 0, 25, -10, 0, 5, "以伤换伤，大幅提升攻击", 250, 0, 1300, 15),
    _gf("mb_gf_bk_02", "狂暴·中级", 1, 50, -20, 0, 10, "更加狂暴", 350, 0, 2200, 28),
    _gf("mb_gf_bk_03", "狂暴·高级", 2, 100, -40, 0, 15, "狂战士之怒", 450, 0, 3600, 45),
    _gf("mb_gf_bk_04", "狂暴·大师", 3, 180, -70, 0, 25, "化身狂神", 550, 0, 5400, 65),
]

# ── 虚晃系 (Feint) ────────────────────────────────────────
# 虚实结合，闪避攻击
_MB_FEINT = [
    _gf("mb_gf_ft_01", "虚晃·初级", 0, 0, 20, 0, 8, "虚实结合，闪避敌人攻击", 200, 0, 1100, 10),
    _gf("mb_gf_ft_02", "虚晃·中级", 1, 0, 40, 0, 15, "更精妙的虚晃", 300, 0, 1900, 18),
    _gf("mb_gf_ft_03", "虚晃·高级", 2, 0, 80, 0, 25, "神出鬼没", 400, 0, 3000, 28),
    _gf("mb_gf_ft_04", "虚晃·大师", 3, 0, 140, 0, 40, "幻影般的技巧", 500, 0, 4500, 42),
]

# ── 格挡反击系 (Block & Counter) ──────────────────────────
# 完美格挡并反击
_MB_BLOCK_COUNTER = [
    _gf("mb_gf_bc_01", "格挡反击·初级", 0, 15, 25, 0, 5, "格挡后反击", 200, 0, 1200, 12),
    _gf("mb_gf_bc_02", "格挡反击·中级", 1, 30, 50, 0, 10, "更有效的反击", 300, 0, 2000, 22),
    _gf("mb_gf_bc_03", "格挡反击·高级", 2, 60, 100, 0, 15, "完美格挡", 400, 0, 3200, 35),
    _gf("mb_gf_bc_04", "格挡反击·大师", 3, 100, 180, 0, 25, "无懈可击", 500, 0, 4800, 52),
]

# ── 破盾击系 (Pierce Shield) ──────────────────────────────
# 针对盾牌使用者的攻击
_MB_PIERCE_SHIELD = [
    _gf("mb_gf_ps_01", "破盾击·初级", 0, 20, 0, 0, 5, "针对盾牌的攻击", 200, 0, 1100, 12),
    _gf("mb_gf_ps_02", "破盾击·中级", 1, 40, 0, 0, 10, "更容易破防", 300, 0, 1900, 20),
    _gf("mb_gf_ps_03", "破盾击·高级", 2, 80, 0, 0, 15, "破盾专家", 400, 0, 3000, 32),
    _gf("mb_gf_ps_04", "破盾击·大师", 3, 140, 0, 0, 25, "无盾能挡", 500, 0, 4500, 48),
]

# ── 弓弩系 (Bow & Crossbow) ───────────────────────────────
# 远程攻击技能
_MB_BOW = [
    _gf("mb_gf_bow_01", "精准射击·初级", 0, 25, 0, 0, 8, "精准的远程攻击", 200, 0, 1000, 10),
    _gf("mb_gf_bow_02", "精准射击·中级", 1, 50, 0, 0, 15, "更远的射程", 300, 0, 1800, 18),
    _gf("mb_gf_bow_03", "精准射击·高级", 2, 100, 0, 0, 25, "箭无虚发", 400, 0, 2800, 28),
    _gf("mb_gf_bow_04", "精准射击·大师", 3, 180, 0, 0, 40, "神射手", 500, 0, 4200, 42),
]

# ── 投掷系 (Throwing) ─────────────────────────────────────
# 投掷武器攻击
_MB_THROWING = [
    _gf("mb_gf_th_01", "投掷·初级", 0, 18, 0, 0, 10, "投掷武器攻击", 200, 0, 900, 8),
    _gf("mb_gf_th_02", "投掷·中级", 1, 35, 0, 0, 18, "更远的投掷", 300, 0, 1600, 14),
    _gf("mb_gf_th_03", "投掷·高级", 2, 70, 0, 0, 28, "致命投掷", 400, 0, 2600, 22),
    _gf("mb_gf_th_04", "投掷·大师", 3, 120, 0, 0, 45, "百步穿杨", 500, 0, 3900, 35),
]

# ── 连击系 (Combo) ────────────────────────────────────────
# 连续攻击
_MB_COMBO = [
    _gf("mb_gf_combo_01", "连击·初级", 0, 15, 0, 0, 8, "连续攻击两次", 250, 0, 1300, 15),
    _gf("mb_gf_combo_02", "连击·中级", 1, 30, 0, 0, 15, "连续攻击三次", 350, 0, 2200, 28),
    _gf("mb_gf_combo_03", "连击·高级", 2, 60, 0, 0, 25, "连续攻击四次", 450, 0, 3500, 45),
    _gf("mb_gf_combo_04", "连击·大师", 3, 100, 0, 0, 40, "风暴般的连击", 550, 0, 5200, 65),
]

# ── 恢复系 (Recovery) ─────────────────────────────────────
# 战斗中恢复生命和体力
_MB_RECOVERY = [
    _gf("mb_gf_rec_01", "战场恢复·初级", 0, 0, 0, 30, 10, "战斗中恢复生命", 200, 0, 1000, 8),
    _gf("mb_gf_rec_02", "战场恢复·中级", 1, 0, 0, 60, 20, "更快的恢复", 300, 0, 1800, 15),
    _gf("mb_gf_rec_03", "战场恢复·高级", 2, 0, 0, 120, 35, "恢复专家", 400, 0, 2800, 25),
    _gf("mb_gf_rec_04", "战场恢复·大师", 3, 0, 0, 200, 55, "自愈能力", 500, 0, 4200, 40),
]


def register_mb_skills():
    """注册所有骑砍技能到游戏系统。"""
    
    # 注册被动技能
    heart_method_lists = [
        _MB_POWER_STRIKE, _MB_IRON_FIST, _MB_SHIELD_BASH, _MB_ATHLETICS,
        _MB_RIDING, _MB_WEAPON_MASTER, _MB_TRAINER, _MB_LOOTING,
        _MB_SURGERY, _MB_FIRST_AID, _MB_LEADERSHIP, _MB_TACTICS,
        _MB_TRADE, _MB_PERSUASION, _MB_SMITHING, _MB_ENGINEERING,
    ]
    
    for hm_list in heart_method_lists:
        for hm in hm_list:
            HEART_METHOD_REGISTRY[hm.method_id] = hm
    
    # 注册战斗技能
    gongfa_lists = [
        _MB_CHARGE, _MB_SHIELD_BASH_GONGFAS, _MB_BATTLE_CRY, _MB_BERSERK,
        _MB_FEINT, _MB_BLOCK_COUNTER, _MB_PIERCE_SHIELD, _MB_BOW,
        _MB_THROWING, _MB_COMBO, _MB_RECOVERY,
    ]
    
    for gf_list in gongfa_lists:
        for gf in gf_list:
            GONGFA_REGISTRY[gf.gongfa_id] = gf
    
    return {
        "heart_methods": sum(len(lst) for lst in heart_method_lists),
        "gongfas": sum(len(lst) for lst in gongfa_lists),
    }


# ══════════════════════════════════════════════════════════════
# 技能效果计算函数
# ══════════════════════════════════════════════════════════════

def get_mb_skill_bonus(skill_id: str, mastery: int, realm: int = 0) -> dict:
    """获取骑砍技能的加成。
    
    Returns:
        {
            "attack_bonus": int,
            "defense_bonus": int,
            "hp_regen": int,
            "lingqi_regen": int,
            "exp_multiplier": float,
            "dao_yun_rate": float,
        }
    """
    from .constants import get_heart_method_bonus, get_gongfa_bonus
    
    # 被动技能加成
    hm_bonus = get_heart_method_bonus(skill_id, mastery)
    
    # 战斗技能加成
    gf_bonus = get_gongfa_bonus(skill_id, mastery, realm)
    
    return {
        "attack_bonus": hm_bonus.get("attack_bonus", 0) + gf_bonus.get("attack_bonus", 0),
        "defense_bonus": hm_bonus.get("defense_bonus", 0) + gf_bonus.get("defense_bonus", 0),
        "hp_regen": gf_bonus.get("hp_regen", 0),
        "lingqi_regen": gf_bonus.get("lingqi_regen", 0),
        "exp_multiplier": hm_bonus.get("exp_multiplier", 0.0),
        "dao_yun_rate": hm_bonus.get("dao_yun_rate", 0.0),
    }


def get_skill_tree_bonus(player, skill_prefix: str) -> dict:
    """获取同系技能的总加成（如强击系的所有加成）。
    
    Args:
        player: Player object
        skill_prefix: 技能前缀，如 "mb_ps" 表示强击系
    
    Returns:
        总加成的 dict
    """
    total = {
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hp_regen": 0,
        "lingqi_regen": 0,
        "exp_multiplier": 0.0,
        "dao_yun_rate": 0.0,
    }
    
    # 检查玩家当前装备的被动技能
    if player.heart_method and player.heart_method.startswith(skill_prefix):
        bonus = get_mb_skill_bonus(player.heart_method, player.heart_method_mastery)
        for k, v in bonus.items():
            total[k] += v
    
    # 检查装备的战斗技能
    for slot in ["gongfa_1", "gongfa_2", "gongfa_3"]:
        gf_id = getattr(player, slot, None)
        if gf_id and gf_id.startswith(skill_prefix):
            mastery = getattr(player, f"{slot}_mastery", 0)
            bonus = get_mb_skill_bonus(gf_id, mastery)
            for k, v in bonus.items():
                total[k] += v
    
    return total


# ══════════════════════════════════════════════════════════════
# 技能树说明
# ══════════════════════════════════════════════════════════════

MB_SKILL_TREES = {
    "power_strike": {
        "name": "强击",
        "name_en": "Power Strike",
        "desc": "增加近战武器伤害",
        "skills": [h.method_id for h in _MB_POWER_STRIKE],
        "stat": "attack",
    },
    "iron_fist": {
        "name": "铁骨",
        "name_en": "Iron Fist",
        "desc": "增加生命值上限",
        "skills": [h.method_id for h in _MB_IRON_FIST],
        "stat": "hp",
    },
    "shield_bash": {
        "name": "盾击",
        "name_en": "Shield Bash",
        "desc": "盾牌攻击和防御",
        "skills": [h.method_id for h in _MB_SHIELD_BASH],
        "stat": "defense",
    },
    "athletics": {
        "name": "跑动",
        "name_en": "Athletics",
        "desc": "增加移动和闪避",
        "skills": [h.method_id for h in _MB_ATHLETICS],
        "stat": "defense",
    },
    "riding": {
        "name": "骑术",
        "name_en": "Riding",
        "desc": "骑乘战斗能力",
        "skills": [h.method_id for h in _MB_RIDING],
        "stat": "attack",
    },
    "weapon_master": {
        "name": "武器大师",
        "name_en": "Weapon Master",
        "desc": "加快技能熟练度",
        "skills": [h.method_id for h in _MB_WEAPON_MASTER],
        "stat": "exp",
    },
    "trainer": {
        "name": "教练",
        "name_en": "Trainer",
        "desc": "加快声望获取",
        "skills": [h.method_id for h in _MB_TRAINER],
        "stat": "dao_yun",
    },
    "looting": {
        "name": "掠夺",
        "name_en": "Looting",
        "desc": "增加战利品",
        "skills": [h.method_id for h in _MB_LOOTING],
        "stat": "gold",
    },
    "surgery": {
        "name": "手术",
        "name_en": "Surgery",
        "desc": "更好的治疗效果",
        "skills": [h.method_id for h in _MB_SURGERY],
        "stat": "hp_regen",
    },
    "first_aid": {
        "name": "急救",
        "name_en": "First Aid",
        "desc": "快速恢复生命",
        "skills": [h.method_id for h in _MB_FIRST_AID],
        "stat": "hp_regen",
    },
    "leadership": {
        "name": "统治术",
        "name_en": "Leadership",
        "desc": "增加队伍和防御",
        "skills": [h.method_id for h in _MB_LEADERSHIP],
        "stat": "defense",
    },
    "tactics": {
        "name": "战术",
        "name_en": "Tactics",
        "desc": "战斗阵型和策略",
        "skills": [h.method_id for h in _MB_TACTICS],
        "stat": "attack",
    },
    "trade": {
        "name": "交易",
        "name_en": "Trade",
        "desc": "更好的交易价格",
        "skills": [h.method_id for h in _MB_TRADE],
        "stat": "gold",
    },
    "persuasion": {
        "name": "说服",
        "name_en": "Persuasion",
        "desc": "更容易说服别人",
        "skills": [h.method_id for h in _MB_PERSUASION],
        "stat": "social",
    },
    "smithing": {
        "name": "锻造",
        "name_en": "Smithing",
        "desc": "武器制作和维护",
        "skills": [h.method_id for h in _MB_SMITHING],
        "stat": "attack",
    },
    "engineering": {
        "name": "工程学",
        "name_en": "Engineering",
        "desc": "建造攻城器械",
        "skills": [h.method_id for h in _MB_ENGINEERING],
        "stat": "special",
    },
}


def get_skill_tree_info(tree_id: str) -> dict | None:
    """获取技能树信息。"""
    return MB_SKILL_TREES.get(tree_id)


def get_all_skill_trees() -> dict:
    """获取所有技能树信息。"""
    return MB_SKILL_TREES


# 自动注册
register_mb_skills()
