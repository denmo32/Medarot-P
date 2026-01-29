"""
UI・演出専用の計算ロジック
ECSの世界とは隔離され、進行度(0.0~1.0)に基づいた座標や表示状態の計算のみを行う。
"""

from typing import Dict, Any, Optional
from config import GAME_PARAMS
from domain.constants import TraitType
from .snapshot import CutinStateData

class CutinAnimationLogic:
    """カットイン演出のシーケンス計算を司る（UIレイヤー専用）"""

    # 演出タイミングの定数（秒数ではなく進行度 0.0 ~ 1.0 に対する割合）
    T_ENTER = 0.2
    # 格闘用シーケンス
    T_MELEE_DASH = 0.35
    T_MELEE_HIT = 0.55
    T_MELEE_LEAVE = 0.75
    # 射撃用シーケンス
    T_SHOOT_FIRE = 0.25
    T_SHOOT_SWAP_START = 0.45
    T_SHOOT_SWAP_END = 0.7
    T_SHOOT_IMPACT = 0.8

    @classmethod
    def calculate_frame(cls, progress: float, trait: str, is_enemy: bool, hit_result: Any) -> CutinStateData:
        """指定された進行度におけるカットインの状態を計算する"""
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        cy = sh // 2 - 20
        
        # 基本的な背景と帯のフェード
        fade_ratio = min(1.0, progress / cls.T_ENTER)
        state = CutinStateData(
            is_active=True,
            bg_alpha=int(150 * fade_ratio),
            bar_height=int((sh // 8) * fade_ratio),
            mirror=is_enemy
        )

        # 攻撃タイプ（格闘/射撃）に応じた座標計算
        if trait in TraitType.MELEE_TRAITS:
            cls._calc_melee_sequence(state, progress, sw, cy)
        else:
            cls._calc_shoot_sequence(state, progress, sw, cy, hit_result)

        # 共通：ポップアップ（ダメージ等）の判定
        impact_t = cls.T_MELEE_HIT if trait in TraitType.MELEE_TRAITS else cls.T_SHOOT_IMPACT
        if progress > impact_t and hit_result:
            anim_t = min(1.0, (progress - impact_t) / (1.0 - impact_t))
            state.popup = {'visible': True, 'x': sw - 150, 'y': cy - 60 - (40 * anim_t), 'result': hit_result}

        # 共通：敵側のアクションなら座標を反転
        if is_enemy:
            cls._apply_mirroring(state, sw)

        return state

    @classmethod
    def _calc_melee_sequence(cls, state, progress, sw, cy):
        l_x, r_x, off = 150, sw - 150, 400
        atk, defn = {'y': cy, 'visible': True}, {'x': r_x, 'y': cy, 'visible': True}
        
        if progress < cls.T_ENTER:
            r = progress / cls.T_ENTER
            atk['x'], atk['y'] = l_x, (cy + off) - (off * r)
            defn['y'] = (cy - off) + (off * r)
        elif progress < cls.T_MELEE_DASH:
            atk['x'] = l_x
        elif progress < cls.T_MELEE_HIT:
            r = (progress - cls.T_MELEE_DASH) / (cls.T_MELEE_HIT - cls.T_MELEE_DASH)
            atk['x'] = l_x + (r_x - 100 - l_x) * (r * r)
        elif progress < cls.T_MELEE_LEAVE:
            atk['x'] = r_x - 100
            state.effect = {'visible': True, 'x': r_x, 'y': cy, 'progress': progress, 'start_time': cls.T_MELEE_HIT}
        else:
            r = (progress - cls.T_MELEE_LEAVE) / (1.0 - cls.T_MELEE_LEAVE)
            atk['x'] = (r_x - 100) + (sw + off - (r_x - 100)) * (r * r)
            
        state.attacker, state.defender = atk, defn

    @classmethod
    def _calc_shoot_sequence(cls, state, progress, sw, cy, hit_result):
        l_x, r_x, off = 150, sw - 150, 400
        atk, defn = {'y': cy, 'visible': True}, {'y': cy, 'visible': True}
        bul = {'visible': False, 'x': 0, 'y': cy}

        # アタッカー退場 & ディフェンダー入場
        if progress < cls.T_SHOOT_SWAP_START:
            atk['x'] = l_x
            if progress < cls.T_ENTER:
                r = progress / cls.T_ENTER
                atk['y'], defn['x'] = (cy + off) - (off * r), sw + off
            else:
                defn['x'] = sw + off
        elif progress < cls.T_SHOOT_SWAP_END:
            r = (progress - cls.T_SHOOT_SWAP_START) / (cls.T_SHOOT_SWAP_END - cls.T_SHOOT_SWAP_START)
            atk['x'], defn['x'] = l_x - (l_x + off) * r, (sw + off) - (sw + off - r_x) * r
        else:
            atk['x'], defn['x'] = -off * 2, r_x

        # 弾丸（弾道）
        if progress >= cls.T_SHOOT_FIRE:
            bul['visible'] = True
            mid_x = sw // 2
            if progress < cls.T_SHOOT_SWAP_START:
                r = (progress - cls.T_SHOOT_FIRE) / (cls.T_SHOOT_SWAP_START - cls.T_SHOOT_FIRE)
                bul['x'] = (l_x + 80) + (mid_x - (l_x + 80)) * r
            elif progress < cls.T_SHOOT_SWAP_END:
                r = (progress - cls.T_SHOOT_SWAP_START) / (cls.T_SHOOT_SWAP_END - cls.T_SHOOT_SWAP_START)
                bul['x'] = mid_x + (50 * r)
            else:
                r = (progress - cls.T_SHOOT_SWAP_END) / (cls.T_SHOOT_IMPACT - cls.T_SHOOT_SWAP_END)
                if progress <= cls.T_SHOOT_IMPACT:
                    bul['x'] = (mid_x + 50) + (r_x - (mid_x + 50)) * r
                else:
                    if hit_result and hit_result.is_hit: bul['visible'] = False
                    else:
                        r_miss = (progress - cls.T_SHOOT_IMPACT) / (1.0 - cls.T_SHOOT_IMPACT)
                        bul['x'] = r_x + (sw - r_x + 100) * r_miss

        state.attacker, state.defender, state.bullet = atk, defn, bul

    @classmethod
    def _apply_mirroring(cls, state, sw):
        for d in [state.attacker, state.defender, state.bullet]:
            if 'x' in d: d['x'] = sw - d['x']