from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random

app = Ursina()

bullets = []
enemies = []
shoot_cooldown = 0.2
time_since_last_shot = 999
MAX_ENEMIES = 3

crosshair = Entity(
    parent=camera.ui,
    model='quad',
    color=color.black,
    scale=0.008,
    position=(0, 0)
)

gun = Entity(
    parent=camera,
    model='assets/gun.glb',
    scale=0.4,
    position=(0.6, -0.55, 1),
    rotation=(0, 190, 2),
    collider=None
)

muzzle_flash = Entity(
    parent=gun,
    model='quad',
    texture='MuzzleFlash.png',
    color=color.white,
    scale=0.1,
    position=(0.660, 1.010, 0.500),
    rotation=(0, 78, 0),
    enabled=False,
    billboard=True
)

gun_sound = Audio('gunshot.wav', loop=False, autoplay=False)

def input(key):
    if key == 'left mouse down':
        muzzle_flash.enabled = True
        gun_sound.play()
    elif key == 'left mouse up':
        muzzle_flash.enabled = False


def shoot():
    bullet = Entity(
        model='cube',
        color=color.yellow,
        scale=(0.5, 0.01, 0.01),
        position=muzzle_flash.world_position - camera.forward * 0.1,
        rotation=muzzle_flash.world_rotation,
        collider='box'
    )

    bullet.animate_position(bullet.position + camera.forward * 10, duration=1, curve=curve.linear)
    destroy(bullet, delay=1)
    bullets.append(bullet)

def random_position_outside_hospital(max_attempts=100):
    for _ in range(max_attempts):
        x = random.uniform(-40, 40)
        z = random.uniform(-40, 40)

        if hospital_bounds['x_min'] < x < hospital_bounds['x_max'] and \
           hospital_bounds['z_min'] < z < hospital_bounds['z_max']:
            continue

        test_entity = Entity(position=(x, 0.1, z), scale=0.5, collider='box', visible=False)
        hit_info = test_entity.intersects()
        destroy(test_entity)

        if not hit_info.hit:
            return (x, 0.1, z)

    return (20, 0.1, 20)


hospital_bounds = {
    'x_min': -10,
    'x_max': 10,
    'z_min': -10,
    'z_max': 10,
}

def spawn_enemy():
    pos = random_position_outside_hospital()
    enemy = Entity(
        model='assets/zombie.glb',
        scale=0.02,
        position=pos,
        collider='mesh',
    )
    enemy.speed = 2.0

    def move():
        direction_to_player = (player.position - enemy.position).normalized()
        target_pos = enemy.position + direction_to_player * time.dt * enemy.speed
        hit_info = raycast(
            origin=enemy.position,
            direction=direction_to_player,
            distance=0.3,
            ignore=[enemy]
        )
        if not hit_info.hit:
            enemy.position = target_pos
        else:
             enemy.position += Vec3(random.uniform(-1, 1), 0, random.uniform(-1, 1)).normalized() * time.dt * enemy.speed

    enemy.update = move
    enemies.append(enemy)

def generate_enemies_forever():
    if len(enemies) < MAX_ENEMIES:
        spawn_enemy()
    invoke(generate_enemies_forever, delay=2)

def update():
    global time_since_last_shot
    time_since_last_shot += time.dt
    if held_keys['left mouse']:
        muzzle_flash.enabled = True
        if time_since_last_shot >= shoot_cooldown:
            gun_sound.play()
            shoot()
            time_since_last_shot = 0
    else:
        muzzle_flash.enabled = False

    for bullet in bullets.copy():
        for enemy in enemies.copy():
            if bullet.intersects(enemy).hit:
                destroy(enemy)
                destroy(bullet)
                enemies.remove(enemy)
                bullets.remove(bullet)
                break

mouse.visible = False

hospital_scene = Entity(
    model='zombie_hospital.glb',
    scale=0.5,
    position=(0, 0.02, 0),
    rotation=(0, 0, 0),
    collider='mesh'
)

ground = Entity(model='plane', scale=100, texture='white_cube', texture_scale=(100, 100), collider='box')
Sky()
player = FirstPersonController(model='cube', color=color.clear, speed=5, position=(0, 1, -25))
player.gravity = 0.5
player.rotation_y = 0
camera.fov = 90

generate_enemies_forever()

app.run()
