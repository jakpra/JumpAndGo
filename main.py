from collections import defaultdict

import pygame
import pygame.gfxdraw

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

        self.id2intersects = {}
        self.intersects2id = {}
        self.id2grid = {}
        self.grid2id = defaultdict(lambda: -1)
        for i, v in enumerate(self.intersects):
            self.id2intersects[i] = v
            self.intersects2id[tuple(v)] = i
            grid_pos = (int((v[0] - xmarg) / sqlen * size) + 1, int((v[1] - ymarg) / sqlen * size) + 1)
            self.id2grid[i] = grid_pos
            self.grid2id[grid_pos] = i

        self.edges = {'top':    {'y': ymarg},
                      'right':  {'x': xwidth - xmarg - (sqlen / self.size)},
                      'bottom': {'y': yheight - ymarg - (sqlen / self.size)},
                      'left':   {'x': xmarg}}

        self.id2influence = defaultdict(float)

    def draw(self, screen):
        screen.fill('white')

        for i, infl in self.id2influence.items():
            if i in id2intersects:
                _infl = min(255, max(0, abs(255*infl)))
                _inv = 255-_infl  # ((2*255)-_infl)//2
                color = (255 if infl<0 else _inv, _inv, 255 if infl>0 else _inv)
                screen.fill(color,
                            pygame.rect.Rect((id2intersects[i][0]-stone_size, id2intersects[i][1]-stone_size),
                                             (2*stone_size, 2*stone_size)))

        for i in range(self.size):
            pygame.draw.line(screen, 'black',
                             (xmarg, (ymarg + (i / self.size) * sqlen)),
                             (xwidth - xmarg - (sqlen / self.size), (ymarg + (i / self.size) * sqlen)))
            pygame.draw.line(screen, 'black',
                             ((xmarg + (i / self.size) * sqlen), ymarg),
                             ((xmarg + (i / self.size) * sqlen), yheight - ymarg - (sqlen / self.size)))

board = Board(board_size)
intersects = board.intersects
id2intersects = board.id2intersects
intersects2id = board.intersects2id
id2grid = board.id2grid
grid2id = board.grid2id
id2influence = board.id2influence

free_intersect_ids = set(id2grid.keys())

print('id2intersects', id2intersects)
print('id2grid', id2grid)

click_ready = True

prev_stones = None
stones = {0: frozenset(), 1: frozenset()}
id2sprite = {}
stone_sprites = pygame.sprite.Group()

G_CONST = 9.81
I_CONST = 0.5


class Player(pygame.sprite.Sprite):
    def __init__(self, komi=0, idx=0, start_pos=id2intersects[len(intersects)//2],
                 floor='bottom', stone_floor='top', gravity=1, color='red',
                 keys=[pygame.K_UP, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN]):
        super().__init__()
        self.idx = idx
        self.width = 7
        self.height = 7
        self.xy = start_pos
        self.xy_dict = {'x': start_pos[0], 'y': start_pos[1]}
        self.xvel = 0
        self.yvel = 0
        self.home_floor = board.edges[floor]
        self.cur_floor = self.home_floor
        self.stone_floor = stone_floor
        self.gravity = gravity
        self.floor_axis = 'y'

        self.color = color

        self.jump_ready = True
        self.rotate_ready = True
        self.floating = True
        self.rotated = False
        # self.rotations = [0, 1, 2, 3]  # cycle through

        left = self.xy[0] - (self.width * max(0, self.gravity))
        top = self.xy[1] - (self.height * max(0, self.gravity))
        self.rect = pygame.rect.Rect((left, top), (self.width, self.height))

        self.keys = keys

        self.score = komi

    def update(self, dt):

        # fall
        floor_axis = self.xy_dict[self.floor_axis]
        if self.cur_floor.get(self.floor_axis, floor_axis) != floor_axis:  # check if we are floating
            if floor_axis * self.gravity > self.cur_floor[self.floor_axis] * self.gravity:  # below floor
                if self.rotated:
                    self.xvel = 0
                else:
                    self.yvel = 0
                self.xy_dict[self.floor_axis] = self.cur_floor[self.floor_axis]  # clip back  # TODO: currently instantly boosting to the top of any stone pile
            else:
                self.floating = True
                if self.rotated:
                    self.xvel += G_CONST * self.gravity
                else:
                    self.yvel += G_CONST * self.gravity  # if we are floating above floor, move towards floor
        else:
            self.floating = False

        # inertia
        if not self.floating:
            if self.rotated:
                self.yvel *= I_CONST  # inertia
                if abs(self.yvel) < 0.1:  # clipping
                    self.yvel = 0
            else:
                self.xvel *= I_CONST  # inertia
                if abs(self.xvel) < 0.1:  # clipping
                    self.xvel = 0

        keys = pygame.key.get_pressed()

        # rotate
        if keys[self.keys[3]]:
            if self.rotate_ready:
                if self.rotated:
                    self.rotate_ready = False
                    self.rotated = False
                    self.floor_axis = 'y'
                    self.cur_floor = self.home_floor = board.edges['bottom' if self.gravity > 0 else 'top']
                    self.stone_floor = 'top' if self.gravity > 0 else 'bottom'
                else:
                    self.rotate_ready = False
                    self.rotated = True
                    self.floor_axis = 'x'
                    self.cur_floor = self.home_floor = board.edges['right' if self.gravity > 0 else 'left']
                    self.stone_floor = 'left' if self.gravity > 0 else 'right'
                self.floating = True
        else:
            self.rotate_ready = True

        # jump
        if keys[self.keys[0]]:
            if self.jump_ready and not self.floating:
                self.jump_ready = False
                if self.rotated:
                    self.xvel -= 350 * self.gravity
                else:
                    self.yvel -= 350 * self.gravity
        else:
            self.jump_ready = True

        # walk
        acc = 2 if self.floating else 50 if self.cur_floor != self.home_floor else 200
        if keys[self.keys[1]]:
            if self.rotated:
                self.yvel += acc * self.gravity
            else:
                self.xvel -= acc * self.gravity
        if keys[self.keys[2]]:
            if self.rotated:
                self.yvel -= acc * self.gravity
            else:
                self.xvel += acc * self.gravity

        # updating pos
        self.xy_dict['x'] += self.xvel * dt
        self.xy_dict['y'] += self.yvel * dt
        self.xy = pygame.math.Vector2(self.xy_dict['x'], self.xy_dict['y'])

        # collision
        coll = pygame.sprite.spritecollideany(self, stone_sprites)
        if coll:
            self.cur_floor = {self.floor_axis: getattr(coll.rect, self.stone_floor)}
        else:
            self.cur_floor = self.home_floor

    def draw(self, screen):
        left = self.xy[0]-(self.width * max(0, self.gravity))
        top = self.xy[1]-(self.height * max(0, self.gravity))
        self.rect = pygame.rect.Rect((left, top), (self.width, self.height))
        pygame.draw.rect(screen, self.color, self.rect)


class Player1(Player):
    def __init__(self):
        super().__init__(komi=6.5, idx=1,
                 floor='left', stone_floor='right', gravity=-1, color='blue',
                 keys=[pygame.K_s, pygame.K_q, pygame.K_y, pygame.K_a])

        self.rotated = True
        self.floor_axis = 'x'


players = [Player(), Player1()]


class Group:  # TODO: idea: groups project influence/strength, opposing strength can also cancel each other out
    def __init__(self, stones):
        self.stones = stones
        self.stone_ids = set(s.i for s in self.stones)
        self._liberties = None

    @property
    def liberties(self):
        lib = set()
        for stone in self.stones:
            x, y = stone.grid
            neighbors = [((x - 1), y), ((x + 1), y), (x, (y - 1)), (x, (y + 1))]
            for n in neighbors:
                if (i := grid2id.get(n)) in free_intersect_ids and i not in self.stone_ids:  # TODO: is the stone_ids check necessary?
                    lib.add(i)
        self._liberties = lib
        return len(self._liberties)


class Stone(pygame.sprite.Sprite):
    def __init__(self, placement_id, player):
        super().__init__()
        self.i = placement_id
        self.xy = id2intersects[placement_id]
        self.grid = id2grid[placement_id]
        self.player = player
        self.rect = pygame.rect.Rect((self.xy[0]-stone_size, self.xy[1]-stone_size),
                                     (2*stone_size, 2*stone_size))

        connected_stones = set()
        captured_stones = set()
        x, y = self.grid
        neighbors = [((x - 1), y), ((x + 1), y), (x, (y - 1)), (x, (y + 1))]
        for n in neighbors:
            if (i := grid2id.get(n)) in id2sprite:
                stone = id2sprite[i]
                if stone.player == self.player:
                    for s in stone.group.stones:
                        connected_stones.add(s.i)
                else:
                    if stone.group.liberties <= 1:
                        for s in stone.group.stones:
                            captured_stones.add(s.i)

        self.new_stones = {self.player: stones[self.player] | frozenset([self.i])}

        other_player = abs(self.player - 1)

        if captured_stones:
            self.new_stones[other_player] = stones[other_player] - frozenset(captured_stones)

            if self.new_stones == prev_stones:
                print('Illegal move: Ko.')
                raise ValueError

            print(f'Captured {len(captured_stones)} stones!')
            for s in captured_stones:
                free_intersect_ids.add(s)
                sprite = id2sprite.pop(s)
                stone_sprites.remove_internal(sprite)
                players[self.player].score += 1
        else:
            self.new_stones[other_player] = stones[other_player]

        self.group = Group([self] + [id2sprite[i] for i in connected_stones])
        if self.group.liberties == 0:
            print('Illegal move: self-capture.')
            raise ValueError

        for s in connected_stones:
            id2sprite[s].group = self.group  # TODO: sanity check garbage collector: how many unused/old groups are kept around?

        print(f'Placed {player_colors[self.player]} stone. It belongs to a group with {len(self.group.stones)} stones {[s.i for s in self.group.stones]} and {self.group.liberties} liberties {list(self.group._liberties)}.')

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

    for s_id in id2sprite:
        sprite = id2sprite[s_id]
        sprite.draw(screen)

    for player in players:
        player.update(dt)
        player.draw(screen)

    my_font = pygame.font.SysFont('Arial', 30)
    player0_score_text = my_font.render(f'Score: {players[0].score}', True, (0, 0, 0))
    player0_ctrl_text = my_font.render('Arrows,Space', True, (0, 0, 0))
    player1_score_text = my_font.render(f'Score: {players[1].score}', True, (0, 0, 0))
    player1_ctrl_text = my_font.render('SQAY,Space', True, (0, 0, 0))

    click, _, _ = pygame.mouse.get_pressed(3)
    keys = pygame.key.get_pressed()
    space = keys[pygame.K_SPACE]
    placement = False
    if click:
        if click_ready:
            placement = True
            click_ready = False
        pos = pygame.math.Vector2(pygame.mouse.get_pos())
    elif space:
        if click_ready:
            placement = True
            click_ready = False
        pos = players[player_id].xy
    else:
        click_ready = True

    if placement:  # TODO: idea: can aim and place stones not only at current position but also anywhere in the influence of the group we are currently standing on
                   # TODO: OR - can still only place at current position, but when inside stone influence, we can move around more freely/floaty and more precisely
        min_d = float('inf')
        min_v = None
        min_i = None
        for i in free_intersect_ids:  # find intersection closest to player position
            v = id2intersects[i]
            d = pos.distance_to(v)
            if d < min_d:
                min_d = d
                min_v = v
                min_i = i
        if min_i in free_intersect_ids:
            try:
                s = Stone(min_i, player_id)
            except ValueError:
                pass
            else:
                free_intersect_ids.remove(min_i)
                prev_stones, stones = stones, s.new_stones
                id2sprite[min_i] = s
                stone_sprites.add_internal(s)

                x, y = id2grid[s.i]
                _x, _y = x, y-1
                m = 1  # resolution  # TODO: for m != 1, id2influence needs to be replaced with pxlCoord2influence
                n = m  # spiral edge length
                strength = player_id-0.5
                id2influence[s.i] += 2*strength
                while abs(strength) > 0.01:
                    # fib1, fib2 = fib2, fib1+fib2
                    for _ in range(n//m):
                        id2influence[grid2id[_x, _y]] += strength
                        _x += m  # right
                    # fib1, fib2 = fib2, fib1+fib2
                    n += m

                    for _ in range(n//m):
                        id2influence[grid2id[_x, _y]] += strength
                        _y += m  # down
                    # fib1, fib2 = fib2, fib1+fib2
                    for _ in range(n//m):
                        id2influence[grid2id[_x, _y]] += strength
                        _x -= m  # left
                    # fib1, fib2 = fib2, fib1+fib2
                    n += m

                    for _ in range(n//m):
                        id2influence[grid2id[_x, _y]] += strength
                        _y -= m  # up

                    strength /= 2

                player_id = abs(player_id-1)

    screen.blit(player1_score_text, (xmarg/3, yheight/5))
    screen.blit(player1_ctrl_text, (xmarg/3, yheight/5+30))
    screen.blit(player0_score_text, (xwidth-xmarg, 3*yheight/4))
    screen.blit(player0_ctrl_text, (xwidth-xmarg, 3*yheight/4+30))

    # flip() the display to put your work on screen
    pygame.display.flip()

    # limits FPS to 60
    # dt is delta time in seconds since last frame, used for framerate-
    # independent physics.
    dt = clock.tick(60) / 1000


pygame.quit()