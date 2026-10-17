"""カットイン演出のタイムライン管理・データ駆動エフェクトプロファイル。

UI や表示モデル（View Model）には依存せず、時間軸上の進行率・位置の計算のみを担います。
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from domain.constants import ActionCategory, SkillType


@dataclass(frozen=True)
class ProjectileMotion:
    """飛翔体の時間軸進行データ"""
    progress: float
    kind: str = "bullet"
    is_hit: bool = True


@dataclass(frozen=True)
class ImpactMotion:
    """衝撃エフェクトの時間軸進行データ"""
    progress: float
    kind: str = "hit"


@dataclass(frozen=True)
class ActorMotion:
    """攻撃機体の移動演出データ（接近・すり抜け）"""
    phase: str
    progress: float


@dataclass(frozen=True)
class ProjectileTrack:
    """飛翔体（弾丸・ミサイル等）の演出トラック"""
    start: float
    end: float
    kind: str = "bullet"
    miss_end: Optional[float] = None
    pass_through_factor: float = 1.6

    @property
    def max_time(self) -> float:
        if self.miss_end is not None:
            return max(self.end, self.miss_end)
        return max(self.end, self.start + (self.end - self.start) * self.pass_through_factor)

    def evaluate(self, elapsed: float, is_hit: bool = True) -> Optional[ProjectileMotion]:
        effective_end = self.end if is_hit else (
            self.miss_end if self.miss_end is not None else self.start + (self.end - self.start) * self.pass_through_factor
        )
        if self.start <= elapsed < effective_end:
            dur = max(0.001, self.end - self.start)
            progress = max(0.0, (elapsed - self.start) / dur)
            if is_hit:
                progress = min(1.0, progress)
            return ProjectileMotion(progress=progress, kind=self.kind, is_hit=is_hit)
        return None


@dataclass(frozen=True)
class ImpactTrack:
    """着弾・爆発・打撃等の衝撃演出トラック"""
    start: float
    end: float
    kind: str = "hit"
    only_on_hit: bool = True

    @property
    def max_time(self) -> float:
        return self.end

    def evaluate(self, elapsed: float, is_hit: bool) -> Optional[ImpactMotion]:
        if self.only_on_hit and not is_hit:
            return None
        if self.start <= elapsed < self.end:
            dur = max(0.001, self.end - self.start)
            progress = max(0.0, min(1.0, (elapsed - self.start) / dur))
            return ImpactMotion(progress=progress, kind=self.kind)
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
    contact_time: float = 0.45
    pass_start: float = 0.85
    exit_time: float = 1.25

    @property
    def max_time(self) -> float:
        return self.exit_time

    def evaluate(self, elapsed: float) -> Tuple[bool, Optional[ActorMotion]]:
        if elapsed < self.start:
            return True, None

        if elapsed < self.contact_time:
            dur = max(0.001, self.contact_time - self.start)
            raw_p = (elapsed - self.start) / dur
            p = raw_p * raw_p
            return True, ActorMotion(phase="approach", progress=min(1.0, max(0.0, p)))

        if elapsed < self.pass_start:
            return True, ActorMotion(phase="approach", progress=1.0)

        if elapsed < self.exit_time:
            dur = max(0.001, self.exit_time - self.pass_start)
            raw_p = (elapsed - self.pass_start) / dur
            p = raw_p * raw_p
            return True, ActorMotion(phase="pass_through", progress=min(1.0, max(0.0, p)))

        return False, None


@dataclass(frozen=True)
class CameraTrack:
    """カメラ追従演出のトラック（射撃時のスクロール）"""
    start: float
    end: float

    @property
    def max_time(self) -> float:
        return self.end

    def evaluate(self, elapsed: float) -> float:
        if elapsed <= self.start:
            return 0.0
        if elapsed >= self.end:
            return 1.0
        dur = max(0.001, self.end - self.start)
        t = (elapsed - self.start) / dur
        return t * t * (3.0 - 2.0 * t)


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


def build_shooting_profile(projectile_kind: str = "bullet", impact_kind: Optional[str] = None) -> CutinProfile:
    resolved_impact = impact_kind or ("explosion" if projectile_kind == "missile" else "hit")
    proj_start = 0.15
    proj_end = 0.85
    impact_start = 0.85
    impact_end = 1.10
    popup_start = 1.10

    flight_dur = proj_end - proj_start
    cam_start = proj_start + flight_dur * 0.25
    cam_end = proj_start + flight_dur * 0.75

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


SHOOTING_PROJECTILE_KINDS: Dict[SkillType, str] = {
    SkillType.RIFLE: "bullet",
    SkillType.GATLING: "bullet",
    SkillType.MISSILE: "missile",
}

MELEE_IMPACT_KINDS: Dict[SkillType, str] = {
    SkillType.SWORD: "hit",
    SkillType.HAMMER: "hit",
}


def resolve_cutin_profile(part) -> CutinProfile:
    if not part or not part.action:
        return FALLBACK_PROFILE

    category = part.action.category
    if category == ActionCategory.SHOOTING:
        projectile_kind = SHOOTING_PROJECTILE_KINDS.get(part.skill, "bullet")
        return build_shooting_profile(projectile_kind=projectile_kind)

    if category == ActionCategory.MELEE:
        impact_kind = MELEE_IMPACT_KINDS.get(part.skill, "hit")
        return build_melee_profile(impact_kind=impact_kind)

    return FALLBACK_PROFILE