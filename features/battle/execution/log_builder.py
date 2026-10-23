# features/battle/execution/log_builder.py
"""バトルログ（表示文言）の生成を集約するビルダー。"""
from typing import TYPE_CHECKING, List, Optional

from domain.constants import PartType, SkillType, EffectType, TeamType
from domain.models import ActionResult, StatusEffect
from .effect_handlers import dispatch_format_log
from ..entities.commands import ExecutionOutcome, PartCommand

if TYPE_CHECKING:
    from ..entities.commands import BattleCommand
    from ..entities.part import Part
    from ..entities.robot import Robot

STATUS_EXPIRE_MESSAGES = {
    EffectType.SUCCESS_UP: "{actor}のスキャン効果が切れた！",
}


class BattleLogBuilder:
    """実行結果からバトルログ文言を生成するビルダー"""

    # === 開戦・勝敗 ===

    @staticmethod
    def opening() -> List[str]:
        return ["合意と見てよろしいですね！？"]

    @staticmethod
    def battle_end(winner: TeamType) -> List[str]:
        if winner == TeamType.PLAYER:
            return ["リーダー機能停止！　プレイヤーの勝利！"]
        return ["リーダー機能停止！　プレイヤーの敗北……"]

    # === 宣言・事前検証 ===

    @staticmethod
    def trap_triggered(
        actor: 'Robot', part_type: PartType, skill: Optional[SkillType], damage: int, is_destroyed: bool
    ) -> List[str]:
        label = part_type.label
        messages = [
            f"{skill.value}発動！",
            f"{actor.name}の{label}に {damage} のダメージ！",
        ]
        if is_destroyed:
            messages.append(f"{actor.name}の{label}は破壊された！")
        return messages

    @staticmethod
    def declaration(actor: 'Robot', part: 'Part') -> List[str]:
        if not part.is_implemented:
            action_label = part.action.value if part.action else "未定義"
            return [f"err: 未実装の行動形式「{action_label}」"]
        action_label = part.action.value if part.action else "未定義"
        skill_label = part.skill.value if part.skill else ""
        skill_text = f"　{skill_label}！" if skill_label else "！"
        return [f"{actor.name}の{action_label}行動！{skill_text}"]

    @staticmethod
    def intercepted(blocker: 'Robot') -> List[str]:
        return [f"{blocker.name}が身代わりになった！"]

    # === 行動実行の結果 ===

    @staticmethod
    def skipped(actor: 'Robot') -> List[str]:
        return [f"{actor.name}は行動をスキップ！"]

    @staticmethod
    def execution_failure(
        actor: 'Robot', command: Optional['BattleCommand'], outcome: ExecutionOutcome
    ) -> List[str]:
        if outcome is ExecutionOutcome.PART_STOPPED:
            part_type = command.part_type if isinstance(command, PartCommand) else None
            label = part_type.label if part_type else "パーツ"
            return [f"行動失敗！　{actor.name}の{label}は停止している！"]
        if outcome is ExecutionOutcome.PART_UNUSABLE:
            return [f"{actor.name}の行動パーツは使用不能だ！"]
        if outcome is ExecutionOutcome.TRAP_DESTROYED:
            return [f"{actor.name}の行動パーツは破壊された！"]
        if outcome is ExecutionOutcome.TARGET_LOST:
            return [f"{actor.name}はターゲットを失った！"]
        return []

    @staticmethod
    def interruption(robot: 'Robot', reason: ExecutionOutcome) -> List[str]:
        if reason is ExecutionOutcome.RESERVED_PART_DESTROYED:
            return [f"{robot.name}の予約パーツは破壊された！"]
        return [f"{robot.name}はターゲットを失った！"]

    @staticmethod
    def pierce() -> List[str]:
        return ["貫通ダメージ！"]

    # === 結果反映 ===

    @staticmethod
    def effect_expired(actor: 'Robot', effect: StatusEffect) -> Optional[str]:
        template = STATUS_EXPIRE_MESSAGES.get(effect.type)
        return template.format(actor=actor.name) if template else None

    @classmethod
    def effect_resolution(
        cls, result: Optional[ActionResult], target: Optional['Robot']
    ) -> List[str]:
        if result is None or target is None:
            return []

        if not result.success:
            if result.skill:
                return [f"{target.name}には効果がなかった！"]
            return []

        messages: List[str] = []
        for applied in result.applied_effects:
            messages.extend(dispatch_format_log(applied, target))

        return messages