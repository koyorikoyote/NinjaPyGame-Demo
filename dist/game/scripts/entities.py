import pygame
import math
import random

from scripts.particle import Particle
from scripts.spark import Spark

class PhysicsEntity:
    def __init__(self, game, e_type, pos, size):
        self.game = game
        self.type = e_type
        self.pos = list(pos)
        self.size = size
        self.velocity = [0, 0]
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}
        # Animation. Offset accounts for border padding with rendering changing player image sizes between animations 
        self.action = ''
        self.anim_offset = (-3, -3)
        self.flip = False
        self.set_action('idle')
        # Keep track of last input movement
        self.last_movement = [0, 0]

    def rect(self):
        # Note: Rects only accept/rounds to integer dimensions so it is not accurate for representing player movement in pixels for collision, so use pos variable instead
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

    def set_action(self, action):
        # Only if action has changed, update action and animation
        if action != self.action:
            self.action = action
            self.animation = self.game.assets[self.type + '/' + self.action].copy()

    def update(self, tilemap, movement=(0, 0)):
        # Keeping track of collisions to remember player velocity, and resets every frame
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}

        frame_movement = (movement[0] + self.velocity[0], movement[1] + self.velocity[1])
        # Update player X position
        self.pos[0] += frame_movement[0]
        # Collision checking with tilemap for physics in X axis
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                # If player is moving right, snap player's rect position right edge back to the collided tile's left edge
                if frame_movement[0] > 0:
                    entity_rect.right = rect.left
                    self.collisions['right'] = True
                if frame_movement[0] < 0:
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                # Update player position to player rect position
                self.pos[0] = entity_rect.x

        # Update player Y position
        self.pos[1] += frame_movement[1]
        # Collision checking with tilemap for physics in Y axis
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                # If player is moving right, snap player's rect position right edge back to the collided tile's left edge
                if frame_movement[1] > 0:
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                if frame_movement[1] < 0:
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
                # Update player position to player rect position
                self.pos[1] = entity_rect.y
        # Flip animation image depending on player input movement direction. Flip true to show player facing left. Flip false means player faces right.
        if movement[0] > 0:
            self.flip = False
        if movement[0] < 0:
            self.flip = True

        self.last_movement = movement

        # Apply gravity by change in velocity, and capped at terminal velocity
        self.velocity[1] = min(5, self.velocity[1] + 0.1)
        # Keep velocity in Y axis at 0 if not falling
        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0

        self.animation.update()

    def render(self, surf, offset=(0, 0)):
        # Whether to flip image before rendering: (the image, flip on X axis?, flip on Y axis?) , (Player position with Camera and Anim Offsets)
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False), (self.pos[0] - offset[0] + self.anim_offset[0], self.pos[1] - offset[1] + self.anim_offset[1]))
        #surf.blit(self.game.assets['player'], (self.pos[0] - offset[0], self.pos[1] - offset[1]))

# Spawning and Animating Enemies. Walks and patrols but does not walk off edge, turns around at edge. Shoots horizontally at player.
class Enemy(PhysicsEntity):
    def __init__(self, game, pos, size):
        super().__init__(game, 'enemy', pos, size)

        self.walking = 0

    def update(self, tilemap, movement=(0, 0)):
        if self.walking:
            # Scans out in facing direction 7 pixels horizontally and 23 pixels down in ground. Checks if physics tile exists or whether it is a ledge.
            if tilemap.solid_check((self.rect().centerx + (-7 if self.flip else 7), self.pos[1] + 23)):
                # Check if there is a wall blocking the way, flip entity around if it is.
                if (self.collisions['right'] or self.collisions['left']):
                    self.flip = not self.flip
                else:
                    # If flipped direction, subtract 0.5 from X movement input, else set to 0.5. Keep Y same.
                    movement = (movement[0] - 0.5 if self.flip else 0.5, movement[1])
            # If physics tile was not found, flip entity around.
            else:
                self.flip = not self.flip
            self.walking = max(0, self.walking - 1)     # Normalizes walking timer down to 0 over time
            # When done walking once, shoots projectile
            if not self.walking:
                # Distance between enemy and player position
                dis = (self.game.player.pos[0] - self.pos[0], self.game.player.pos[1] - self.pos[1])
                if (abs(dis[1]) < 16 and abs(dis[0]) < 180):
                    # If looking left and player is on the left side
                    if (self.flip and dis[0] < 0):
                        self.game.sfx['shoot'].play()
                        self.game.projectiles.append([[self.rect().centerx - 7, self.rect().centery], -1.5, 0])
                        # Spawn sparks to the left when shooting projectile from gun
                        for i in range(4):
                            self.game.sparks.append(Spark(self.game.projectiles[-1][0], random.random() - 0.5 + math.pi, 2 + random.random()))
                    # If looking right and player is on the right side
                    if (not self.flip and dis[0] > 0):
                        self.game.projectiles.append([[self.rect().centerx + 7, self.rect().centery], 1.5, 0])    
                        # Spawn sparks to the right when shooting projectile from gun
                        for i in range(4):
                            self.game.sparks.append(Spark(self.game.projectiles[-1][0], random.random() - 0.5, 2 + random.random()))    
        elif random.random() < 0.01:
            # If not walking, have a random small delay then set walking timer to random time between 30 to 120 msec. 
            self.walking = random.randint(30, 120)

        super().update(tilemap, movement=movement)

        if movement[0] != 0:
            self.set_action('run')
        else:
            self.set_action('idle')

        # If player collides with enemy while dashing, kill enemy. Else if player collides with enemy, kill player and restart map.   
        if self.rect().colliderect(self.game.player.rect()) and not self.game.dead:
            self.game.screenshake = max(16, self.game.screenshake)
            self.game.sfx['hit'].play()
            for i in range(30):
                angle = random.random() * math.pi * 2
                speed = random.random() * 5
                self.game.sparks.append(Spark(self.rect().center, angle, 2 + random.random()))
                self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0, 7)))
            if abs(self.game.player.dashing) >= 50:    
                # Show two big sparks each to the left and right
                self.game.sparks.append(Spark(self.rect().center, 0, 3.5 + random.random()))
                self.game.sparks.append(Spark(self.rect().center, math.pi, 3.5 + random.random()))
                return True
            else:
                self.game.dead += 1

    def render(self, surf, offset=(0, 0)):
        super().render(surf, offset=offset)

        if self.flip:
            surf.blit(pygame.transform.flip(self.game.assets['gun'], True, False), (self.rect().centerx - 4 - self.game.assets['gun'].get_width() - offset[0], self.rect().centery - offset[1]))
        else:
            surf.blit(self.game.assets['gun'], (self.rect().centerx + 4 - offset[0], self.rect().centery - offset[1]))

# Animating Player entity (inherits from PhysicsEntity)
class Player(PhysicsEntity):
    def __init__(self, game, pos, size):
        super().__init__(game, 'player', pos, size)
        self.air_time = 0
        self.jumps = 1
        self.wall_slide = False
        self.dashing = 0

    # What to update every frame
    def update(self, tilemap, movement=(0, 0)):
        super().update(tilemap, movement=movement)

        # If player not on ground
        self.air_time += 1

        #Alternative method to restart map if player falls off edge based on air time
        #if self.air_time > 120:
        #    self.game.dead += 1

        # When in contact with ground
        if self.collisions['down']:
            self.air_time = 0
            self.jumps = 1
        
        self.wall_slide = False
        if (self.collisions['right'] or self.collisions['left']) and self.air_time > 4:
            self.wall_slide = True
            # Cap the downward velocity to 0.5
            self.velocity[1] = min(self.velocity[1], 0.5)
            if self.collisions['right']:
                self.flip = False
            else:
                self.flip = True
            self.set_action('wall_slide')

        # When in the air (or else on ground) and not sliding on a wall
        if not self.wall_slide:
            if self.air_time > 4:
                self.set_action('jump')
                self.jumps = 0
            elif movement[0] != 0:
                self.set_action('run')
            else:
                self.set_action('idle')

        # If at start or end of the dash
        if abs(self.dashing) in {60, 50}:
            # For 20 times do
            for i in range(20):
                # Show a burst explosion of random outward particles at the start and end of a player's dash
                angle = random.random() * math.pi * 2   # Pick a random angle within Full circle angle in radians for particle direction
                speed = random.random() * 0.5 + 0.5     # Pick a random value from 0.5 to 1
                pvelocity = [math.cos(angle) * speed, math.sin(angle) * speed]      # Generate velocity from angle using trigonometry. Moves particles outward in natural circular pattern
                self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=pvelocity, frame=random.randint(0, 7)))
        # Stop Dash velocity from going below 0 after subtracting to normalize it to 0
        if self.dashing > 0:
            self.dashing = max(0, self.dashing - 1)
        # Limit opposite direction dash velocity to normalize it to 0
        if self.dashing < 0:
            self.dashing = min(0, self.dashing + 1)
        # If within first ten frames of the dash, extract the normalized dash direction (1 or -1) multiplied by a Multiplier as a movement speed to increase dash distance
        # 50 frames will be the cooldown period before dash attack is available to use again
        if abs(self.dashing) > 50:
            self.velocity[0] = abs(self.dashing) / self.dashing * 6
            # At the last of ten frames, slow down the velocity abruptly to show player has ended the dash attack
            if abs(self.dashing) == 51:
                self.velocity[0] *= 0.1
            # Show a stream of particles trailing behind when player is dashing
            # Random particle velocity's X-magnitude in the direction player is dashing
            pvelocity = [abs(self.dashing) / self.dashing * random.random() * 3, 0]
            self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=pvelocity, frame=random.randint(0, 7)))

        # Normalize all velocities to 0 automatically
        if self.velocity[0] > 0:
            # Stop velocity from going below 0 after subtracting to normalize it to 0
            self.velocity[0] = max(self.velocity[0] - 0.1, 0)
        else:
            # Stop velocity from going above 0 after adding to normalize it to 0
            self.velocity[0] = min(self.velocity[0] + 0.1, 0)

    # Override parent's render function
    def render(self, surf, offset=(0, 0)):
        # Only render player when dash on cooldown/ready to use. Makes player invisible for the 10 frames when dashing.
        if abs(self.dashing) <= 50:
            super().render(surf, offset=offset)

    def jump(self):
        if self.wall_slide:
            # If facing left and input moving left
            if self.flip and self.last_movement[0] < 0:
                self.velocity[0] = 2.5
                self.velocity[1] = -3
                self.air_time = 5
                # Stop remaining jumps from going below 0
                self.jumps = max(0, self.jumps - 1)
                return True
            elif not self.flip and self.last_movement[0] > 0:
                self.velocity[0] = -2.5
                self.velocity[1] = -3
                self.air_time = 5
                self.jumps = max(0, self.jumps - 1)
                return True
        elif self.jumps:
            self.velocity[1] = -3
            self.jumps -= 1
            self.air_time = 5
            return True

    # Dash attack against enemies to go through and kill them
    def dash(self):
        # Tracks how much in velocity to dash and in which direction on X axis
        if not self.dashing:
            self.game.sfx['dash'].play()
            if self.flip:
                self.dashing = -60
            else:
                self.dashing = 60