from audioop import cross

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()

#Floor
ground = Entity(model = 'plane', scale = 100, texture = 'white_cube', texture_scale = (100, 100), collider = 'box')

#Sky
Sky()

#Players
player = FirstPersonController(model = 'cube', color = color.orange, speed = 5)
player.gravity = 0.5

#Aiming
mouse.visible = False

#Target
crosshiar = Entity(
    parent = camera.ui,
    model = 'quad',
    color = color.black,
    scale = 0.008,
    position= (0,0)
)

#Gun
gun = Entity(
    parent = camera,
    model = 'assets/gun.glb',
    scale = 0.4,
    position = (0.65, -0.5, 1),
    rotation = (-90, 90, 11),
    collider = None
)

app.run()
