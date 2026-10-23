"""バトルログ（表示文言）の生成を集約するビルダー。"""
from typing import TYPE_CHECKING, List, Optional

from domain.constants import PartType, PART_TYPE_LABELS, SkillType, EffectType, TeamType
from domain.effect_payloads import (
    AppliedEffect, PartRepair, PartRestore, TrapInstall, ApplyStatus
)
from domain.models import ActionResult, StatusEffect
from ..entities.commands import ExecutionOutcome

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
        """開戦時のログ"""
        return ["合意と見てよろしいですね！？"]

    @staticmethod
    def battle_end(winner: TeamType) -> List[str]:
        """決着時の勝敗ログ"""
        if winner == TeamType.PLAYER:
            return ["リーダー機能停止！　プレイヤーの勝利！"]
        return ["リーダー機能停止！　プレイヤーの敗北……"]

    # === 宣言・事前検証 ===

    @staticmethod
    def trap_triggered(
        actor: 'Robot', part_type: PartType, skill: Optional[SkillType], damage: int, is_destroyed: bool
    ) -> List[str]:
        """トラップ先行発動時のログ"""
        label = PART_TYPE_LABELS.get(part_type, part_type.value)
        messages = [
            f"{skill.value}発動！",
            f"{actor.name}の{label}に {damage} のダメージ！",
        ]
        if is_destroyed:
            messages.append(f"{actor.name}の{label}は破壊された！")
        return messages

    @staticmethod
    def declaration(actor: 'Robot', part: 'Part') -> List[str]:
        """行動形式・技の宣言ログ（例: 「メタビーの撃つ　ライフル！」）"""
        if not part.is_implemented:
            action_label = part.action.value if part.action else "未定義"
            return [f"err: 未実装の行動形式「{action_label}」"]
        action_label = part.action.value if part.action else "未定義"
        skill_label = part.skill.value if part.skill else ""
        skill_text = f"　{skill_label}！" if skill_label else "！"
        return [f"{actor.name}の{action_label}行動！{skill_text}"]

    @staticmethod
    def intercepted(blocker: 'Robot') -> List[str]:
        """身代わり発生ログ"""
        return [f"{blocker.name}が身代わりになった！"]

    # === 行動実行の結果 ===

    @staticmethod
    def skipped(actor: 'Robot') -> List[str]:
        """スキップ行動のログ"""
        return [f"{actor.name}は行動をスキップ！"]

    @staticmethod
    def part_stopped(actor: 'Robot', part_type: PartType) -> List[str]:
        """停止中パーツによる行動失敗ログ"""
        label = PART_TYPE_LABELS.get(part_type, part_type.value)
        return [f"行動失敗！　{actor.name}の{label}は停止している！"]

    @staticmethod
    def execution_failure(actor: 'Robot', command: Optional['BattleCommand'],
                          outcome: ExecutionOutcome) -> List[str]:
        if outcome is ExecutionOutcome.PART_UNUSABLE:
            return [f"{actor.name}の行動パーツは使用不能だ！"]
        if outcome is ExecutionOutcome.TRAP_DESTROYED:
            return [f"{actor.name}の行動パーツは破壊された！"]
        if outcome is ExecutionOutcome.TARGET_LOST:
            return [f"{actor.name}はターゲットを失った！"]
        return []

    @staticmethod
    def interruption(robot: 'Robot', reason: ExecutionOutcome) -> List[str]:
        """充填中の割り込み（予約パーツ破壊／ターゲット喪失）ログ"""
        if reason is ExecutionOutcome.RESERVED_PART_DESTROYED:
            return [f"{robot.name}の予約パーツは破壊された！"]

        return [f"{robot.name}はターゲットを失った！"]

    @staticmethod
    def pierce() -> List[str]:
        """貫通ダメージ発生時のログ"""
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
            msgs = cls._format_applied_effect(applied, target)
            messages.extend(msgs)

        return messages

    @classmethod
    def _format_applied_effect(cls, effect: AppliedEffect, target: 'Robot') -> List[str]:
        target_name = target.name
        team_label = "味方チーム" if target.team.value == "player" else "相手チーム"

        if isinstance(effect, PartRepair):
            label = PART_TYPE_LABELS.get(effect.part_type, effect.part_type.value)
            return [f"{target_name}の{label}が {effect.amount} 回復した！"]

        if isinstance(effect, PartRestore):
            label = PART_TYPE_LABELS.get(effect.part_type, effect.part_type.value)
            return [f"{target_name}の{label}が復元された！"]

        if isinstance(effect, TrapInstall):
            return [f"{team_label}に「{effect.trap.skill.value}」が設置された！"]

        if isinstance(effect, ApplyStatus):
            eff = effect.effect
            if eff.type == EffectType.STOP:
                label = PART_TYPE_LABELS.get(eff.part_type, "") if eff.part_type else ""
                return [f"{target_name}の{label}が停止した！" if label else f"{target_name}が停止した！"]
            if eff.type == EffectType.BLOCK:
                return [f"{target_name}は味方への攻撃を庇う！"]
            if eff.type == EffectType.PROTECT:
                return [f"{target_name}はダメージを減少する！"]
            if eff.type == EffectType.SUCCESS_UP:
                return [f"{target_name}の命中度が上がった！ 残り{eff.charges}回"]

        return []