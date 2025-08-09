
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random, math, time as pytime

app = Ursina()

# ---------------- Global state ----------------
bullets = []
enemies = []
shoot_cooldown = 0.12
time_since_last_shot = 999
MAX_ENEMIES = 3

game_over = False
kills = 0

# ---------------- UI ----------------
kill_text = Text(text=f'Kills: {kills}', parent=camera.ui,
                 origin=(-.5, .5), position=(-.87, .47), scale=1, color=color.white)

death_text = Text(text='You died', parent=camera.ui, origin=(0, 0),
                  position=(0, 0), scale=2, color=color.red, enabled=False)

crosshair = Entity(parent=camera.ui, model='quad', color=color.black, scale=0.008, position=(0, 0))

# ---------------- Weapon ----------------
gun = Entity(parent=camera, model='assets/gun.glb', scale=0.4, position=(0.6, -0.55, 1),
             rotation=(0, 190, 2), collider=None)

muzzle_flash = Entity(parent=gun, model='quad', texture='MuzzleFlash.png', color=color.white,
                      scale=0.1, position=(0.660, 1.010, 0.500), rotation=(0, 78, 0),
                      enabled=False, billboard=True)

gun_sound = Audio('gunshot.wav', loop=False, autoplay=False)

# ---------------- Areas ----------------
hospital_bounds = {'x_min': -10, 'x_max': 10, 'z_min': -10, 'z_max': 10}

def in_hospital_rect(x, z):
    return (hospital_bounds['x_min'] < x < hospital_bounds['x_max']
            and hospital_bounds['z_min'] < z < hospital_bounds['z_max'])

# ---------------- Input ----------------
def input(key):
    if key == 'escape':
        application.quit()
        return
    if game_over:
        return
    if key == 'left mouse down':
        muzzle_flash.enabled = True
        gun_sound.play()
    elif key == 'left mouse up':
        muzzle_flash.enabled = False

# ---------------- Bullet ----------------
class Bullet(Entity):
    def __init__(self, origin: Vec3, direction: Vec3, **kwargs):
        super().__init__(
            model='cube',
            color=color.yellow,
            scale=(0.1, 0.1, 0.5),
            position=origin,
            collider='box',
            **kwargs
        )
        self.dir = direction.normalized()
        self.speed = 36
        self.life = 1.2
        self._age = 0

    def _kill_enemy(self, enemy_root: Entity):
        destroy(enemy_root)
        if enemy_root in enemies:
            enemies.remove(enemy_root)
        global kills
        kills += 1
        kill_text.text = f'Kills: {kills}'
        destroy(self)

    def update(self):
        if game_over:
            destroy(self); return

        dt = time.dt
        start = self.world_position
        move_vec = self.dir * self.speed * dt
        dist = move_vec.length()

        # 1) Raycast along the bullet path for this frame (no tunnelling)
        ignore_list = [player, self, gun, muzzle_flash, ground, hospital_scene]
        hit = raycast(start, self.dir, distance=dist, ignore=ignore_list)

        if hit.hit:
            ent = hit.entity
            # Hit either the enemy root (is_enemy) or the visual child (whose parent is_enemy)
            if getattr(ent, 'is_enemy', False) or getattr(getattr(ent, 'parent', None), 'is_enemy', False):
                enemy_root = ent if getattr(ent, 'is_enemy', False) else ent.parent
                self._kill_enemy(enemy_root)
                return

        # 2) Advance the bullet
        self.position += move_vec

        # 3) Safety net: box–box overlap vs each enemy root (has BoxCollider)
        for enemy in enemies.copy():
            if self.intersects(enemy).hit:
                self._kill_enemy(enemy)
                return

        # 4) Lifetime
        self._age += dt
        if self._age >= self.life:
            destroy(self)

def shoot():
    if game_over:
        return
    origin = muzzle_flash.world_position - camera.forward * 0.05
    direction = camera.forward
    b = Bullet(origin=origin, direction=direction)
    bullets.append(b)

# ---------------- Spawning ----------------
def pick_spawn_pos():
    """Random ring around hospital; keep distance from player."""
    for _ in range(120):
        angle = random.uniform(0, 2*math.pi)
        r = random.uniform(22, 40)
        x = math.cos(angle) * r
        z = math.sin(angle) * r
        if in_hospital_rect(x, z):
            continue
        if distance_2d(Vec3(x, 0, z), player.position) < 15:
            continue
        return Vec3(x, 0.1, z)
    return Vec3(26, 0.1, 26)

def spawn_enemy():
    """Create an enemy root with a BoxCollider (not scaled),
    and attach the visual glb model as a child (scaled 0.02)."""
    pos = pick_spawn_pos()

    # Root: holds the collider and AI (keep scale=1)
    enemy = Entity(position=pos, collider='box')
    enemy.is_enemy = True
    enemy.spawned_at = pytime.time()

    # Give the root a human-sized box collider (height ~1.8, centred at chest)
    from ursina import BoxCollider
    enemy.collider = BoxCollider(enemy, center=Vec3(0, 0.9, 0), size=Vec3(0.6, 1.8, 0.6))

    # Visual model as a child (scaled), does not affect collider
    Entity(parent=enemy, model='assets/zombie.glb', scale=0.02, position=Vec3(0, 0, 0))

    enemy.speed = 2.0

    def move():
        if game_over:
            return
        direction_to_player = (player.position - enemy.position).normalized()
        target_pos = enemy.position + direction_to_player * time.dt * enemy.speed

        # Simple obstacle avoidance
        hit_info = raycast(origin=enemy.position + Vec3(0, 0.5, 0),
                           direction=direction_to_player,
                           distance=0.6,
                           ignore=[enemy, player])
        if not hit_info.hit:
            enemy.position = target_pos
        else:
            enemy.position += Vec3(random.uniform(-1, 1), 0, random.uniform(-1, 1)).normalized() * time.dt * enemy.speed

    enemy.update = move
    enemies.append(enemy)

def generate_enemies_forever():
    if not game_over and len(enemies) < MAX_ENEMIES:
        spawn_enemy()
    invoke(generate_enemies_forever, delay=2)

# ---------------- Death handling ----------------
def trigger_game_over():
    global game_over
    if game_over:
        return
    game_over = True
    death_text.enabled = True
    muzzle_flash.enabled = False
    mouse.visible = True

SPAWN_PROTECT = 0.50  # seconds after spawn where enemy cannot cause death

def enemy_touching_player(enemy_root: Entity) -> bool:
    if (pytime.time() - enemy_root.spawned_at) < SPAWN_PROTECT:
        return False
    # Player (FirstPersonController) has a box collider; enemy_root has a BoxCollider
    return player.intersects(enemy_root).hit

# ---------------- Main update ----------------
def update():
    global time_since_last_shot
    if game_over:
        return

    time_since_last_shot += time.dt
    if held_keys['left mouse']:
        muzzle_flash.enabled = True
        if time_since_last_shot >= shoot_cooldown:
            gun_sound.play()
            shoot()
            time_since_last_shot = 0
    else:
        muzzle_flash.enabled = False

    # Death check: close contact between colliders
    for enemy in enemies:
        if enemy_touching_player(enemy):
            trigger_game_over()
            break

# ---------------- World ----------------
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

# Player
player = FirstPersonController(model='cube', color=color.clear, speed=5, position=(0, 1, -25))
player.collider = 'box'      # ensure a simple box collider
player.gravity = 0.5
player.rotation_y = 0
camera.fov = 90

# ---------------- Go ----------------
generate_enemies_forever()
app.run()
