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
    contact_time: float = 0.45  # 接近完了・接触時刻
    pass_start: float = 0.85    # 静止終了・すり抜け開始時刻
    exit_time: float = 1.25     # 画面外退出完了時刻

    @property
    def max_time(self) -> float:
        return self.exit_time

    def evaluate(self, elapsed: float) -> Tuple[bool, Optional[ActorMotionModel]]:
        if elapsed < self.start:
            return True, None

        # 1. 加速しながら接近 (Ease-In)
        if elapsed < self.contact_time:
            dur = max(0.001, self.contact_time - self.start)
            raw_p = (elapsed - self.start) / dur
            p = raw_p * raw_p  # 加速して飛び込む
            return True, ActorMotionModel(phase="approach", progress=min(1.0, max(0.0, p)))

        # 2. 接触地点で完全静止（衝撃波描画中）
        if elapsed < self.pass_start:
            return True, ActorMotionModel(phase="approach", progress=1.0)

        # 3. 再度加速しながら画面外へ (Ease-In)
        if elapsed < self.exit_time:
            dur = max(0.001, self.exit_time - self.pass_start)
            raw_p = (elapsed - self.pass_start) / dur
            p = raw_p * raw_p  # 停止状態からグンと加速して突き抜ける
            return True, ActorMotionModel(phase="pass_through", progress=min(1.0, max(0.0, p)))

        # 画面外へ退出後
        return False, None


@dataclass(frozen=True)
class CameraTrack:
    """カメラ追従演出のトラック（射撃時のスクロール）"""
    start: float  # 追従開始時刻（弾丸が画面中央に達する時刻）
    end: float    # 追従完了時刻（標的が定位置に達する時刻）

    @property
    def max_time(self) -> float:
        return self.end

    def evaluate(self, elapsed: float) -> float:
        """経過時間からカメラ進行度 (0.0: 攻撃側注視 〜 1.0: 防御側注視) を算出"""
        if elapsed <= self.start:
            return 0.0
        if elapsed >= self.end:
            return 1.0
        dur = max(0.001, self.end - self.start)
        t = (elapsed - self.start) / dur
        return t * t * (3.0 - 2.0 * t)  # Smoothstep による滑らかな加減速


@dataclass(frozen=True)
class CutinProfile:
    """1つの演出シーケンスを定義するプロファイル"""
    projectiles: Tuple[ProjectileTrack, ...] = ()
    impacts: Tuple[ImpactTrack, ...] = ()
    popup: PopupTrack = PopupTrack(start=1.0)
    actor_movement: Optional[ActorMovementTrack] = None
    camera_track: Optional[CameraTrack] = None
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
        if self.camera_track is not None:
            times.append(self.camera_track.max_time)
        return max(times) + self.extra_duration


# ==============================================================================
# 共通テンプレートビルダー（射撃 / 格闘）
# ==============================================================================

def build_shooting_profile(projectile_kind: str = "bullet", impact_kind: Optional[str] = None) -> CutinProfile:
    """射撃系統の共通演出プロファイルを生成する。
    弾丸が画面中央に到達するとカメラが弾を追いかけ、攻撃側退場・防御側登場を行う。
    """
    resolved_impact = impact_kind or ("explosion" if projectile_kind == "missile" else "hit")
    proj_start = 0.15
    proj_end = 0.85
    impact_start = 0.85
    impact_end = 1.10
    popup_start = 1.10

    flight_dur = proj_end - proj_start
    cam_start = proj_start + flight_dur * 0.25  # 0.325s (中央到達時刻)
    cam_end = proj_start + flight_dur * 0.75    # 0.675s (防御側定位置到達時刻)

    return CutinProfile(
        projectiles=(
            ProjectileTrack(start=proj_start, end=proj_end, kind=projectile_kind),
        ),
        impacts=(
            ImpactTrack(start=impact_start, end=impact_end, kind=resolved_impact),
        ),
        popup=PopupTrack(start=popup_start, miss_start=impact_start),
        camera_track=CameraTrack(start=cam_start, end=cam_end),
        extra_duration=0.15,
    )


def build_melee_profile(impact_kind: str = "hit") -> CutinProfile:
    """格闘系統の共通演出プロファイルを生成する。
    衝撃波の種類のみが可変で、タイムライン構造は共通。
    """
    return CutinProfile(
        actor_movement=ActorMovementTrack(
            start=0.0,
            contact_time=0.45,
            pass_start=0.85,
            exit_time=1.25,
        ),
        impacts=(
            ImpactTrack(start=0.45, end=0.85, kind=impact_kind),
        ),
        popup=PopupTrack(start=0.85, miss_start=0.85),
        extra_duration=0.2,
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