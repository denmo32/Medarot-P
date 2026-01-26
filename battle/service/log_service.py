"""バトルログ生成サービス"""

from typing import Optional

class LogService:
    """バトルログのメッセージ生成を一元管理するクラス"""

    @staticmethod
    def get_attack_declaration(attacker_name: str, skill_name: str, trait_text: str = "") -> str:
        """攻撃宣言ログ
        例: メタビーの狙い撃ち攻撃！ ライフル！
        """
        return f"{attacker_name}の{skill_name}攻撃！{trait_text}"

    @staticmethod
    def get_target_lost(actor_name: str) -> str:
        """ターゲットロストログ"""
        return f"{actor_name}はターゲットロストした！"

    @staticmethod
    def get_skip_action(actor_name: str) -> str:
        """行動スキップログ"""
        return f"{actor_name}は行動をスキップ！"

    @staticmethod
    def get_interruption(actor_name: str, reason: str) -> str:
        """行動中断ログ（理由は呼び出し側で指定）"""
        return reason

    @staticmethod
    def get_part_broken_interruption(actor_name: str) -> str:
        """予約パーツ破壊による中断ログ"""
        return f"{actor_name}の予約パーツは破壊された！"

    @staticmethod
    def get_part_broken_attack(actor_name: str) -> str:
        """攻撃実行時にパーツが壊れていた場合のログ"""
        return f"{actor_name}の攻撃！ しかしパーツが破損している！"