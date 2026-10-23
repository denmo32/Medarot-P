"""カットイン演出（機体・命中結果・飛翔および衝撃エフェクト）を描画する。"""
from typing import Callable, Dict, Optional, Tuple
import pygame

from domain.constants import TeamType
from ui_base.renderer import BaseRenderer
from ui_base.widgets import MedabotWidgets
from features.battle.ui import layout
from features.battle.presentation.view_models import (
    CutinActorModel,
    CutinModel,
    CutinPopupModel,
    ImpactEffectModel,
    ProjectileEffectModel,
)
from ui_base.config import resolve_accent_color
from features.battle.ui.config import BATTLE_UI_PARAMS as UI_PARAMS

ProjectileDrawFn = Callable[['CutinRenderer', int, int, ProjectileEffectModel, bool], None]
ImpactDrawFn = Callable[['CutinRenderer', int, int, ImpactEffectModel], None]


def _draw_bullet_projectile(
    renderer: 'CutinRenderer', current_x: int, y: int, proj: ProjectileEffectModel, is_left_to_right: bool
):
    r = max(3, renderer.scaled(UI_PARAMS.cutin_projectile_radius))
    pygame.draw.circle(renderer.screen, renderer.theme.bullet, (current_x, y), r)
    pygame.draw.circle(renderer.screen, renderer.theme.bullet_core, (current_x, y), max(1, r // 2))


def _draw_missile_projectile(
    renderer: 'CutinRenderer', current_x: int, y: int, proj: ProjectileEffectModel, is_left_to_right: bool
):
    r = max(4, renderer.scaled(9))
    pygame.draw.circle(renderer.screen, renderer.theme.bullet, (current_x, y), r)
    pygame.draw.circle(renderer.screen, (255, 100, 50), (current_x, y), max(2, r - 3))
    tail_offset = -renderer.scaled(10) if is_left_to_right else renderer.scaled(10)
    tail_x = int(current_x + tail_offset)
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

        if model.camera_progress is not None:
            actor_x, target_x = layout.calculate_cutin_scrolled_positions(
                model.actor.team, model.camera_progress, screen_size
            )
        else:
            actor_x = layout.calculate_cutin_actor_x(model.actor, screen_size)
            _, target_x = layout.calculate_cutin_actor_positions(model.actor.team, screen_size)

        center_y = cutin_layout['center_y']

        self.screen.set_clip(panel_rect)

        try:
            if model.actor.is_visible:
                self._draw_actor(actor_x, center_y, model.actor)

            for proj in model.projectiles:
                if not proj.is_hit:
                    self._draw_projectile(proj, model.actor.team, model.camera_progress, center_y)

            if model.target.is_visible:
                self._draw_actor(target_x, center_y, model.target)

            for proj in model.projectiles:
                if proj.is_hit:
                    self._draw_projectile(proj, model.actor.team, model.camera_progress, center_y)

            for impact in model.impacts:
                self._draw_impact(target_x, center_y, impact)

            if model.popup is not None:
                self._draw_popup(target_x, center_y, model.popup)
        finally:
            self.screen.set_clip(None)

    def _draw_actor(self, x, y, actor: CutinActorModel):
        accent_color = resolve_accent_color(actor.accent_state, self.theme)
        self.widgets.draw_robot_icon(x, y, accent_color, actor.part_status)

    def _draw_projectile(
        self,
        projectile: ProjectileEffectModel,
        actor_team: TeamType,
        camera_progress: Optional[float],
        y: int,
    ):
        screen_size = self.get_screen_size()
        current_x = layout.calculate_cutin_projectile_x(
            projectile.progress, actor_team, camera_progress, screen_size
        )
        is_left_to_right = (actor_team == TeamType.PLAYER)
        handler = PROJECTILE_RENDERERS.get(projectile.kind, _draw_bullet_projectile)
        handler(self, current_x, y, projectile, is_left_to_right)

    def _draw_impact(self, target_x: int, y: int, impact: ImpactEffectModel):
        handler = IMPACT_RENDERERS.get(impact.kind, _draw_hit_impact)
        handler(self, target_x, y, impact)

    def _draw_popup(self, target_x, center_y, popup: CutinPopupModel):
        damage_y = center_y - self.scaled(UI_PARAMS.cutin_damage_offset)
        if popup.is_miss:
            self.draw_text_with_outline(popup.damage_label, target_x, damage_y, self.theme.text, 'large', 'center')
            return

        self.draw_text_with_outline(
            popup.primary_label, target_x, center_y - self.scaled(UI_PARAMS.cutin_label_offset),
            self.theme.text, 'normal', 'center'
        )
        self.draw_text_with_outline(popup.damage_label, target_x, damage_y, self.theme.text, 'large', 'center')