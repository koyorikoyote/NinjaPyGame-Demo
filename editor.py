import sys
import pygame
from scripts.utils import load_images
from scripts.tilemap import Tilemap

RENDER_SCALE = 2.0

class Editor:
    def __init__(self):
        pygame.init()
        # Change window title
        pygame.display.set_caption('Level Editor')
        # Create a window
        self.screen = pygame.display.set_mode((640, 480))
        # Create the display within the window
        self.display = pygame.Surface((320, 240))
        # Restrict at 60 fps runtime to avoid over-processing
        self.clock = pygame.time.Clock()

        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'spawners': load_images('tiles/spawners')
        }
        self.movement = [False, False, False, False]

        self.tilemap = Tilemap(self, tile_size=16)

        try:
            self.tilemap.load('map.json')
        except FileNotFoundError:
            pass

        # Camera implementation
        self.scroll = [0, 0]

        # Editor Tile control variables
        self.tile_list = list(self.assets)
        self.tile_group = 0
        self.tile_variant = 0
        self.clicking = False
        self.right_clicking = False
        self.shift = False
        self.ongrid = True

    def run(self):
        # Create the game loop for each frame iteration
        while True:
            # Clear screen between each frame with a screen color of RGB values
            self.display.fill((0, 0, 0))

            # Moving Camera, multiplied by 2 to make it faster
            # Holding Right minus Left
            self.scroll[0] += (self.movement[1] - self.movement[0]) * 2
            # Holding Down minus Up
            self.scroll[1] += (self.movement[3] - self.movement[2]) * 2

            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))
            self.tilemap.render(self.display, offset=render_scroll)

            # Current Tile control in Editor, which tile to use, and copy it to set alpha value
            current_tile_img = self.assets[self.tile_list[self.tile_group]][self.tile_variant].copy()
            # Tile image transparency 0-255 opaque
            current_tile_img.set_alpha(100)

            # Pixel coordinates of Mouse with respect to window. Topleft= 0,0
            mpos = pygame.mouse.get_pos()
            # Scale down mouse position to get correct coordinates
            mpos = (mpos[0] / RENDER_SCALE, mpos[1] / RENDER_SCALE)
            # Coordinates of mouse in tile system
            tile_pos = (int((mpos[0] + self.scroll[0]) // self.tilemap.tile_size), int((mpos[1] + self.scroll[1]) // self.tilemap.tile_size))

            if self.ongrid:
                # Show where next tile would be placed under cursor, converted back into pixel coordinates by multiplying by tile size, adjusted based on camera position for rendering
                self.display.blit(current_tile_img, (tile_pos[0] * self.tilemap.tile_size - self.scroll[0], tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
            else:
                self.display.blit(current_tile_img, mpos)

            # Placing tiles on cursor mouse up
            if self.clicking and self.ongrid:
                # Convert index selection into string name for the group
                self.tilemap.tilemap[str(tile_pos[0]) + ';' + str(tile_pos[1])] = {'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': tile_pos}
            # Deleting tiles on right mouse down
            if self.right_clicking:
                tile_loc = str(tile_pos[0]) + ';' + str(tile_pos[1])
                # Delete if hovered tile exists in tilemap ongrid or if exists in offgrid
                if tile_loc in self.tilemap.tilemap:
                    del self.tilemap.tilemap[tile_loc]
                for tile in self.tilemap.offgrid_tiles.copy():
                    tile_img = self.assets[tile['type']][tile['variant']]
                    tile_r = pygame.Rect(tile['pos'][0] - self.scroll[0], tile['pos'][1] - self.scroll[1], tile_img.get_width(), tile_img.get_height())
                    if tile_r.collidepoint(mpos):
                        self.tilemap.offgrid_tiles.remove(tile)

            self.display.blit(current_tile_img, (5, 5))

            # Get user input
            for event in pygame.event.get():
                # Clicking X to close window
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                # On Mouseclick event for Editor
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Left Click Down
                    if event.button == 1:
                        self.clicking = True
                        if not self.ongrid:
                            # Add camera coordinates to cursor coordinates for world coordinates, then add to Off Grid tiles.
                            self.tilemap.offgrid_tiles.append({'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': (mpos[0] + self.scroll[0], mpos[1] + self.scroll[1])})
                    # Right Click Down
                    if event.button == 3:
                        self.right_clicking = True
                    if self.shift:
                        # Mousewheel Scroll Up
                        if event.button == 4:
                            self.tile_variant = (self.tile_variant - 1) % len(self.assets[self.tile_list[self.tile_group]])
                        # Mousewheel Scroll Down
                        if event.button == 5:
                            self.tile_variant = (self.tile_variant + 1) % len(self.assets[self.tile_list[self.tile_group]])
                    else:
                        # Mousewheel Scroll Up
                        if event.button == 4:
                            self.tile_variant = 0
                            self.tile_group = (self.tile_group - 1) % len(self.tile_list)                
                        # Mousewheel Scroll Down
                        if event.button == 5:
                            self.tile_variant = 0
                            self.tile_group = (self.tile_group + 1) % len(self.tile_list)
                if event.type == pygame.MOUSEBUTTONUP:
                    # Left Click Up
                    if event.button == 1:
                        self.clicking = False
                    # Right Click Up
                    if event.button == 3:
                        self.right_clicking = False                             
                # On Keypress event
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_w:
                        self.movement[2] = True
                    if event.key == pygame.K_s:
                        self.movement[3] = True
                    # Pressing G will toggle between On Grid or Off Grid tiles in editor
                    if event.key == pygame.K_g:
                        self.ongrid = not self.ongrid
                    # Pressing T will do AutoTiling to match appropriate tile variants to their neighbor tiles, this changes all blocks of ground tiles to follow tiling rules
                    if event.key == pygame.K_t:
                        self.tilemap.autotile()
                    # Pressing O will output save the map to a Json file in editor
                    if event.key == pygame.K_o:
                        self.tilemap.save('map.json')
                    # Holding Shift will scroll variant tile list in editor
                    if event.key == pygame.K_LSHIFT:
                        self.shift = True
                # On Keypress release event
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False
                    if event.key == pygame.K_w:
                        self.movement[2] = False
                    if event.key == pygame.K_s:
                        self.movement[3] = False
                    if event.key == pygame.K_LSHIFT:
                        self.shift = False
            
            # Render the display onto the window
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            # Update the display
            pygame.display.update()
            # Force at 60 fps
            self.clock.tick(60)

Editor().run()

