"""カットイン演出のタイムライン管理・データ駆動エフェクトプロファイル。

カットイン演出は大きく「射撃（SHOOTING）」と「格闘（MELEE）」の2系統に分かれ、
それぞれの時間軸・進行テンプレートは完全に共通化されています。
- 射撃系統: 飛翔体（弾丸/ミサイル等）の種別のみがスキルによって変化
- 格闘系統: 衝撃波・着弾演出（打撃/斬撃等）の種別のみがスキルによって変化
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
    pass_through_factor: float = 1.6  # ミス時に画面外まで通り抜ける倍率

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
    only_on_hit: bool = True  # 命中時のみ再生

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
    """攻撃機体の移動演出トラック（格闘突進・すり抜け退出）"""
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
            return True, ActorMotionModel(phase="approach", progress=1.0)

        if elapsed < self.exit_time:
            dur = max(0.001, self.exit_time - self.pass_start)
            raw_p = (elapsed - self.pass_start) / dur
            return True, ActorMotionModel(phase="pass_through", progress=min(1.0, max(0.0, raw_p)))

        return False, None


@dataclass(frozen=True)
class CutinProfile:
    """1つの演出シーケンスを定義するプロファイル"""
    projectiles: Tuple[ProjectileTrack, ...] = ()
    impacts: Tuple[ImpactTrack, ...] = ()
    popup: PopupTrack = PopupTrack(start=1.0)
    actor_movement: Optional[ActorMovementTrack] = None
    extra_duration: float = 0.1

    @property
    def duration(self) -> float:
        times = [0.4]
        for p in self.projectiles:
            times.append(p.max_time)
        for i in self.impacts:
            times.append(i.max_time)
        if self.actor_movement is not None:
            times.append(self.actor_movement.max_time)
        return max(times) + self.extra_duration


# ==============================================================================
# 共通テンプレートビルダー（射撃 / 格闘）
# ==============================================================================

def build_shooting_profile(projectile_kind: str = "bullet", impact_kind: Optional[str] = None) -> CutinProfile:
    """射撃系統の共通演出プロファイルを生成する。
    弾丸の種類のみが可変で、タイムライン構造は完全に共通。
    """
    resolved_impact = impact_kind or ("explosion" if projectile_kind == "missile" else "hit")
    return CutinProfile(
        projectiles=(
            ProjectileTrack(start=0.0, end=0.6, kind=projectile_kind),
        ),
        impacts=(
            ImpactTrack(start=0.6, end=0.85, kind=resolved_impact),
        ),
        popup=PopupTrack(start=0.85, miss_start=0.6),
        extra_duration=0.1,
    )


def build_melee_profile(impact_kind: str = "hit") -> CutinProfile:
    """格闘系統の共通演出プロファイルを生成する。
    衝撃波・打撃演出の種類のみが可変で、突進・すり抜けタイムラインは完全に共通。
    """
    return CutinProfile(
        actor_movement=ActorMovementTrack(
            start=0.0,
            contact_time=0.30,
            pass_start=0.35,
            exit_time=0.65,
        ),
        impacts=(
            ImpactTrack(start=0.30, end=0.58, kind=impact_kind),
        ),
        popup=PopupTrack(start=0.65, miss_start=0.35),
        extra_duration=0.15,
    )


FALLBACK_PROFILE = CutinProfile(
    popup=PopupTrack(start=0.5),
)


# ==============================================================================
# スキル別の可変要素マッピング（弾丸 / 衝撃波の種別のみを定義）
# ==============================================================================

# 射撃スキル -> 弾丸の種別（未指定はデフォルト "bullet"）
SHOOTING_PROJECTILE_KINDS: Dict[SkillType, str] = {
    SkillType.RIFLE: "bullet",
    SkillType.GATLING: "bullet",
    SkillType.MISSILE: "missile",
}

# 格闘スキル -> 衝撃波・打撃エフェクトの種別（未指定はデフォルト "hit"）
# 将来 "slash"（ソード用斬撃）や "heavy_hit"（ハンマー用衝撃波）等を追加可能
MELEE_IMPACT_KINDS: Dict[SkillType, str] = {
    SkillType.SWORD: "hit",
    SkillType.HAMMER: "hit",
}


def resolve_cutin_profile(part) -> CutinProfile:
    """パーツ情報から対応する演出プロファイルを解決する。"""
    if not part or not part.action:
        return FALLBACK_PROFILE

    category = part.action.category

    # 1. 射撃系統（弾丸のみスキル依存）
    if category == ActionCategory.SHOOTING:
        projectile_kind = SHOOTING_PROJECTILE_KINDS.get(part.skill, "bullet")
        return build_shooting_profile(projectile_kind=projectile_kind)

    # 2. 格闘系統（衝撃波のみスキル依存）
    if category == ActionCategory.MELEE:
        impact_kind = MELEE_IMPACT_KINDS.get(part.skill, "hit")
        return build_melee_profile(impact_kind=impact_kind)

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