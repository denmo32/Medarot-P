"""ゲーム全体で共通の定数・データ型定義"""

class TeamType:
    PLAYER = "player"
    ENEMY = "enemy"

class PartType:
    HEAD = "head"
    RIGHT_ARM = "right_arm"
    LEFT_ARM = "left_arm"
    LEGS = "legs"

class AttributeType:
    SPEED = "speed"
    POWER = "power"
    TECHNIQUE = "technique"
    UNDEFINED = "undefined"

class TraitType:
    # 射撃系
    RIFLE = "ライフル"
    GATLING = "ガトリング"
    # 格闘系
    SWORD = "ソード"
    HAMMER = "ハンマー"
    THUNDER = "サンダー"

    MELEE_TRAITS = [SWORD, HAMMER, THUNDER]
    SHOOTING_TRAITS = [RIFLE, GATLING]

class SkillType:
    """行動区分（スキルタイプ）"""
    SHOOT = "shoot"           # 撃つ
    STRIKE = "strike"         # 殴る
    AIMED_SHOT = "aimed_shot" # 狙い撃ち
    RECKLESS = "reckless"     # 我武者羅

class ActionType:
    ATTACK = "attack"
    SKIP = "skip"

class GaugeStatus:
    CHARGING = "charging" # 充填
    EXECUTING = "executing"
    COOLDOWN = "cooldown" # 冷却
    ACTION_CHOICE = "action_choice"
