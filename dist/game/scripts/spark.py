import math
import pygame

class Spark:
    def __init__(self, pos, angle, speed):
        # Cartesian coordinates position for rendering
        self.pos = list(pos)
        # Angle and Speed for Polar coordinates of velocity vector
        self.angle = angle
        self.speed = speed
    
    def update(self):
        self.pos[0] += math.cos(self.angle) * self.speed
        self.pos[1] += math.sin(self.angle) * self.speed

        self.speed = max(0, self.speed - 0.1)
        # Return True if speed reduced to 0 which will remove the spark from list
        return not self.speed

    def render(self, surf, offset=(0, 0)):
        # Render a diamond shaped spark
        render_points = [
            # Cast out a vector point towards the front
            (self.pos[0] + math.cos(self.angle) * self.speed * 3 - offset[0], self.pos[1] + math.sin(self.angle) * self.speed * 3 - offset[1]),
            # Cast out a vector point towards the left
            (self.pos[0] + math.cos(self.angle + math.pi * 0.5) * self.speed * 0.5 - offset[0], self.pos[1] + math.sin(self.angle + math.pi * 0.5) * self.speed * 0.5 - offset[1]),
            # Cast out a vector point towards the back
            (self.pos[0] + math.cos(self.angle + math.pi) * self.speed * 3 - offset[0], self.pos[1] + math.sin(self.angle + math.pi) * self.speed * 3 - offset[1]),
            # Cast out a vector point towards the right
            (self.pos[0] + math.cos(self.angle - math.pi * 0.5) * self.speed * 0.5 - offset[0], self.pos[1] + math.sin(self.angle - math.pi * 0.5) * self.speed * 0.5 - offset[1])
        ]

        pygame.draw.polygon(surf, (255, 255, 255), render_points)