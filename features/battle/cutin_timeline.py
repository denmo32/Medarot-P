"""カットイン演出のタイムライン管理・データ駆動エフェクトプロファイル。

カットイン演出を「時間軸に沿ったトラックの集合」として定義・管理する。
スキルや行動形式ごとの演出パラメータ、順序、タイミングをデータとして集約し、
ViewBuilder や Renderer にロジックが肥大化・散乱するのを防ぐ。
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from domain.constants import ActionCategory, SkillType
from domain.models import ActionResult
from features.battle.constants import CutinStep
from features.battle.view_models import (
    ActorMotionModel,
    CutinPopupModel,
    ImpactEffectModel,
    ProjectileEffectModel,
)


@dataclass(frozen=True)
class ProjectileTrack:
    """飛翔体（弾丸・ミサイル等）の演出トラック"""
    start: float
    end: float
    kind: str = "bullet"
    miss_end: Optional[float] = None
    pass_through_factor: float = 1.6  # ミス時に画面外まで通り抜ける移動倍率

    @property
    def max_time(self) -> float:
        if self.miss_end is not None:
            return max(self.end, self.miss_end)
        return max(self.end, self.start + (self.end - self.start) * self.pass_through_factor)

    def evaluate(self, elapsed: float, is_hit: bool = True) -> Optional[ProjectileEffectModel]:
        effective_end = self.end if is_hit else (
            self.miss_end if self.miss_end is not None else self.start + (self.end - self.start) * self.pass_through_factor
        )
        if self.start <= elapsed < effective_end:
            dur = max(0.001, self.end - self.start)
            progress = max(0.0, (elapsed - self.start) / dur)
            if is_hit:
                progress = min(1.0, progress)
            return ProjectileEffectModel(progress=progress, kind=self.kind, is_hit=is_hit)
        return None


@dataclass(frozen=True)
class ImpactTrack:
    """着弾・爆発・打撃等の衝撃演出トラック"""
    start: float
    end: float
    kind: str = "hit"
    only_on_hit: bool = True  # 命中時のみ再生（ミス時は非表示）

    @property
    def max_time(self) -> float:
        return self.end

    def evaluate(self, elapsed: float, is_hit: bool) -> Optional[ImpactEffectModel]:
        if self.only_on_hit and not is_hit:
            return None
        if self.start <= elapsed < self.end:
            dur = max(0.001, self.end - self.start)
            progress = max(0.0, min(1.0, (elapsed - self.start) / dur))
            return ImpactEffectModel(progress=progress, kind=self.kind)
        return None


@dataclass(frozen=True)
class PopupTrack:
    """ポップアップ表示の演出トラック"""
    start: float
    miss_start: Optional[float] = None

    def is_active(self, elapsed: float, is_hit: bool = True) -> bool:
        start_time = self.start if is_hit else (self.miss_start if self.miss_start is not None else self.start)
        return elapsed >= start_time


@dataclass(frozen=True)
class ActorMovementTrack:
    """攻撃機体の移動演出トラック（格闘突進・すり抜け退出など）"""
    start: float = 0.0
    contact_time: float = 0.30
    pass_start: float = 0.35
    exit_time: float = 0.65

    @property
    def max_time(self) -> float:
        return self.exit_time

    def evaluate(self, elapsed: float) -> Tuple[bool, Optional[ActorMotionModel]]:
        if elapsed < self.start:
            return True, None

        if elapsed < self.contact_time:
            dur = max(0.001, self.contact_time - self.start)
            raw_p = (elapsed - self.start) / dur
            # Ease-in: 加速しながら接近
            p = raw_p * raw_p
            return True, ActorMotionModel(phase="approach", progress=min(1.0, max(0.0, p)))

        if elapsed < self.pass_start:
            # 接触・インパクト維持
            return True, ActorMotionModel(phase="approach", progress=1.0)

        if elapsed < self.exit_time:
            # 相手の背面を突き抜けて画面外へ駆け抜ける
            dur = max(0.001, self.exit_time - self.pass_start)
            raw_p = (elapsed - self.pass_start) / dur
            return True, ActorMotionModel(phase="pass_through", progress=min(1.0, max(0.0, raw_p)))

        # 画面外退出後
        return False, None


@dataclass(frozen=True)
class CutinProfile:
    """1つの演出シーケンスを定義するプロファイル"""
    projectiles: Tuple[ProjectileTrack, ...] = ()
    impacts: Tuple[ImpactTrack, ...] = ()
    popup: PopupTrack = PopupTrack(start=1.0)
    actor_movement: Optional[ActorMovementTrack] = None
    extra_duration: float = 0.1  # エフェクト終了後の余白バッファ

    @property
    def duration(self) -> float:
        """全トラックの終了時刻からプロファイル全体の再生時間を自動算出"""
        times = [0.4]  # 最低保証時間
        for p in self.projectiles:
            times.append(p.max_time)
        for i in self.impacts:
            times.append(i.max_time)
        if self.actor_movement is not None:
            times.append(self.actor_movement.max_time)
        return max(times) + self.extra_duration


# ==============================================================================
# 演出プロファイル カタログ（データ駆動定義）
# ==============================================================================

# 通常射撃（ライフル等）: 弾丸(0.0~0.6s) -> 着弾火花(0.6~0.85s) -> ポップアップ(0.85s~)
SHOOTING_BULLET_PROFILE = CutinProfile(
    projectiles=(ProjectileTrack(start=0.0, end=0.6, kind="bullet"),),
    impacts=(ImpactTrack(start=0.6, end=0.85, kind="hit"),),
    popup=PopupTrack(start=0.85, miss_start=0.6),
)

# ミサイル: ミサイル飛翔(0.0~0.7s) -> 爆発(0.7~1.1s) -> ポップアップ(1.1s~)
MISSILE_PROFILE = CutinProfile(
    projectiles=(ProjectileTrack(start=0.0, end=0.7, kind="missile"),),
    impacts=(ImpactTrack(start=0.7, end=1.1, kind="explosion"),),
    popup=PopupTrack(start=1.1, miss_start=0.7),
)

# ガトリング: 高速連射(0.0~0.4s) -> 連射着弾(0.4~0.75s) -> ポップアップ(0.75s~)
GATLING_PROFILE = CutinProfile(
    projectiles=(ProjectileTrack(start=0.0, end=0.4, kind="bullet"),),
    impacts=(ImpactTrack(start=0.4, end=0.75, kind="hit"),),
    popup=PopupTrack(start=0.75, miss_start=0.4),
)

# 格闘（殴る・ソード・ハンマー）:
# 突進接近(0.0~0.30s) -> ヒット衝撃(0.30~0.58s) -> 背面すり抜け画面外(0.35~0.65s) -> ポップアップ(0.65s~)
MELEE_DEFAULT_PROFILE = CutinProfile(
    actor_movement=ActorMovementTrack(
        start=0.0,
        contact_time=0.30,
        pass_start=0.35,
        exit_time=0.65,
    ),
    impacts=(ImpactTrack(start=0.30, end=0.58, kind="hit"),),
    popup=PopupTrack(start=0.65, miss_start=0.35),
    extra_duration=0.15,
)

# フォールバック
FALLBACK_PROFILE = CutinProfile(
    popup=PopupTrack(start=0.5),
)

# 技固有のプロファイルマッピング
SKILL_CUTIN_PROFILES: Dict[SkillType, CutinProfile] = {
    SkillType.MISSILE: MISSILE_PROFILE,
    SkillType.GATLING: GATLING_PROFILE,
}

# 行動カテゴリ単位のプロファイルマッピング
ACTION_CATEGORY_CUTIN_PROFILES: Dict[ActionCategory, CutinProfile] = {
    ActionCategory.SHOOTING: SHOOTING_BULLET_PROFILE,
    ActionCategory.MELEE: MELEE_DEFAULT_PROFILE,
}


def resolve_cutin_profile(part) -> CutinProfile:
    """パーツ情報（スキル・行動形式）から対応する演出プロファイルをテーブル引きで解決する"""
    if not part:
        return FALLBACK_PROFILE

    # 1. スキル個別定義の優先解決
    if part.skill in SKILL_CUTIN_PROFILES:
        return SKILL_CUTIN_PROFILES[part.skill]

    # 2. 行動形式カテゴリ単位の解決
    if part.action and part.action.category in ACTION_CATEGORY_CUTIN_PROFILES:
        return ACTION_CATEGORY_CUTIN_PROFILES[part.action.category]

    return FALLBACK_PROFILE


# ==============================================================================
# ポップアップ文言の定義および解決ヘルパー
# ==============================================================================

CUTIN_POPUP_LABELS = {
    "critical": "CRITICAL!!",
    "guard": "GUARD",
    "hit": "HIT!",
    "miss": "MISS!",
    "pierce": "PENETRATION",
}


def resolve_cutin_popup(result: ActionResult, step: CutinStep) -> CutinPopupModel:
    """戦闘結果と現在のステップからポップアップモデルを解決する純粋関数"""
    if step == CutinStep.PIERCE:
        pierce = result.pierce_effect
        dmg = pierce.effective_damage if pierce else 0
        return CutinPopupModel(
            primary_label=CUTIN_POPUP_LABELS["pierce"],
            damage_label=f"-{dmg}",
            is_miss=False,
        )

    if not result.success:
        return CutinPopupModel(
            primary_label="",
            damage_label=CUTIN_POPUP_LABELS["miss"],
            is_miss=True,
        )

    if result.is_critical:
        label = CUTIN_POPUP_LABELS["critical"]
    elif result.is_guarded:
        label = CUTIN_POPUP_LABELS["guard"]
    else:
        label = CUTIN_POPUP_LABELS["hit"]

    return CutinPopupModel(
        primary_label=label,
        damage_label=f"-{result.effective_damage}",
        is_miss=False,
    )