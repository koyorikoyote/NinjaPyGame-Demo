import os
import sys
import math
import random
import pygame
from scripts.utils import load_image, load_images, Animation
from scripts.entities import PhysicsEntity, Player, Enemy
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark

class Game:
    def __init__(self):
        pygame.init()
        # Change window title
        pygame.display.set_caption('Ninja Game')
        # Create a window
        self.screen = pygame.display.set_mode((640, 480))
        # Create the display within the window. For outline shadows on foreground render onto first display, for backgrounds render onto second display.
        self.display = pygame.Surface((320, 240), pygame.SRCALPHA)
        self.display_2 = pygame.Surface((320, 240))

        # Restrict at 60 fps runtime to avoid over-processing
        self.clock = pygame.time.Clock()

        # # Load images into memory
        # self.img = pygame.image.load('data/images/clouds/cloud_1.png')
        # # Colorkey to match background color in image and display this color as transparent
        # self.img.set_colorkey((0, 0, 0))
        # self.img_pos = [160, 260]

        self.movement = [False, False]
        # Graphical Images
        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'player': load_image('entities/player.png'),
            'background': load_image('background.png'),
            'clouds': load_images('clouds'),
            'enemy/idle': Animation(load_images('entities/enemy/idle'), img_dur=6),
            'enemy/run': Animation(load_images('entities/enemy/run'), img_dur=4),
            'player/idle': Animation(load_images('entities/player/idle'), img_dur=6),
            'player/run': Animation(load_images('entities/player/run'), img_dur=4),
            'player/jump': Animation(load_images('entities/player/jump')),
            'player/slide': Animation(load_images('entities/player/slide')),
            'player/wall_slide': Animation(load_images('entities/player/wall_slide')),
            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'gun': load_image('gun.png'),
            'projectile': load_image('projectile.png')
        }
        # Sound Effects and Music
        self.sfx = {
            'jump': pygame.mixer.Sound('data/sfx/jump.wav'),
            'dash': pygame.mixer.Sound('data/sfx/dash.wav'),
            'hit': pygame.mixer.Sound('data/sfx/hit.wav'),
            'shoot': pygame.mixer.Sound('data/sfx/shoot.wav'),
            'ambience': pygame.mixer.Sound('data/sfx/ambience.wav')
        }
        self.sfx['jump'].set_volume(0.2)
        self.sfx['dash'].set_volume(0.2)
        self.sfx['hit'].set_volume(0.2)
        self.sfx['shoot'].set_volume(0.2)
        self.sfx['ambience'].set_volume(0.1)

        #print(self.assets)
        # self.collision_area = pygame.Rect(50, 50, 300, 50)       
        self.clouds = Clouds(self.assets['clouds'], count=6)

        self.player = Player(self, (50, 50), (8, 15))

        self.tilemap = Tilemap(self, tile_size=16)

        self.map = 0
        self.load_map(self.map)

        self.screenshake = 0   

    def load_map(self, map_id=0):
        self.tilemap.load('data/maps/' + str(map_id) + '.json')

        # Spawn leaf particles falling from Trees
        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            # Append an offsetted hitbox based on illustrated area of the Tree tile
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))

        # Get spawn locations for Enemies
        self.enemies = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
            else:
                self.enemies.append(Enemy(self, spawner['pos'], (8, 15)))
        
        self.projectiles = []
        self.particles = []
        self.sparks = []

        # Camera implementation
        self.scroll = [0, 0]
        # Reset player death delay timer
        self.dead = 0
        # When transition counter is -30, a Black screen is shown for map level transition
        self.transition = -30

    def run(self):
        # Play game music and ambience sfx on infinite loop
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.2)
        pygame.mixer.music.play(-1)
        self.sfx['ambience'].play(-1)

        # Create the game loop for each frame iteration
        while True:
            # Clear screen between each frame with a screen color of RGB values. Make a transparent foreground display.
            self.display.fill((0, 0, 0, 0))
            self.display_2.blit(self.assets['background'], (0, 0))
            #self.display.fill((14, 219, 248))

            self.screenshake = max(0, self.screenshake - 1)

            # Transition to next map if all enemies are killed
            if not len(self.enemies):
                self.transition += 1
                if self.transition > 30:
                    self.map = min(self.map + 1, len(os.listdir('data/maps')) - 1)
                    self.load_map(self.map)
            # When transition counter is 0, screen is shown
            if self.transition < 0:
                self.transition += 1

            # After Player Death delay timer
            if self.dead:
                self.dead += 1
                # Transition screen effect when dead
                if self.dead >= 10:
                    self.transition = min(30, self.transition + 1)
                # Restart map after some time when dead
                if self.dead > 40:
                    self.load_map(self.map)
            else:
                # If player falls off map edge, set player death and restart map
                if abs(self.player.rect().centery) >= self.display.get_height() * 2.5:
                    self.dead += 1

            # Center camera onto player entity
            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 30
            # Smooth the scrolling without subpixel render jitters by converting scroll values from player position from float to int
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            # Look for Leaf particle spawners
            for rect in self.leaf_spawners:
                # Multiplier controls how seldom Leaves should spawn. Spawns more Leaves proportional to size of Tree image.
                if random.random() * 49999 < rect.width * rect.height:
                    # Find some random xy position within the size bounds of the Rect hitbox
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    # Spawn a leaf particle at the given position at a constant velocity (slowly moving left and down). Start from random frame between 0-20 incl for diversity effect
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

            self.clouds.update()
            self.clouds.render(self.display_2, offset=render_scroll)

            self.tilemap.render(self.display, offset=render_scroll)
               
            # # Collision handling
            # img_r = pygame.Rect(self.img_pos[0], self.img_pos[1], self.img.get_width(), self.img.get_height())
            # if img_r.colliderect(self.collision_area):
            #     pygame.draw.rect(self.screen, (0, 100, 255), self.collision_area)
            # else:
            #     pygame.draw.rect(self.screen, (0, 50, 155), self.collision_area)
            # # Move image based on keypress
            # self.img_pos[1] += (self.movement[1] - self.movement[0]) * 5
            # # Put images on screen at coordinate x, y starting from topleft
            # self.screen.blit(self.img, self.img_pos)

            # Render Enemies
            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0, 0))
                enemy.render(self.display, offset=render_scroll)
                if kill:
                    self.enemies.remove(enemy)

            # Render Player
            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

            # Render Projectiles. Projectile list = [[x, y], direction, timer]
            for projectile in self.projectiles.copy():
                projectile[0][0] += projectile[1]
                projectile[2] += 1
                img = self.assets['projectile']
                self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
                # Remove projectile if it hits a physics tile
                if self.tilemap.solid_check(projectile[0]):
                    self.projectiles.remove(projectile)
                    for i in range(4):
                        # Bounce sparks to the left only if projectile is going right and hits a wall
                        self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                elif projectile[2] > 360:
                    self.projectiles.remove(projectile)
                elif abs(self.player.dashing) < 50:
                    # Player death if player is not dashing and player hitbox collides with gun projectile
                    if self.player.rect().collidepoint(projectile[0]):
                        self.projectiles.remove(projectile)
                        self.dead += 1
                        self.sfx['hit'].play()
                        self.screenshake = max(16, self.screenshake)
                        # White Sparks and Black particles explode outward when hit player
                        for i in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0, 7)))

            # Spark effects
            for spark in self.sparks.copy():
                kill = spark.update()
                spark.render(self.display_2, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)

            # Shadow silhouette outlines using mask from the display
            display_mask = pygame.mask.from_surface(self.display)
            display_silhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
            # Shadow positional transformation enlarge one pixel in each of four directions
            for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                self.display_2.blit(display_silhouette, offset)

            # Check if need to remove particle after animation finishes
            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                if particle.type == 'leaf':
                    # Sine function to smooth values limited between -1 and 1. Makes particle move wavelike naturally (e.g. sway left/right as leaf falls), slowed by a multiplier.
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3
                if kill:
                    self.particles.remove(particle)

            # Get user input
            for event in pygame.event.get():
                # Clicking X to close window
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                # On Keypress event
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.movement[0] = True
                    if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_UP or event.key == pygame.K_w or event.key == pygame.K_SPACE:
                        if self.player.jump():
                            self.sfx['jump'].play()
                    if event.key == pygame.K_e:
                        self.player.dash()
                # On Keypress release event
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.movement[1] = False
            
            if self.transition:
                transition_surf = pygame.Surface(self.display.get_size())
                # Draw a zooming in and out circle mask around screen during map level transitions
                pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width() // 2, self.display.get_height() // 2), (30 - abs(self.transition)) * 8)
                # Ignore the white color and make it transparent
                transition_surf.set_colorkey((255, 255, 255))
                self.display.blit(transition_surf, (0, 0))

            self.display_2.blit(self.display, (0, 0))

            screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
            # Render the display onto the window
            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), screenshake_offset)
            # Update the display
            pygame.display.update()
            # Force at 60 fps
            self.clock.tick(60)

Game().run()

