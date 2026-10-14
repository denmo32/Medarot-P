"""敵AIの行動選択を担当するコントローラ。"""
from domain.ai_logic import get_tactics
from domain.constants import ACTIONABLE_PART_TYPES, TacticsType
from domain.models import TacticsContext
from .commands import SkipCommand, build_command_for_part
from .context import BattleContext
from .models import Robot
from .targeting_resolver import TargetingResolver


class AIController:
    def __init__(self, ctx: BattleContext, targeting: TargetingResolver):
        self.ctx = ctx
        self.targeting = targeting

    def decide_command(self, robot: Robot):
        valid_parts = [
            pt for pt, part in robot.iter_parts()
            if part.is_alive and pt in ACTIONABLE_PART_TYPES and part.is_implemented
        ]

        tactics_ctx = TacticsContext(
            hp_map=robot.get_parts_hp(),
            active_effects=tuple(robot.active_effects),
        )

        chosen = get_tactics(TacticsType.RANDOM).select_part(valid_parts, tactics_ctx, rng=self.ctx.rng)
        if not chosen:
            robot.set_command(SkipCommand(robot))
            return

        part = robot.get_part(chosen)
        if not part:
            robot.set_command(SkipCommand(robot))
            return

        preview_target = self.targeting.resolve_preview_target(robot, chosen)

        if part.locks_target and not preview_target:
            robot.set_command(SkipCommand(robot))
            return

        robot.set_command(build_command_for_part(robot, part, preview_target))