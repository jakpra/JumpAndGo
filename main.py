# Example file showing a circle moving on screen
import pygame

# pygame setup
pygame.init()
pygame.font.init()

xwidth = 1280
yheight = 720

sqlen = min(xwidth, yheight) - 45

xmarg = (xwidth - sqlen) / 2
ymarg = (yheight - sqlen) / 2

screen = pygame.display.set_mode((xwidth, yheight))
clock = pygame.time.Clock()
running = True
dt = 0

player_pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)

player_colors = ['black', 'white']
player_id = 0

board_size = 19
stone_size = (1/board_size)*sqlen/2

class Board:
    def __init__(self, size):
        self.size = size

        self.intersects = []
        for i in range(size):
            for j in range(size):
                self.intersects.append(pygame.math.Vector2(xmarg + (i / size) * sqlen,
                                                           ymarg + (j / size) * sqlen))

        self.edges = {'top':    {'y': ymarg},
                      'right':  {'x': xwidth - xmarg - (sqlen / self.size)},
                      'bottom': {'y': yheight - ymarg - (sqlen / self.size)},
                      'left':   {'x': xmarg}}

    def draw(self, screen):
        screen.fill('white')

        for i in range(self.size):
            pygame.draw.line(screen, 'gray',
                             (xmarg, (ymarg + (i / self.size) * sqlen)),
                             (xwidth - xmarg - (sqlen / self.size), (ymarg + (i / self.size) * sqlen)))
            pygame.draw.line(screen, 'gray',
                             ((xmarg + (i / self.size) * sqlen), ymarg),
                             ((xmarg + (i / self.size) * sqlen), yheight - ymarg - (sqlen / self.size)))


board = Board(board_size)
intersects = board.intersects
id2intersects = {i: v for i, v in enumerate(intersects)}
intersects2ids = {tuple(v): i for i, v in enumerate(intersects)}
free_intersect_ids = set(id2intersects.keys())

click_ready = True

stones = {0: [], 1: []}
id2sprite = {}
stone_sprites = pygame.sprite.Group()

G_CONST = 9.81
I_CONST = 0.5


class Player(pygame.sprite.Sprite):
    def __init__(self, idx=0, start_pos=id2intersects[len(intersects)-2],
                 floor='bottom', stone_floor='top', gravity=1, color='red',
                 keys=[pygame.K_UP, pygame.K_LEFT, pygame.K_RIGHT]):
        super().__init__()
        self.idx = idx
        self.width = 6
        self.height = 8
        self.xy = start_pos
        self.xvel = 0
        self.yvel = 0
        self.home_floor = board.edges[floor]
        self.cur_floor = self.home_floor
        self.stone_floor = stone_floor
        self.gravity = gravity
        self.color = color

        self.jump_ready = True
        self.floating = True

        left = self.xy[0]-self.width/2
        top = self.xy[1]-(self.height * max(0, self.gravity))
        self.rect = pygame.rect.Rect((left, top), (self.width, self.height))

        self.keys = keys

    def update(self, dt):
        x, y = self.xy

        # fall
        if self.cur_floor.get('y', y) != y:  # check if we are floating
            if y * self.gravity > self.cur_floor['y'] * self.gravity:  # below floor
                y = self.cur_floor['y']
                self.yvel = 0
            else:
                self.floating = True
                self.yvel += G_CONST * self.gravity  # if we are, move towards floor
        else:
            self.floating = False

        # inertia
        if not self.floating:
            self.xvel = self.xvel * I_CONST  # inertia
            if abs(self.xvel) < 0.1:  # clipping
                self.xvel = 0

        keys = pygame.key.get_pressed()

        # jump
        if keys[self.keys[0]]:
            if self.jump_ready and not self.floating:
                self.jump_ready = False
                self.yvel -= 350 * self.gravity
        else:
            self.jump_ready = True

        # walk
        acc = 2 if self.floating else 50 if self.cur_floor != self.home_floor else 200
        if keys[self.keys[1]]:
            self.xvel -= acc
        if keys[self.keys[2]]:
            self.xvel += acc

        # updating pos
        x += self.xvel * dt
        y += self.yvel * dt
        self.xy = pygame.math.Vector2(x, y)

        # collision
        coll = pygame.sprite.spritecollideany(self, stone_sprites)
        if coll:
            self.cur_floor = {'y': getattr(coll.rect, self.stone_floor)}
        else:
            self.cur_floor = self.home_floor


    def draw(self, screen):
        left = self.xy[0]-self.width/2
        top = self.xy[1]-(self.height * max(0, self.gravity))
        self.rect = pygame.rect.Rect((left, top), (self.width, self.height))
        pygame.draw.rect(screen, self.color, self.rect)


class Player1(Player):
    def __init__(self):
        super().__init__(idx=1, start_pos=id2intersects[1],
                 floor='top', stone_floor='bottom', gravity=-1, color='blue',
                 keys=[pygame.K_w, pygame.K_a, pygame.K_d])


players = [Player(), Player1()]


class Stone(pygame.sprite.Sprite):
    def __init__(self, xy, player):
        super().__init__()
        self.xy = xy
        self.player = player
        self.rect = pygame.rect.Rect((self.xy[0]-stone_size, self.xy[1]-stone_size),
                                     (1.5*stone_size, 2*stone_size))

    def draw(self, screen):
        pygame.draw.circle(screen, 'black', self.xy, stone_size + 0.1)
        pygame.draw.circle(screen, player_colors[self.player], self.xy, stone_size - 1)


while running:
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    board.draw(screen)

    for p, s in stones.items():
        for s_id in s:
            sprite = id2sprite[s_id]
            sprite.draw(screen)

    for player in players:
        player.update(dt)
        player.draw(screen)

    my_font = pygame.font.SysFont('Arial', 30)
    text_surface1 = my_font.render('Arrows,Space', False, (0, 0, 0))
    text_surface2 = my_font.render('W,A,D,Space', False, (0, 0, 0))

    # click, _, _ = pygame.mouse.get_pressed(3)
    keys = pygame.key.get_pressed()
    click = keys[pygame.K_SPACE]
    if click:
        if click_ready:
            click_ready = False

            # pos = pygame.math.Vector2(pygame.mouse.get_pos())
            pos = players[player_id].xy
            min_d = float('inf')
            min_v = None
            for v in intersects:
                d = pos.distance_to(v)
                if d < min_d:
                    min_d = d
                    min_v = v
            placement = intersects2ids[tuple(min_v)]
            if placement in free_intersect_ids:
                free_intersect_ids.remove(placement)
                stones[player_id].append(placement)
                s = Stone(id2intersects[placement], player_id)
                id2sprite[placement] = s
                stone_sprites.add_internal(s)
                player_id = abs(player_id-1)
    else:
        click_ready = True

    screen.blit(text_surface2, (xmarg/3, yheight/5))
    screen.blit(text_surface1, (xwidth-xmarg, 3*yheight/4))

    # flip() the display to put your work on screen
    pygame.display.flip()

    # limits FPS to 60
    # dt is delta time in seconds since last frame, used for framerate-
    # independent physics.
    dt = clock.tick(60) / 1000


pygame.quit()