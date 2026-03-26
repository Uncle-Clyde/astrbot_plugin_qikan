# 骑砍世界 (Mount & Blade Style) Plugin Conversion

## Goal

Convert the AstrBot "修仙世界" (Cultivation World) plugin into a **Mount & Blade (骑砍/M&B)** themed game, including:
1. Complete terminology conversion (修仙→战争, 灵石→第纳尔, 宗门→家族, etc.)
2. Adding M&B-style skills (强击/铁骨/盾击/跑动/骑术等)
3. Ensuring skills display correctly in the WEB UI
4. Planning the corresponding UI design

## Instructions
- Systematically convert all files with Xianxia terminology to medieval knight/warrior style
- Create comprehensive M&B skill system with passive skills and combat skills
- Add WebSocket API endpoints for skill tree display
- Create UI design documentation for frontend implementation

## Discoveries
- Frontend is a **Vue 3 SPA** with minified/compiled JS/CSS (`index-CWSMAYrl.js`)
- No source maps or original source code available - frontend cannot be directly edited
- Skills defined in `game/constants.py` (HeartMethodDef/GongfaDef classes) and `game/mb_skills.py` (newly created)
- WebSocket handler (`web/websocket_handler.py`) manages API communication
- Existing engine methods for learning/equipping skills in `game/engine.py`
- **Pre-existing LSP errors** in engine.py (lines 1802, 1804, etc.) and other files - these existed before our edits

## Accomplished

### Terminology Conversion (Completed):
| File | Status |
|------|--------|
| `pvp.py` | ✅ Full conversion |
| `adventure.py` | ✅ Full conversion |
| `constants.py` | ✅ Major overhaul |
| `models.py` | ✅ Docstrings/comments |
| `engine.py` | ✅ Terminology conversion |
| `market.py` | ✅ Full conversion (坊市→集市) |
| `sect.py` | ✅ Full conversion (宗门→家族) |
| `renderer.py` | ✅ Display text conversion |
| `shop.py` | ✅ Full conversion (天机阁→军需商店) |
| `pills.py` | ✅ Full conversion (丹药→药剂) |
| `dungeon.py` | ✅ Full conversion (秘境→副本, 历练→征战) |
| `main.py` | ✅ Command descriptions + prompts |

### M&B Skills System (Completed):
- **Created `game/mb_skills.py`** with:
  - 16 passive skill trees (80 skills): 强击, 铁骨, 盾击, 跑动, 骑术, 武器大师, 教练, 掠夺, 手术, 急救, 统治术, 战术, 交易, 说服, 锻造, 工程学
  - 11 combat skill trees (44 skills): 冲锋, 盾击, 战吼, 狂暴, 虚晃, 格挡反击, 破盾击, 弓弩, 投掷, 连击, 战场恢复
  - Skill tree info management functions

- **Updated `game/combat.py`**:
  - Added M&B combat actions: 冲锋, 盾击, 战吼, 狂暴, 虚晃
  - Added combat states: 眩晕, 狂暴, 虚弱
  - New action costs and effects

- **Updated `web/websocket_handler.py`**:
  - Added API endpoints: `get_skill_trees`, `get_combat_skills`, `get_available_skills`, `get_skill_detail`

- **Created `SKILLS_UI_DESIGN.md`**:
  - Comprehensive UI design with layouts, tabs, modals
  - API definitions
  - Implementation checklist

- **Updated `game/__init__.py`** to auto-import skills

## Terminology Mappings Applied

| Original (Xianxia) | M&B Style |
|---------------------|-----------|
| 修仙/修炼 | 战争/训练 |
| 灵石 | 第纳尔 |
| 丹药 | 药剂 |
| 经验/修为 | 经验 |
| 境界/境界 | 爵位 |
| 突破 | 晋升 |
| 陨落 | 战死沙场 |
| 心法 | 被动技能/技能 |
| 功法 | 战斗技能/战技 |
| 道韵 | 声望 |
| 坊市 | 集市 |
| 宗门 | 家族 |
| 宗主 | 家主 |
| 弟子 | 成员 |
| 道号 | 骑士名 |
| 历练 | 征战 |
| 秘境 | 副本 |
| 天机阁 | 军需商店 |
| 心法秘籍 | 技能书 |
| 功法卷轴 | 战技卷轴 |

### Equipment Tier Names
| Original | M&B Style |
|----------|-----------|
| 凡器 | 凡品 |
| 灵器 | 良品 |
| 道器 | 精品 |
| 先天道器 | 极品 |

### Pill Tier Names
| Original | M&B Style |
|----------|-----------|
| 凡阶 | 凡品 |
| 黄阶 | 初品 |
| 玄阶 | 中品 |
| 地阶 | 高品 |
| 天阶 | 极品 |

## Relevant Files / Directories

```
L:\G\astrbot_plugin_monixiuxian-main\astrbot_plugin_monixiuxian-main\
├── game\
│   ├── __init__.py                    [MODIFIED - imports mb_skills]
│   ├── mb_skills.py                   [CREATED - M&B skill system]
│   ├── combat.py                      [MODIFIED - M&B combat actions]
│   ├── constants.py                    [MODIFIED - terminology + skill defs]
│   ├── engine.py                      [MODIFIED - terminology conversion]
│   ├── models.py                      [MODIFIED - terminology conversion]
│   ├── pvp.py                         [MODIFIED - terminology conversion]
│   ├── adventure.py                   [MODIFIED - terminology conversion]
│   ├── market.py                     [MODIFIED - terminology conversion]
│   ├── sect.py                       [MODIFIED - terminology conversion]
│   ├── pills.py                      [MODIFIED - terminology conversion]
│   ├── dungeon.py                    [MODIFIED - terminology conversion]
│   ├── renderer.py                   [MODIFIED - terminology conversion]
│   ├── shop.py                       [MODIFIED - terminology conversion]
│   ├── inventory.py                  [NOT MODIFIED]
│   ├── cultivation.py                 [NOT MODIFIED]
│   ├── auth.py                       [NOT MODIFIED]
│   └── ... (other files)
├── web\
│   ├── websocket_handler.py           [MODIFIED - new skill APIs]
│   ├── routes.py                     [NOT MODIFIED]
│   └── ...
├── static\
│   ├── index.html                   [MINIFIED - cannot edit]
│   ├── js\index-CWSMAYrl.js         [MINIFIED - cannot edit]
│   └── css\index-BJ_XiCvZ.css       [MINIFIED - cannot edit]
├── main.py                            [MODIFIED - command descriptions]
└── SKILLS_UI_DESIGN.md               [CREATED - UI design doc]
```

## Remaining Work

### Skills Implementation (Pending):
- **Frontend skills UI** - Cannot be implemented due to minified frontend code
  - Need to either: rebuild frontend from scratch, or modify existing minified JS
- Backend skill APIs are complete and functional

### Pre-existing Issues (Not Our Fault):
- LSP errors in `engine.py` (lines 1802, 1804, etc.)
- LSP errors in `pvp.py` (CombatAction undefined)
- LSP errors in `web/routes.py` (fastapi unresolved)
- LSP errors in `main.py` (astrbot.api unresolved)
- These errors existed before our changes
