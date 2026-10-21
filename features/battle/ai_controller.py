"""敵AIの行動選択を担当するコントローラ。"""
from domain.ai_logic import get_tactics
from domain.constants import TacticsType
from domain.models import TacticsContext
from .context import BattleContext
from .entities.commands import SkipCommand, build_command_for_part
from .entities.robot import Robot
from .execution.targeting_resolver import TargetingResolver


class AIController:
    def __init__(self, ctx: BattleContext, targeting: TargetingResolver):
        self.ctx = ctx
        self.targeting = targeting

    def decide_command(self, robot: Robot):
        # 【改善】外部で iter_parts() や is_alive, is_implemented を判定せず、Robot に自己診断を命じる
        valid_parts = robot.get_actionable_part_types()

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