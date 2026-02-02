"""
UI・演出専用の計算ロジック
"""

from typing import Any, Tuple
from domain.constants import TraitType
from .snapshot import CutinStateData
from ui.config import SCREEN_HEIGHT

class CutinAnimationLogic:
    """カットイン演出のシーケンス計算"""

    T_ENTER = 0.2
    # 格闘
    T_MELEE_DASH = 0.35
    T_MELEE_HIT = 0.55
    T_MELEE_LEAVE = 0.75
    # 射撃
    T_SHOOT_FIRE = 0.25
    T_SHOOT_SWAP_START = 0.45
    T_SHOOT_SWAP_END = 0.7
    T_SHOOT_IMPACT = 0.8

    @classmethod
    def calculate_frame(cls, progress: float, trait: str, is_enemy: bool, hit_result: Any, screen_size: Tuple[int, int]) -> CutinStateData:
        """
        指定された進行度におけるカットインの状態を計算する。
        座標はピクセルで計算して返す（レンダリング時に再変換する必要がないように）。
        """
        sw, sh = screen_size
        s = sh / SCREEN_HEIGHT
        
        cy = sh // 2 - int(20 * s) # 基準高さからの補正
        
        fade_ratio = min(1.0, progress / cls.T_ENTER)
        state = CutinStateData(
            is_active=True,
            bg_alpha=int(150 * fade_ratio),
            bar_height=int((sh // 8) * fade_ratio),
            mirror=is_enemy
        )

        if trait in TraitType.MELEE_TRAITS:
            cls._calc_melee_sequence(state, progress, sw, cy, sh)
        else:
            cls._calc_shoot_sequence(state, progress, sw, cy, hit_result, sh)

        # ポップアップ
        impact_t = cls.T_MELEE_HIT if trait in TraitType.MELEE_TRAITS else cls.T_SHOOT_IMPACT
        if progress > impact_t and hit_result:
            anim_t = min(1.0, (progress - impact_t) / (1.0 - impact_t))
            # 画面右側、中央より少し上
            px = sw - (sw * 0.18)
            py = cy - (sh * 0.1) - (sh * 0.06 * anim_t)
            state.popup = {'visible': True, 'x': px, 'y': py, 'result': hit_result}

        if is_enemy:
            cls._apply_mirroring(state, sw)

        return state

    @classmethod
    def _calc_melee_sequence(cls, state, progress, sw, cy, sh):
        # 画面幅に応じた相対的なオフセット
        l_x = sw * 0.18
        r_x = sw * 0.82
        off = sw * 0.5 
        
        atk, defn = {'y': cy, 'visible': True}, {'x': r_x, 'y': cy, 'visible': True}
        
        if progress < cls.T_ENTER:
            r = progress / cls.T_ENTER
            atk['x'], atk['y'] = l_x, (cy + off) - (off * r)
            defn['y'] = (cy - off) + (off * r)
        elif progress < cls.T_MELEE_DASH:
            atk['x'] = l_x
        elif progress < cls.T_MELEE_HIT:
            r = (progress - cls.T_MELEE_DASH) / (cls.T_MELEE_HIT - cls.T_MELEE_DASH)
            # 相手の手前まで突進
            target_x = r_x - (sw * 0.12)
            atk['x'] = l_x + (target_x - l_x) * (r * r)
        elif progress < cls.T_MELEE_LEAVE:
            atk['x'] = r_x - (sw * 0.12)
            state.effect = {'visible': True, 'x': r_x, 'y': cy, 'progress': progress, 'start_time': cls.T_MELEE_HIT}
        else:
            r = (progress - cls.T_MELEE_LEAVE) / (1.0 - cls.T_MELEE_LEAVE)
            start_x = r_x - (sw * 0.12)
            # 画面外へ突き抜ける
            atk['x'] = start_x + (sw + off - start_x) * (r * r)
            
        state.attacker, state.defender = atk, defn

    @classmethod
    def _calc_shoot_sequence(cls, state, progress, sw, cy, hit_result, sh):
        l_x = sw * 0.18
        r_x = sw * 0.82
        off = sw * 0.5
        
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

        # 弾丸
        if progress >= cls.T_SHOOT_FIRE:
            bul['visible'] = True
            mid_x = sw // 2
            bullet_offset = sw * 0.1 # 銃口や着弾のオフセット
            
            if progress < cls.T_SHOOT_SWAP_START:
                r = (progress - cls.T_SHOOT_FIRE) / (cls.T_SHOOT_SWAP_START - cls.T_SHOOT_FIRE)
                bul['x'] = (l_x + bullet_offset) + (mid_x - (l_x + bullet_offset)) * r
            elif progress < cls.T_SHOOT_SWAP_END:
                r = (progress - cls.T_SHOOT_SWAP_START) / (cls.T_SHOOT_SWAP_END - cls.T_SHOOT_SWAP_START)
                bul['x'] = mid_x + (bullet_offset * r)
            else:
                r = (progress - cls.T_SHOOT_SWAP_END) / (cls.T_SHOOT_IMPACT - cls.T_SHOOT_SWAP_END)
                start_b = mid_x + bullet_offset
                if progress <= cls.T_SHOOT_IMPACT:
                    bul['x'] = start_b + (r_x - start_b) * r
                else:
                    if hit_result and hit_result.is_hit: bul['visible'] = False
                    else:
                        r_miss = (progress - cls.T_SHOOT_IMPACT) / (1.0 - cls.T_SHOOT_IMPACT)
                        bul['x'] = r_x + (sw - r_x + bullet_offset * 2) * r_miss

        state.attacker, state.defender, state.bullet = atk, defn, bul

    @classmethod
    def _apply_mirroring(cls, state, sw):
        for d in [state.attacker, state.defender, state.bullet, state.effect, state.popup]:
            if 'x' in d: d['x'] = sw - d['x']