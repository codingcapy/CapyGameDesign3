# author: Paul Kim
# date: October 9, 2022
# version: 1.0
import sys
from math import sin
from os import walk

from pygame import time

from world_map import *
import pygame

pygame.init()
pygame.display.set_caption("Capy Game Design 3")
WINDOW_WIDTH, WINDOW_HEIGHT = (1200, 800)
WINDOW = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
FPS = 60
TILESIZE = 64
BAR_HEIGHT = 20
HP_BAR_WIDTH = 200
MP_BAR_WIDTH = 200
ITEM_BOX_SIZE = 80
UI_FONT = 'arial'
UI_FONT_SIZE = 18
WATER_COLOR = '#71ddee'
UI_BG_COLOR = '#222222'
UI_BORDER_COLOR = '#111111'
TEXT_COLOR = '#EEEEEE'
HP_COLOR = '#70e000'
MP_COLOR = '#7b2cbf'
UI_BORDER_ACTIVE_COLOR = 'gold'

weapon_data = {'sword': {'cooldown': 50, 'damage': 15, 'graphics': 'assets/weapon/sword/down.png'}}
magic_data = {'heal': {'damage': 10, 'cost': 20, 'graphics': 'assets/magic/heal/3.png'},
              'dash': {'damage:': 0, 'cost': 0, 'graphics': 'assets/magic/dash/5.png'},
              'slash': {'damage': 100, 'cost': 20, 'graphics': 'assets/magic/slash/0.png'}}
monster_data = {'mushroom': {'hp': 100, 'exp': 100, 'damage': 10, 'attack_type': 'slam', 'speed': 3, 'resistance': 1,
                             'attack_radius': 100, 'notice_radius': 200},
                'boss': {'hp': 1000, 'exp': 1000, 'damage': 20, 'attack_type': 'flame', 'speed': 3, 'resistance': 1,
                         'attack_radius': 100, 'notice_radius': 200}}


class World:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False
        self.upgrade_screen = False
        self.visible_sprites = CameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.current_attack = None
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()
        self.create_map()
        self.ui = UI()
        self.pause_screen = PauseScreen(self.player)
        self.upgrade_menu = UpgradeMenu(self.player)
        self.animation = Animation()
        self.magic_animation = MagicAnimation(self.animation)

    def create_map(self):
        for row_index, row in enumerate(WORLD_MAP):
            for col_index, col in enumerate(row):
                x = col_index * TILESIZE
                y = row_index * TILESIZE
                if col == 'x':
                    Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object')
                if col == 't':
                    Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'tree')
                if col == 'p':
                    self.player = Player((x, y), [self.visible_sprites], self.obstacle_sprites, self.create_attack,
                                         self.remove_attack, self.create_magic)
                if col == 'm':
                    monster_name = 'mushroom'
                    Enemy(monster_name, (x, y), [self.visible_sprites, self.attackable_sprites], self.obstacle_sprites,
                          self.damage_player, self.trigger_defeat_particles, self.add_exp)
                if col == 'b':
                    monster_name = 'boss'
                    Enemy(monster_name, (x, y), [self.visible_sprites, self.attackable_sprites], self.obstacle_sprites,
                          self.damage_player, self.trigger_defeat_particles, self.add_exp)

    def create_attack(self):
        self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def create_magic(self, style, damage, cost):
        if style == 'heal':
            self.magic_animation.heal(self.player, damage, cost, [self.visible_sprites])
        if style == 'dash':
            self.magic_animation.dash(self.player, damage, cost, [self.visible_sprites])
        if style == 'slash':
            self.magic_animation.slash(self.player, cost, [self.visible_sprites, self.attack_sprites])

    def remove_attack(self):
        if self.current_attack:
            self.current_attack.kill()
        self.current_attack = None

    def player_attack_logic(self):
        if self.attack_sprites:
            for attack_sprite in self.attack_sprites:
                collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, False)
                if collision_sprites:
                    for target_sprite in collision_sprites:
                        if target_sprite.sprite_type == 'object':
                            target_sprite.kill()
                        else:
                            target_sprite.get_damage(self.player, attack_sprite.sprite_type)

    def damage_player(self, amount, attack_type):
        if self.player.vulnerable:
            self.player.hp -= amount
            self.player.vulnerable = False
            self.player.hurt_time = pygame.time.get_ticks()
            self.animation.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])
            if self.player.hp <= -10:
                lost_font = pygame.font.SysFont("arial", 60)
                lost_label = lost_font.render(f"Game Over", 1, 'white')
                WINDOW.blit(lost_label, (WINDOW_WIDTH // 2 - lost_label.get_width() // 2, 350))
                pygame.time.wait(3000)
                main_menu()
            elif self.player.exp >= 4900:
                pygame.time.wait(3000)
                main_menu()

    def trigger_defeat_particles(self, pos, particle_type):
        self.animation.create_particles(particle_type, pos, self.visible_sprites)

    def add_exp(self, amount):
        self.player.exp += amount

    def toggle_pause(self):
        self.game_paused = not self.game_paused

    def toggle_menu(self):
        self.upgrade_screen = not self.upgrade_screen

    def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)
        if self.game_paused:
            self.pause_screen.display()
        if self.upgrade_screen:
            self.upgrade_menu.display()
        else:
            self.visible_sprites.update()
            self.visible_sprites.enemy_update(self.player)
            self.player_attack_logic()


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.offset = pygame.math.Vector2()
        self.floor_surf = pygame.image.load('assets/environment/grass3.jpg').convert()
        self.floor_surf2 = pygame.image.load('assets/environment/desert4.jpg').convert()
        self.floor_rect = self.floor_surf.get_rect(topleft=(-750, -750))
        self.floor_rect2 = self.floor_surf.get_rect(topleft=(-750, 2322))

    def custom_draw(self, player):
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height
        floor_offset_pos = self.floor_rect.topleft - self.offset
        floor_offset_pos2 = self.floor_rect2.topleft - self.offset
        self.display_surface.blit(self.floor_surf, floor_offset_pos)
        self.display_surface.blit(self.floor_surf2, floor_offset_pos2)
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)

    def enemy_update(self, player):
        enemy_sprites = [sprite for sprite in self.sprites() if
                         hasattr(sprite, 'sprite_type') and sprite.sprite_type == 'enemy']
        for enemy in enemy_sprites:
            enemy.enemy_update(player)


class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, sprite_type):
        super().__init__(groups)
        self.sprite_type = sprite_type
        if sprite_type == 'object':
            self.image = pygame.transform.scale(pygame.image.load('assets/environment/rock.png').convert_alpha(),
                                                (TILESIZE, TILESIZE))
        if sprite_type == 'tree':
            self.image = pygame.transform.scale(pygame.image.load('assets/environment/tree1.png').convert_alpha(),
                                                (TILESIZE * 2, TILESIZE * 2))

        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)


class Entity(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)
        self.frame_index = 0
        self.animation_speed = 0.15
        self.direction = pygame.math.Vector2()

    def move(self, speed):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
        self.hitbox.x += self.direction.x * speed
        self.collision('horizontal')
        self.hitbox.y += self.direction.y * speed
        self.collision('vertical')
        self.rect.center = self.hitbox.center

    def collision(self, direction):
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.x > 0:
                        self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0:
                        self.hitbox.left = sprite.hitbox.right
        if direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.y > 0:
                        self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0:
                        self.hitbox.top = sprite.hitbox.bottom

    def wave_value(self):
        value = sin(pygame.time.get_ticks())
        if value >= 0:
            return 255
        else:
            return 0


class Player(Entity):
    def __init__(self, pos, groups, obstacle_sprites, create_attack, remove_attack, create_magic):
        super().__init__(groups)
        self.image = pygame.transform.scale(pygame.image.load('assets/player/down_idle/idle_down.png').convert_alpha(),
                                            (TILESIZE, TILESIZE))
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -26)
        self.initiate_player_assets()
        self.status = 'down'
        self.attacking = False
        self.attack_cooldown = 200
        self.attack_time = None
        self.create_attack = create_attack
        self.remove_attack = remove_attack
        self.weapon_index = 0
        self.weapon = list(weapon_data.keys())[self.weapon_index]
        self.create_magic = create_magic
        self.magic_index = 0
        self.magic = list(magic_data.keys())[self.magic_index]
        self.obstacle_sprites = obstacle_sprites
        self.stats = {'hp': 100, 'mp': 100, 'attack': 10, 'magic': 10, 'speed': 5}
        self.hp = self.stats['hp']
        self.mp = self.stats['mp']
        self.exp = 0
        self.speed = self.stats['speed']
        self.vulnerable = True
        self.hurt_time = None
        self.invulnerability_duration = 400
        self.dashing = False
        self.dash_cooldown = 400
        self.dash_time = None

    def initiate_player_assets(self):
        character_path = 'assets/player/'
        self.animations = {'up': [], 'down': [], 'left': [], 'right': [], 'up_idle': [], 'down_idle': [],
                           'left_idle': [],
                           'right_idle': [], 'up_attack': [], 'down_attack': [], 'left_attack': [], 'right_attack': []}
        for animation in self.animations.keys():
            full_path = character_path + animation
            self.animations[animation] = import_folder(full_path)
        print(self.animations)

    def user_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            self.direction.y = -1
            self.status = 'up'

        elif keys[pygame.K_DOWN]:
            self.direction.y = 1
            self.status = 'down'
        else:
            self.direction.y = 0
        if keys[pygame.K_LEFT]:
            self.direction.x = -1
            self.status = 'left'
        elif keys[pygame.K_RIGHT]:
            self.direction.x = 1
            self.status = 'right'
        else:
            self.direction.x = 0
        if keys[pygame.K_q] and not self.attacking:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            self.create_attack()
        if keys[pygame.K_w] and not self.attacking:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            style = list(magic_data.keys())[self.magic_index]
            damage = list(magic_data.values())[self.magic_index]['damage'] + self.stats['magic']
            cost = list(magic_data.values())[self.magic_index]['cost']
            self.create_magic(style, damage, cost)
        if keys[pygame.K_e] and not self.attacking:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            style = list(magic_data.keys())[2]
            damage = list(magic_data.values())[2]['damage'] + self.stats['magic']
            cost = list(magic_data.values())[2]['cost']
            self.create_magic(style, damage, cost)

        if keys[pygame.K_SPACE] and not self.dashing:
            self.dashing = True
            self.dash_time = pygame.time.get_ticks()
            self.dash()
            style = list(magic_data.keys())[1]
            damage = list(magic_data.values())[self.magic_index]['damage'] + self.stats['magic']
            cost = list(magic_data.values())[self.magic_index]['cost']
            self.create_magic(style, damage, cost)

    def get_status(self):
        if self.direction.x == 0 and self.direction.y == 0:
            if not 'idle' in self.status and not 'attack' in self.status:
                self.status = self.status + '_idle'
        if self.attacking:
            self.direction.x = 0
            self.direction.y = 0
            if not 'attack' in self.status:
                if 'idle' in self.status:
                    self.status = self.status.replace('_idle', '_attack')
                else:
                    self.status = self.status + '_attack'
        else:
            if 'attack' in self.status:
                self.status = self.status.replace('_attack', '')

    def animate(self):
        animation = self.animations[self.status]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0
        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.hitbox.center)
        if not self.vulnerable:
            alpha = self.wave_value()
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def get_full_weapon_damage(self):
        base_damage = self.stats['attack']
        weapon_damage = weapon_data[self.weapon]['damage']
        return base_damage + weapon_damage

    def get_full_magic_damage(self):
        base_damage = self.stats['magic']
        spell_damage = magic_data['slash']['damage']
        return base_damage + spell_damage

    def dash(self):
        self.speed += 5

    def remove_dash(self):
        self.speed -= 5

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if self.attacking:
            if current_time - self.attack_time >= self.attack_cooldown + weapon_data[self.weapon]['cooldown']:
                self.attacking = False
                self.remove_attack()
        if not self.vulnerable:
            if current_time - self.hurt_time >= self.invulnerability_duration:
                self.vulnerable = True
        if self.dashing:
            if current_time - self.dash_time >= self.dash_cooldown:
                self.dashing = False
                self.remove_dash()

    def mp_recovery(self):
        if self.mp < self.stats['mp']:
            self.mp += 0.01 * self.stats['magic']
        else:
            self.mp = self.stats['mp']

    def update(self):
        self.user_input()
        self.cooldowns()
        self.get_status()
        self.move(self.speed)
        self.mp_recovery()
        self.animate()


class Enemy(Entity):
    def __init__(self, monster_name, pos, groups, obstacle_sprites, damage_player, trigger_defeat_particles, add_exp):
        super().__init__(groups)
        self.sprite_type = 'enemy'
        self.import_graphics(monster_name)
        self.status = 'idle'
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)
        self.obstacle_sprites = obstacle_sprites
        self.vulnerable = True
        self.hit_time = None
        self.invincibility_duration = 200
        self.monster_name = monster_name
        monster_info = monster_data[self.monster_name]
        self.hp = monster_info['hp']
        self.speed = monster_info['speed']
        self.resistance = monster_info['resistance']
        self.notice_radius = monster_info['notice_radius']
        self.attack_radius = monster_info['attack_radius']
        self.attack_type = monster_info['attack_type']
        self.attack_damage = monster_info['damage']
        self.exp = monster_info['exp']
        self.can_attack = True
        self.attack_time = None
        self.attack_cooldown = 400
        self.damage_player = damage_player
        self.trigger_defeat_particles = trigger_defeat_particles
        self.add_exp = add_exp

    def import_graphics(self, name):
        self.animations = {'idle': [], 'move': [], 'attack': []}
        main_path = f'assets/monster/{name}/'
        for animation in self.animations.keys():
            self.animations[animation] = import_folder(main_path + animation)

    def animate(self):
        animation = self.animations[self.status]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.status == 'attack':
                self.can_attack = False
            self.frame_index = 0
        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.hitbox.center)
        if not self.vulnerable:
            alpha = self.wave_value()
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def get_player_distance_direction(self, player):
        enemy_vector = pygame.math.Vector2(self.rect.center)
        player_vector = pygame.math.Vector2(player.rect.center)
        distance = (player_vector - enemy_vector).magnitude()
        if distance > 0:
            direction = (player_vector - enemy_vector).normalize()
        else:
            direction = pygame.math.Vector2()
        return (distance, direction)

    def get_status(self, player):
        distance = self.get_player_distance_direction(player)[0]
        if distance <= self.attack_radius and self.can_attack:
            if self.status != 'attack':
                self.frame_index = 0
            self.status = 'attack'
        elif distance <= self.notice_radius:
            self.status = 'move'
        else:
            self.status = 'idle'

    def actions(self, player):
        if self.status == 'attack':
            self.attack_time = pygame.time.get_ticks()
            self.damage_player(self.attack_damage, self.attack_type)
        elif self.status == 'move':
            self.direction = self.get_player_distance_direction(player)[1]
        else:
            self.direction = pygame.math.Vector2()

    def cooldown(self):
        current_time = pygame.time.get_ticks()
        if not self.can_attack:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True
        if not self.vulnerable:
            if current_time - self.hit_time >= self.invincibility_duration:
                self.vulnerable = True

    def get_damage(self, player, attack_type):
        self.direction = self.get_player_distance_direction(player)[1]
        if self.vulnerable:
            if attack_type == 'weapon':
                self.hp -= player.get_full_weapon_damage()
            else:
                self.hp -= player.get_full_magic_damage()
            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False

    def hit_reaction(self):
        if not self.vulnerable:
            self.direction *= -self.resistance

    def check_death(self):
        if self.hp <= 0:
            self.kill()
            self.trigger_defeat_particles(self.rect.center, self.monster_name)
            self.add_exp(self.exp)

    def update(self):
        self.hit_reaction()
        self.animate()
        self.move(self.speed)
        self.cooldown()
        self.check_death()

    def enemy_update(self, player):
        self.get_status(player)
        self.actions(player)


class Weapon(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        super().__init__(groups)
        self.sprite_type = 'weapon'
        direction = player.status.split('_')[0]
        full_path = f'assets/weapon/{player.weapon}/{direction}.png'
        self.image = pygame.image.load(full_path).convert_alpha()
        if direction == 'right':
            self.rect = self.image.get_rect(midleft=player.rect.midright + pygame.math.Vector2(-20, 15))
        elif direction == 'left':
            self.rect = self.image.get_rect(midright=player.rect.midleft + pygame.math.Vector2(20, 15))
        elif direction == 'down':
            self.rect = self.image.get_rect(midtop=player.rect.midbottom + pygame.math.Vector2(0, -30))
        else:
            self.rect = self.image.get_rect(midbottom=player.rect.midtop + pygame.math.Vector2(0, 30))


class Animation:
    def __init__(self):
        self.frames = {'mushroom': import_folder('assets/monster/mushroom/defeat'),
                       'slam': import_folder('assets/monster/mushroom/slam'),
                       'boss': import_folder('assets/monster/boss/defeat'),
                       'flame': import_folder('assets/monster/boss/flame'),
                       'heal': import_folder('assets/magic/heal'),
                       'dash': import_folder('assets/magic/dash'),
                       'slash': import_folder('assets/magic/slash')}

    def create_particles(self, animation_type, pos, groups):
        animation_frames = self.frames[animation_type]
        ParticleEffect(pos, animation_frames, groups)


class ParticleEffect(pygame.sprite.Sprite):
    def __init__(self, pos, animation_frames, groups):
        super().__init__(groups)
        self.sprite_type = 'magic'
        self.frame_index = 0
        self.animation_speed = 0.15
        self.frames = animation_frames
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=pos)

    def animate(self):
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.frames):
            self.kill()
        else:
            self.image = self.frames[(int(self.frame_index))]

    def update(self):
        self.animate()


class MagicAnimation:
    def __init__(self, animation):
        self.animation = animation

    def heal(self, player, damage, cost, groups):
        if player.mp >= cost:
            player.hp += damage
            player.mp -= cost
            if player.hp >= player.stats['hp']:
                player.hp = player.stats['hp']
            self.animation.create_particles('heal', player.rect.center, groups)

    def dash(self, player, damage, cost, groups):
        self.animation.create_particles('dash', player.rect.center + pygame.math.Vector2(0, 50), groups)

    def slash(self, player, cost, groups):
        if player.mp >= cost:
            player.mp -= cost
            # if player.status.split('_')[0] == 'right':
            #     direction = pygame.math.Vector2(1, 0)
            # elif player.status.split('_')[0] == 'left':
            #     direction = pygame.math.Vector2(-1, 0)
            # elif player.status.split('_')[0] == 'up':
            #     direction = pygame.math.Vector2(0, -1)
            # else:
            #     direction = pygame.math.Vector2(0, 1)
            #
            # for i in range(1, 6):
            #     if direction.x:
            #         offset_x = (direction.x) * TILESIZE
            #         x = player.rect.centerx + offset_x
            #         y = player.rect.centery
            #         self.animation.create_particles('slash', (x, y), groups)
            #     if direction.y:
            #         offset_y = (direction.y) * TILESIZE
            #         x = player.rect.centerx
            #         y = player.rect.centery + offset_y
            #         self.animation.create_particles('slash', (x, y), groups)

            self.sprite_type = 'weapon'
            direction = player.status.split('_')[0]
            full_path = f'assets/magic/slash/{direction}.png'
            self.image = pygame.image.load(full_path).convert_alpha()
            if direction == 'right':
                self.image.get_rect(midleft=player.rect.midright + pygame.math.Vector2(-20, 15))
            elif direction == 'left':
                self.image.get_rect(midright=player.rect.midleft + pygame.math.Vector2(20, 15))
            elif direction == 'down':
                self.rect = self.image.get_rect(midtop=player.rect.midbottom + pygame.math.Vector2(0, -30))
            else:
                self.rect = self.image.get_rect(midbottom=player.rect.midtop + pygame.math.Vector2(0, 30))
            self.animation.create_particles('slash', player.rect.center, groups)
class UI:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.SysFont('arial', 35)
        self.hp_bar_rect = pygame.Rect(50, 40, HP_BAR_WIDTH, BAR_HEIGHT)
        self.mp_bar_rect = pygame.Rect(50, 64, MP_BAR_WIDTH, BAR_HEIGHT)

    def show_bar(self, current, max_amount, bg_rect, color):
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        ratio = current / max_amount
        current_width = bg_rect.width * ratio
        current_rect = bg_rect.copy()
        current_rect.width = current_width
        pygame.draw.rect(self.display_surface, color, current_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)

    def show_exp(self, exp):
        text_surf = self.font.render(str(int(exp)), False, TEXT_COLOR)
        x = self.display_surface.get_size()[0] - 60
        y = self.display_surface.get_size()[1] - 60
        text_rect = text_surf.get_rect(bottomright=(x, y))
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, text_rect.inflate(20, 20))
        self.display_surface.blit(text_surf, text_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, text_rect.inflate(20, 20), 3)

    def display(self, player):
        self.show_bar(player.hp, player.stats['hp'], self.hp_bar_rect, HP_COLOR)
        self.show_bar(player.mp, player.stats['mp'], self.mp_bar_rect, MP_COLOR)
        self.show_exp(player.exp)


class PauseScreen:
    def __init__(self, player):
        self.display_surface = pygame.display.get_surface()
        self.player = player

    def display(self):
        self.display_surface.fill((0, 50, 100))
        controls_font = pygame.font.SysFont('Arial', 35)
        controls_label = controls_font.render("Controls", 1, 'white')
        controls_display = controls_font.render("Arrow keys: move player", 1, 'white')
        controls_display2 = controls_font.render("Space bar: dash", 1, 'white')
        controls_display3 = controls_font.render("Q:Attack", 1, 'white')
        controls_display4 = controls_font.render("W:Heal Magic", 1, 'white')
        controls_display5 = controls_font.render("Esc/I/C/M:Pause", 1, 'white')
        WINDOW.blit(controls_label, (WINDOW_WIDTH // 2 - controls_label.get_width(), 200))
        WINDOW.blit(controls_display, (WINDOW_WIDTH // 2 - controls_label.get_width(), 250))
        WINDOW.blit(controls_display2, (WINDOW_WIDTH // 2 - controls_label.get_width(), 300))
        WINDOW.blit(controls_display3, (WINDOW_WIDTH // 2 - controls_label.get_width(), 350))
        WINDOW.blit(controls_display4, (WINDOW_WIDTH // 2 - controls_label.get_width(), 400))
        WINDOW.blit(controls_display5, (WINDOW_WIDTH // 2 - controls_label.get_width(), 450))


class UpgradeMenu:
    def __init__(self, player):
        self.display_surface = pygame.display.get_surface()
        self.player = player
        self.attribute_nr = len(player.stats)
        self.attribute_names = list(player.stats.keys())
        self.height = self.display_surface.get_size()[1] * 0.8
        self.width = self.display_surface.get_size()[0] // 6
        self.font = pygame.font.SysFont('Arial', 35)
        self.create_items()
        self.selection_index = 0
        self.selection_time = None
        self.can_move = True

    def create_items(self):
        self.item_list = []
        for item, index in enumerate(range(self.attribute_nr)):
            full_width = self.display_surface.get_size()[0]
            increment = full_width // self.attribute_nr
            top = self.display_surface.get_size()[1] * 0.1
            left = (item * increment) + (increment - self.width) // 2
            item = MenuItem(left, top, self.width, self.height, index, self.font)
            self.item_list.append(item)

    def display(self):
        self.display_surface.fill((0, 50, 100))
        for item in self.item_list:
            item.display(self.display_surface, 0, 'test', 1, 2, 3)


class MenuItem:
    def __init__(self, left, top, width, height, index, font):
        self.rect = pygame.Rect(left, top, width, height)
        self.index = index
        self.font = font

    def display(self, surface, selection_num, name, value, max_value, cost):
        pygame.draw.rect(surface, 'grey', self.rect)


def import_folder(path):
    surface_list = []
    for _, __, img_files in walk(path):
        for image in img_files:
            full_path = path + '/' + image
            image_surf = pygame.image.load(full_path).convert_alpha()
            surface_list.append(image_surf)
    return surface_list


# Debug
font = pygame.font.Font(None, 30)


def debug(info, y=10, x=10):
    display_surface = pygame.display.get_surface()
    debug_surf = font.render(str(info), True, 'White')
    debug_rect = debug_surf.get_rect(topleft=(x, y))
    pygame.draw.rect(display_surface, 'Black', debug_rect)
    display_surface.blit(debug_surf, debug_rect)


def main():
    clock = pygame.time.Clock()
    world = World()
    run = True
    while run:
        clock.tick(FPS)
        WINDOW.fill('white')
        world.run()
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_i:
                    world.toggle_pause()
                if event.key == pygame.K_c or event.key == pygame.K_m:
                    world.toggle_menu()
    pygame.quit()
    sys.exit()


def main_menu():
    title_font = pygame.font.SysFont("arial", 70)
    run = True
    while run:
        background = pygame.image.load('assets/main_menu/background.jpg')
        WINDOW.blit(background, (0, 0))
        title_label = title_font.render("GameDesign3 Prototype by CapyTech", 1, 'white')
        start_label = title_font.render("Click anywhere to begin", 1, 'white')
        WINDOW.blit(title_label, (WINDOW_WIDTH // 2 - title_label.get_width() // 2, 250))
        WINDOW.blit(start_label, (WINDOW_WIDTH // 2 - start_label.get_width() // 2, 350))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                main()
            if event.type == pygame.KEYDOWN:
                main()
    exit()


if __name__ == "__main__":
    main_menu()
