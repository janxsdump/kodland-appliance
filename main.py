import pgzrun
import random
import math
from pygame import Rect

show_menu = True
sound_on = True

WIDTH = 360
HEIGHT = 540

menu_buttons = [
    {"label": "Jogar", "rect": Rect((WIDTH//2 - 100, 200), (200, 50)),
     "action": "play"
     },
    {"label": "Sair", "rect": Rect((WIDTH//2 - 100, 270), (200, 50)),
     "action": "quit"
     },
    {"label": "Som: Ligado", "rect": Rect((WIDTH//2 - 100, 340), (200, 50)),
     "action": "toggle_sound"
     },
]

player = Actor("player")
player.midbottom = (WIDTH // 2, HEIGHT - 40)

bullets = []
enemies = []

# Upgrade config
cooldown = 1.5  # tempo entre tiros (segundos)
bullet_speed = 600
bullet_power = 1.1
multi_shot = 1
freeze_duration = 1.0
freeze_level = 0
bouncy_level = 0
luck = 0

shoot_timer = 0
xp = 0
level = 0
next_fib = 1
fib_seq = [1, 2]
paused = False
game_over = False
upgrade_options = []
upgrade_buttons = []
enemy_spawn_interval = 3.0
enemy_spawn_timer = enemy_spawn_interval
MIN_SPAWN_INTERVAL = 0.3
last_spawn_reduce_minute = -1
game_time = 0
wall_health = 100
wall_max_health = 100
wall_damage_timer = 0


def draw():
    screen.clear()

    if show_menu:
        if game_over:
            screen.draw.text("Obrigado por jogar",
                             center=(WIDTH // 2, HEIGHT // 2),
                             fontsize=40, color="white")
        else:
            draw_menu()
    else:
        draw_game()


def draw_menu():
    title = "C.A.S.T.L.E."
    screen.draw.text(title,
                     center=(WIDTH // 2, 100), fontsize=60, color="white")
    if not music.is_playing("menu"):
        music.play("menu")

    button_y = 200
    for btn in menu_buttons:
        rect = Rect((WIDTH // 2 - 100, button_y), (200, 50))
        screen.draw.filled_rect(rect, "darkgray")
        screen.draw.text(btn["label"],
                         center=rect.center, fontsize=30, color="black")
        btn["rect"] = rect  # salva o retângulo para detecção de clique
        button_y += 70


def toggle_sound():
    global sound_on
    sound_on = not sound_on
    if sound_on:
        music.set_volume(1.0)
    else:
        music.set_volume(0.0)

    # Atualiza o texto do botão de som
    for btn in menu_buttons:
        if btn["action"] == "toggle_sound":
            btn["label"] = f"Som: {'Ligado' if sound_on else 'Desligado'}"


def fib_up_to(n):
    while fib_seq[-1] < n:
        fib_seq.append(fib_seq[-1] + fib_seq[-2])


def spawn_enemy():
    if show_menu or paused:
        return

    enemy = Actor("enemy")
    enemy.pos = (random.randint(30, WIDTH - 15), -16)
    enemy.speed = 35
    enemy.hp = 3
    enemy.max_hp = 3
    enemy.frozen = 0
    enemy.image_index = 0
    enemy.images = ["enemy", "enemy2"]
    enemy.anim_timer = 0
    enemies.append(enemy)


def update(dt):
    global shoot_timer, paused, enemy_spawn_interval, game_time, game_over
    global wall_damage_timer, wall_health, show_menu, last_spawn_reduce_minute
    if show_menu or paused:
        return

    game_time += dt
    current_minute = int(game_time // 60)

    if current_minute > last_spawn_reduce_minute:
        last_spawn_reduce_minute = current_minute
        new_interval = max(enemy_spawn_interval * 0.80, MIN_SPAWN_INTERVAL)
        if new_interval != enemy_spawn_interval:
            enemy_spawn_interval = new_interval
            print(f"Novo intervalo: {enemy_spawn_interval:.2f}s")
            clock.unschedule(spawn_enemy)
            clock.schedule_interval(spawn_enemy, enemy_spawn_interval)

    shoot_timer -= dt
    if shoot_timer <= 0:
        shoot_timer = cooldown
        for i in range(multi_shot):
            delay = i * 0.1  # 100ms entre cada tiro
            clock.schedule(shoot, delay)
    if shoot_timer <= cooldown * (2/3):
        player.image = "player"

    for bullet in bullets[:]:
        bullet.x += bullet.vx * dt
        bullet.y += bullet.vy * dt
        if (bullet.y < 0
                or bullet.y > HEIGHT
                or bullet.x < 0
                or bullet.x > WIDTH):
            bullets.remove(bullet)

    for enemy in enemies[:]:
        if enemy.frozen > 0:
            enemy.frozen -= dt
            speed = enemy.speed * 0.2
        else:
            speed = enemy.speed
        if enemy.y < HEIGHT - 100:
            enemy.y += speed * dt

    wall_damage_timer -= dt
    if wall_damage_timer <= 0:
        touching_enemies = sum(1 for enemy in enemies
                               if enemy.y >= HEIGHT - 110)
        if touching_enemies > 0:
            wall_damage = touching_enemies * 1
            wall_health = max(0, wall_health - wall_damage)
        wall_damage_timer = 1.0  # reinicia o contador de 1 segundo
    if wall_health <= 0:
        wall_health = 0
        paused = True
        show_menu = True
        game_over = True
        music.stop()
        music.play("menu")

    animate_enemies(dt)
    check_collisions()


def check_collisions():
    global xp, level, paused, upgrade_options
    for bullet in bullets[:]:
        for enemy in enemies[:]:
            if bullet.colliderect(enemy):
                if (hasattr(bullet, "ignore_enemy")
                        and bullet.ignore_enemy == enemy):
                    continue  # não colide com o inimigo de origem
                bullets.remove(bullet)
                sounds.hit.play()
                enemy.hp -= bullet.power
                if freeze_level > 0:
                    enemy.frozen = freeze_duration
                if enemy.hp <= 0:
                    enemies.remove(enemy)
                    xp += 1
                    fib_up_to(xp + 1)
                    if xp == fib_seq[level]:
                        level += 1
                        paused = True
                        num_upgrades = 3 if random.random() < luck else 2
                        upgrade_options = random.sample(UPGRADES, num_upgrades)
                        spawn_upgrade_buttons()
                if bouncy_level > 0 and random.random() < bouncy_level * 0.1:
                    bounce(enemy)
                break


def shoot():
    if not enemies:
        return
    sounds.shot.play()
    target = max(enemies, key=lambda e: e.y)
    ex, ey = target.x, target.y
    vx = ex - player.x
    vy = ey - player.y
    dist = math.hypot(vx, vy)
    if dist == 0:
        return
    vx = vx / dist * bullet_speed
    vy = vy / dist * bullet_speed

    bullet = Actor("bullet")
    bullet.pos = player.pos
    bullet.vx = vx
    bullet.vy = vy
    bullet.power = bullet_power
    bullets.append(bullet)

    player.image = "player_shoot"


def bounce(enemy):
    others = [e for e in enemies if e != enemy]
    if not others:
        return
    target = min(others, key=lambda e: math.hypot(e.x - enemy.x, e.y - enemy.y))
    vx = target.x - enemy.x
    vy = target.y - enemy.y
    dist = math.hypot(vx, vy)
    if dist == 0:
        return
    vx = vx / dist * bullet_speed
    vy = vy / dist * bullet_speed
    b = Actor("bullet")
    b.pos = enemy.pos
    b.vx = vx
    b.vy = vy
    b.power = bullet_power * (1/3)
    b.ignore_enemy = enemy
    bullets.append(b)


def draw_game():
    screen.blit("bg", (0, 0))
    draw_wall_health_bar()
    player.draw()
    for bullet in bullets:
        bullet.draw()
    for enemy in enemies:
        enemy.draw()
        draw_enemy_hp(enemy)
    if paused:
        draw_upgrade_buttons()
    draw_debug_ui()


def animate_enemies(dt):
    for enemy in enemies:
        enemy.anim_timer -= dt
        if enemy.anim_timer <= 0:
            enemy.image_index = 1 - enemy.image_index  # Loop entre imagens
            enemy.image = enemy.images[enemy.image_index]
            enemy.anim_timer = (enemy.speed / 50)  # cooldown dos sprites


def draw_enemy_hp(enemy):
    bar_width = 30
    hp_ratio = enemy.hp / enemy.max_hp
    bar_x = enemy.x - bar_width / 2
    bar_y = enemy.y - 25
    screen.draw.filled_rect(Rect((bar_x, bar_y), (bar_width, 5)), "red")
    screen.draw.filled_rect(Rect((bar_x, bar_y), (bar_width * hp_ratio, 5)), "green")


def draw_wall_health_bar():
    bar_width = WIDTH
    bar_height = 100
    x = (WIDTH - bar_width) // 2
    y = HEIGHT - 80

    # fundo (vida máxima)
    screen.draw.filled_rect(Rect((x, y), (bar_width, bar_height)), "darkgray")

    # barra de vida atual
    current_width = int((wall_health / wall_max_health) * bar_width)
    screen.draw.filled_rect(Rect((x, y), (current_width, bar_height)), "lightgray")


def spawn_upgrade_buttons():
    global upgrade_buttons
    upgrade_buttons = []

    center_x = WIDTH // 2
    y = HEIGHT // 2

    if len(upgrade_options) == 2:
        # Dois botões, lado a lado
        for i, upgrade in enumerate(upgrade_options):
            btn_x = center_x - 150 + i * 160  # mesma lógica de antes
            btn_rect = Rect((btn_x, y), (140, 40))
            upgrade_buttons.append((btn_rect, upgrade))

    elif len(upgrade_options) == 3:
        # Dois botões na linha de cima
        for i in range(2):
            btn_x = center_x - 150 + i * 160
            btn_rect = Rect((btn_x, y), (140, 40))
            upgrade_buttons.append((btn_rect, upgrade_options[i]))

        # Terceiro botão centralizado abaixo
        btn_x = center_x - 70  # 140/2 para centralizar
        btn_y = y + 60  # espaço vertical entre as linhas
        btn_rect = Rect((btn_x, btn_y), (140, 40))
        upgrade_buttons.append((btn_rect, upgrade_options[2]))


def draw_upgrade_buttons():
    screen.draw.text("Escolha um upgrade:",
                     center=(WIDTH//2, HEIGHT//2 - 60), fontsize=40, color="white"
                     )

    for i, (rect, upgrade) in enumerate(upgrade_buttons):
        # Cor do botão
        if i == 2:  # terceiro botão (índice 2)
            color = "#cfbe8c"
        else:
            color = "gray"

        screen.draw.filled_rect(rect, color)
        screen.draw.text(upgrade["label"],
                         center=rect.center, fontsize=24, color="white")


def on_mouse_down(pos):
    global paused, show_menu

    if show_menu:
        for btn in menu_buttons:
            if btn["rect"].collidepoint(pos):
                if btn["action"] == "play":
                    show_menu = False
                    music.stop()
                    music.play("game")
                elif btn["action"] == "quit":
                    exit()
                elif btn["action"] == "toggle_sound":
                    toggle_sound()
    if paused:
        for rect, upgrade in upgrade_buttons:
            if rect.collidepoint(pos):
                upgrade["effect"]()
                paused = False
                return


def draw_debug_ui():
    screen.draw.text(f"XP: {xp} / {fib_seq[level]}",
                     topleft=(10, 10), fontsize=30, color="white")
    # screen.draw.text("DEBUG PANEL", topleft=(10, 50), fontsize=24)
    # screen.draw.text("1/2: cooldown +/-", topleft=(10, 80))
    # screen.draw.text("3/4: power +/-", topleft=(10, 100))
    # screen.draw.text("5/6: speed +/-", topleft=(10, 120))
    # screen.draw.text("7: freeze ++", topleft=(10, 140))
    # screen.draw.text("8: bounce ++", topleft=(10, 160))
    # screen.draw.text("9: multishot ++", topleft=(10, 180))
    # screen.draw.text("0: +xp", topleft=(10, 200))
    # screen.draw.text(f"Novo intervalo: {enemy_spawn_interval:.2f}s", topleft=(10, 220))


'''def on_key_down(key):
    global cooldown, bullet_power, bullet_speed, freeze_level, bouncy_level, multi_shot, luck, xp
    from pgzero.keyboard import keys
    if show_menu:
        return
    if key == keys.K_0:
        xp += 1
    if key == keys.K_1:
        cooldown *= 1.1
    elif key == keys.K_2:
        cooldown *= 0.9
    elif key == keys.K_3:
        bullet_power -= 1
    elif key == keys.K_4:
        bullet_power += 1
    elif key == keys.K_5:
        bullet_speed -= 20
    elif key == keys.K_6:
        bullet_speed += 20
    elif key == keys.K_7:
        freeze_level += 1
    elif key == keys.K_8:
        bouncy_level += 1
    elif key == keys.K_9:
        multi_shot += 1
'''
UPGRADES = [
    {"label": "+10% Vel. Ataque", "effect": lambda: increase("cooldown", -0.1)},
    {"label": "+10% Força", "effect": lambda: increase("bullet_power", 0.1)},
    {"label": "+10% Vel. Tiro", "effect": lambda: increase("bullet_speed", 0.1)},
    {"label": "Tiros Congelantes", "effect": lambda: increase("freeze_level", 1)},
    {"label": "+10% Ricochete", "effect": lambda: increase("bouncy_level", 1)},
    {"label": "+Tiros", "effect": lambda: increase("multi_shot", 1)},
    {"label": "+Sorte", "effect": lambda: increase("luck", 0.1)},
]


def increase(attr, percent_or_value):
    global cooldown, bullet_power, bullet_speed, freeze_duration, freeze_level, bouncy_level, multi_shot, luck
    if attr == "cooldown":
        cooldown *= 1 + percent_or_value
    elif attr == "bullet_power":
        bullet_power *= 1 + percent_or_value
    elif attr == "bullet_speed":
        bullet_speed *= 1 + percent_or_value
    elif attr == "freeze_level":
        freeze_level += percent_or_value
        freeze_duration *= 1.333
    elif attr == "bouncy_level":
        bouncy_level += percent_or_value
    elif attr == "multi_shot":
        multi_shot += percent_or_value
    elif attr == "luck":
        luck += percent_or_value


def reduce_spawn_interval():
    global enemy_spawn_interval
    enemy_spawn_interval *= 0.95  # reduz 5%
    enemy_spawn_interval = max(enemy_spawn_interval, MIN_SPAWN_INTERVAL)
    clock.unschedule(spawn_enemy)
    clock.schedule_interval(spawn_enemy, enemy_spawn_interval)
    print(f"Novo intervalo: {enemy_spawn_interval:.2f}s")


pgzrun.go()
