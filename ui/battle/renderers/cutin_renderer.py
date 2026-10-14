"""カットイン演出（機体・命中結果・飛翔および衝撃エフェクト）を描画する。"""
from typing import Callable, Dict, Optional, Tuple
import pygame

from ui.base.renderer import BaseRenderer
from ui.base.widgets import MedabotWidgets
from ui.battle import layout
from features.battle.view_models import (
    CutinActorModel,
    CutinModel,
    CutinPopupModel,
    ImpactEffectModel,
    ProjectileEffectModel,
)
from ui.config import UI_PARAMS, resolve_accent_color

ProjectileDrawFn = Callable[['CutinRenderer', int, int, int, ProjectileEffectModel], None]
ImpactDrawFn = Callable[['CutinRenderer', int, int, ImpactEffectModel], None]


def _draw_bullet_projectile(renderer: 'CutinRenderer', start_x: int, end_x: int, y: int, proj: ProjectileEffectModel):
    progress = max(0.0, proj.progress)
    current_x = int(start_x + (end_x - start_x) * progress)
    r = max(3, renderer.scaled(UI_PARAMS.get('CUTIN_PROJECTILE_RADIUS', 7)))
    pygame.draw.circle(renderer.screen, renderer.theme.bullet, (current_x, y), r)
    pygame.draw.circle(renderer.screen, renderer.theme.bullet_core, (current_x, y), max(1, r // 2))


def _draw_missile_projectile(renderer: 'CutinRenderer', start_x: int, end_x: int, y: int, proj: ProjectileEffectModel):
    progress = max(0.0, proj.progress)
    current_x = int(start_x + (end_x - start_x) * progress)
    r = max(4, renderer.scaled(9))
    pygame.draw.circle(renderer.screen, renderer.theme.bullet, (current_x, y), r)
    pygame.draw.circle(renderer.screen, (255, 100, 50), (current_x, y), max(2, r - 3))
    tail_x = int(current_x - (end_x - start_x) * 0.05)
    pygame.draw.circle(renderer.screen, (180, 180, 180), (tail_x, y), max(2, r // 2))


PROJECTILE_RENDERERS: Dict[str, ProjectileDrawFn] = {
    "bullet": _draw_bullet_projectile,
    "missile": _draw_missile_projectile,
}


def _draw_hit_impact(renderer: 'CutinRenderer', target_x: int, y: int, impact: ImpactEffectModel):
    progress = max(0.0, min(1.0, impact.progress))
    max_r = renderer.scaled(24)
    current_r = max(3, int(max_r * progress))
    pygame.draw.circle(renderer.screen, (255, 255, 200), (target_x, y), current_r, max(1, renderer.scaled(2)))
    spark_len = int(current_r * 1.3)
    pygame.draw.line(renderer.screen, (255, 255, 255), (target_x - spark_len, y), (target_x + spark_len, y), 2)
    pygame.draw.line(renderer.screen, (255, 255, 255), (target_x, y - spark_len), (target_x + spark_len, y), 2)


def _draw_explosion_impact(renderer: 'CutinRenderer', target_x: int, y: int, impact: ImpactEffectModel):
    progress = max(0.0, min(1.0, impact.progress))
    max_r = renderer.scaled(36)
    current_r = max(4, int(max_r * (progress ** 0.5)))
    pygame.draw.circle(renderer.screen, (255, 120, 20), (target_x, y), current_r, max(2, renderer.scaled(3)))
    inner_r = max(2, int(current_r * 0.6))
    pygame.draw.circle(renderer.screen, (255, 240, 80), (target_x, y), inner_r)


IMPACT_RENDERERS: Dict[str, ImpactDrawFn] = {
    "hit": _draw_hit_impact,
    "explosion": _draw_explosion_impact,
}


class CutinRenderer(BaseRenderer):
    def __init__(self, screen):
        super().__init__(screen)
        self.widgets = MedabotWidgets(self)
        self._panel_cache: Optional[pygame.Surface] = None
        self._panel_cache_size: Optional[Tuple[int, int]] = None
        self._panel_cache_color: Optional[Tuple[int, ...]] = None

    def _get_panel_surface(self, size: Tuple[int, int]) -> pygame.Surface:
        color = self.theme.cutin_bg
        if self._panel_cache is None or self._panel_cache_size != size or self._panel_cache_color != color:
            panel = pygame.Surface(size, pygame.SRCALPHA)
            panel.fill(color)
            self._panel_cache = panel
            self._panel_cache_size = size
            self._panel_cache_color = color
        return self._panel_cache

    def render(self, model: CutinModel):
        screen_size = self.get_screen_size()
        cutin_layout = layout.calculate_cutin_layout(screen_size)

        panel_rect = cutin_layout['panel_rect']
        self.screen.blit(self._get_panel_surface(panel_rect.size), panel_rect.topleft)

        actor_x, target_x = layout.calculate_cutin_actor_positions(model.actor.team, screen_size)
        center_y = cutin_layout['center_y']

        self._draw_actor(actor_x, center_y, model.actor)

        # ミス時の飛翔体はターゲット機体の背後（奥）を通り抜けさせる
        for proj in model.projectiles:
            if not proj.is_hit:
                self._draw_projectile(actor_x, target_x, center_y, proj)

        self._draw_actor(target_x, center_y, model.target)

        # 命中時の飛翔体はターゲット機体の前面に着弾させる
        for proj in model.projectiles:
            if proj.is_hit:
                self._draw_projectile(actor_x, target_x, center_y, proj)

        # 着弾・爆発エフェクトの描画
        for impact in model.impacts:
            self._draw_impact(target_x, center_y, impact)

        # ダメージポップアップ
        if model.popup is not None:
            self._draw_popup(target_x, center_y, model.popup)

    def _draw_actor(self, x, y, actor: CutinActorModel):
        accent_color = resolve_accent_color(actor.accent_state, self.theme)
        self.widgets.draw_robot_icon(x, y, accent_color, actor.part_status)

    def _draw_projectile(self, start_x: int, end_x: int, y: int, projectile: ProjectileEffectModel):
        handler = PROJECTILE_RENDERERS.get(projectile.kind, _draw_bullet_projectile)
        handler(self, start_x, end_x, y, projectile)

    def _draw_impact(self, target_x: int, y: int, impact: ImpactEffectModel):
        handler = IMPACT_RENDERERS.get(impact.kind, _draw_hit_impact)
        handler(self, target_x, y, impact)

    def _draw_popup(self, target_x, center_y, popup: CutinPopupModel):
        damage_y = center_y - self.scaled(UI_PARAMS['CUTIN_DAMAGE_OFFSET'])
        if popup.is_miss:
            self.draw_text_with_outline(popup.damage_label, target_x, damage_y, self.theme.text, 'large', 'center')
            return

        self.draw_text_with_outline(
            popup.primary_label, target_x, center_y - self.scaled(UI_PARAMS['CUTIN_LABEL_OFFSET']),
            self.theme.text, 'normal', 'center'
        )
        self.draw_text_with_outline(popup.damage_label, target_x, damage_y, self.theme.text, 'large', 'center')