"""ログ構築ロジック（旧 LogService）"""

class LogBuilder:
    @staticmethod
    def get_attack_declaration(attacker_name: str, skill_name: str, trait_text: str = "") -> str:
        return f"{attacker_name}の{skill_name}攻撃！{trait_text}"

    @staticmethod
    def get_target_lost(actor_name: str) -> str:
        return f"{actor_name}はターゲットロストした！"

    @staticmethod
    def get_skip_action(actor_name: str) -> str:
        return f"{actor_name}は行動をスキップ！"

    @staticmethod
    def get_part_broken_interruption(actor_name: str) -> str:
        return f"{actor_name}の予約パーツは破壊された！"

    @staticmethod
    def get_part_broken_attack(actor_name: str) -> str:
        return f"{actor_name}の攻撃！ しかしパーツが破損している！"