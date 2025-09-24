import tkinter as tk
import math
import random

CELL_SIZE = 20
GRID_WIDTH = 40
GRID_HEIGHT = 40
GAME_SPEED = 1  # milliseconds

SNAKE_HEAD_COLOR = "green"
SNAKE_BODY_COLOR = "lightgreen"
FOOD_COLOR = "red"
SCORE_COLOR = "white"
GAME_OVER_COLOR = "red"
FONT_SCORE = ("Arial", 12)
FONT_GAME_OVER = ("Arial", 24)
FONT_GAME_OVER_SCORE = ("Arial", 16)

class MathHelpers:
    @staticmethod
    def cell_center(x, y):
        """Return the pixel center of a grid cell (x, y)."""
        return x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def line_endpoints(cx, cy, angle, length, pivot=0.0):
        """
        Returns (x1, y1, x2, y2) for a line of given length and pivot (0.0=start, 0.5=center, 1.0=end)
        cx, cy: center point
        angle: direction in radians
        length: length of the line
        pivot: 0.0 = start at cx,cy; 0.5 = center at cx,cy; 1.0 = end at cx,cy
        """
        offset1 = (pivot - 0.5) * length
        offset2 = (pivot + 0.5) * length
        x1 = cx + math.cos(angle) * offset1
        y1 = cy + math.sin(angle) * offset1
        x2 = cx + math.cos(angle) * offset2
        y2 = cy + math.sin(angle) * offset2
        return x1, y1, x2, y2

    @staticmethod
    def perp_vector(angle, width):
        """Return the perpendicular vector (wx, wy) for a given angle and width."""
        wx = math.cos(angle + math.pi / 2) * (width / 2)
        wy = math.sin(angle + math.pi / 2) * (width / 2)
        return wx, wy

class SnakeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Snake Game")
        self.canvas = tk.Canvas(root, width=GRID_WIDTH*CELL_SIZE, height=GRID_HEIGHT*CELL_SIZE, bg="black")
        self.canvas.pack()
        self.direction = "Right"
        self.snake = [(5, 5), (4, 5), (3, 5)]
        self.food = None
        self.game_over = False
        self.score = len(self.snake)
        self.high_score = len(self.snake)
        self.pending_direction = None  # For U-turn logic
        self.head_size = 10  # 1 = radius 0 (just head), 2 = radius 1 (3x3), etc.
        self.mouse_x = 0
        self.mouse_y = 0
        self.frame_count = 0
        self.move_interval = 50

        self.meteor_active = False
        self.meteor_pos = (0, 0)
        self.meteor_vel = (0, 0)
        self.meteor_size = 25
        self.meteor_timer = 0
        self.meteor_frame_count = 0
        self.meteor_interval = 40  # Control meteor speed

        self.laser_active = False
        self.laser_progress = 0
        self.laser_max_progress = 60  # Number of frames for the fade
        self.laser_angle = 0
        self.laser_line = None

        self.spawn_food()
        self.game_loop()

        self.root.bind("<Key>", self.on_key_press)
        self.root.bind("<Motion>", self.on_mouse_move)
        self.root.bind("<Button-1>", self.on_laser_click)

    def get_perpendicular_toward_center(self, direction, head_x, head_y):
        center_x = GRID_WIDTH // 2
        center_y = GRID_HEIGHT // 2
        if direction in ["Left", "Right"]:
            return "Up" if head_y > center_y else "Down"
        else:
            return "Left" if head_x > center_x else "Right"

    def on_key_press(self, event):
        key = event.keysym.lower()
        wasd_to_dir = {"a": "Left", "d": "Right", "w": "Up", "s": "Down"}
        opposites = {"Left": "Right", "Right": "Left", "Up": "Down", "Down": "Up"}
        if key in ["left", "right", "up", "down"]:
            new_dir = key.capitalize()
        elif key in wasd_to_dir:
            new_dir = wasd_to_dir[key]
        else:
            return

        # If trying to reverse, immediately turn perpendicular toward center
        if opposites.get(new_dir) == self.direction:
            head_x, head_y = self.snake[0]
            perp = self.get_perpendicular_toward_center(self.direction, head_x, head_y)
            self.direction = perp
            self.pending_direction = new_dir
        # If the user quickly presses the reverse direction again, allow it
        elif self.pending_direction and new_dir == self.pending_direction:
            self.direction = new_dir
            self.pending_direction = None
        else:
            self.direction = new_dir
            self.pending_direction = None

    def spawn_food(self):
        while True:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break

    def handle_food_collision(self, new_head):
        """Handle all logic related to eating food within a configurable radius."""
        x, y = new_head
        r = self.head_size - 1  # head_size=1 means radius 0, head_size=2 means radius 1, etc.
        positions = [(x + dx, y + dy) for dx in range(-r, r+1) for dy in range(-r, r+1)]
        if self.food in positions:
            self.spawn_food()
            return True  # Snake grows
        return False  # Snake moves normally

    def move_snake(self):
        # Apply pending direction if set
        if self.pending_direction:
            self.direction = self.pending_direction
            self.pending_direction = None

        if self.game_over:
            self.draw_game_over()
            return

        head_x, head_y = self.snake[0]
        if self.direction == "Left":
            head_x -= 1
        elif self.direction == "Right":
            head_x += 1
        elif self.direction == "Up":
            head_y -= 1
        elif self.direction == "Down":
            head_y += 1

        new_head = (head_x, head_y)

        # Check collisions
        if (head_x < 0 or head_x >= GRID_WIDTH or
            head_y < 0 or head_y >= GRID_HEIGHT or
            new_head in self.snake):
            # Try to turn perpendicular toward center instead of dying
            perp = self.get_perpendicular_toward_center(self.direction, *self.snake[0])
            head_x, head_y = self.snake[0]
            if perp == "Left":
                head_x -= 1
            elif perp == "Right":
                head_x += 1
            elif perp == "Up":
                head_y -= 1
            elif perp == "Down":
                head_y += 1
            new_head = (head_x, head_y)
            if (0 <= head_x < GRID_WIDTH and 0 <= head_y < GRID_HEIGHT and new_head not in self.snake):
                self.direction = perp
            else:
                self.game_over = True
                self.draw_game_over()
                return

        self.snake = [new_head] + self.snake
        if not self.handle_food_collision(new_head):
            self.snake.pop()

        self.score = len(self.snake)
        if self.score > self.high_score:
            self.high_score = self.score

        # Dynamically set head_size
        self.head_size = max(1, min(10, len(self.snake) // 2))

        self.draw()

    def meteor(self):
        """Randomly create a meteor that travels across the screen."""
        if self.meteor_active:
            return  # Only one meteor at a time

        # Randomly pick a starting edge and direction
        edges = ["top", "bottom", "left", "right"]
        edge = random.choice(edges)
        if edge == "top":
            x = random.randint(0, GRID_WIDTH * CELL_SIZE)
            y = 0
            angle = random.uniform(math.radians(20), math.radians(160))
        elif edge == "bottom":
            x = random.randint(0, GRID_WIDTH * CELL_SIZE)
            y = GRID_HEIGHT * CELL_SIZE
            angle = random.uniform(-math.radians(160), -math.radians(20))
        elif edge == "left":
            x = 0
            y = random.randint(0, GRID_HEIGHT * CELL_SIZE)
            angle = random.uniform(-math.radians(70), math.radians(70))
        else:  # right
            x = GRID_WIDTH * CELL_SIZE
            y = random.randint(0, GRID_HEIGHT * CELL_SIZE)
            angle = random.uniform(math.radians(110), math.radians(250))

        speed = random.uniform(8, 16)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed

        self.meteor_pos = [x, y]
        self.meteor_vel = [vx, vy]
        self.meteor_active = True
        self.meteor_timer = 0

    def update_meteor(self):
        """Move the meteor if active, at a controlled speed, and check for snake collision."""
        if not self.meteor_active:
            # Randomly spawn a meteor every ~5 seconds
            if random.randint(0, 500) == 0:
                self.meteor()
            return

        self.meteor_frame_count += 1
        if self.meteor_frame_count % self.meteor_interval == 0:
            self.meteor_pos[0] += self.meteor_vel[0]
            self.meteor_pos[1] += self.meteor_vel[1]
            self.meteor_timer += 1

            # Check for collision with snake
            mx, my = self.meteor_pos
            r = self.meteor_size // 2
            for idx, (sx, sy) in enumerate(self.snake):
                # Snake segment center
                seg_cx, seg_cy = MathHelpers.cell_center(sx, sy)
                dist = math.hypot(mx - seg_cx, my - seg_cy)
                if dist < r + CELL_SIZE // 2:
                    # Lose half the segments, rounding down, but always keep at least 1
                    n = len(self.snake)
                    keep = max(1, n // 2)
                    self.snake = self.snake[:keep]
                    self.meteor_active = False
                    self.meteor_frame_count = 0
                    break

            # Remove meteor if it goes off screen or after a certain time
            x, y = self.meteor_pos
            if (x < -self.meteor_size or x > GRID_WIDTH * CELL_SIZE + self.meteor_size or
                y < -self.meteor_size or y > GRID_HEIGHT * CELL_SIZE + self.meteor_size or
                self.meteor_timer > 200):
                self.meteor_active = False
                self.meteor_frame_count = 0  # Reset for next meteor

    def on_laser_click(self, event):
        # Start the laser from the rectangle's tip toward the edge in the direction of the mouse
        head_x, head_y = self.snake[0]
        head_cx, head_cy = MathHelpers.cell_center(head_x, head_y)
        dx = self.mouse_x - head_cx
        dy = self.mouse_y - head_cy
        self.laser_angle = math.atan2(dy, dx)
        self.laser_active = True
        self.laser_progress = 0

        # Calculate laser line endpoints (same as in update_laser)
        rect_length = 30
        tip_offset = rect_length * 0.75
        x0 = head_cx + math.cos(self.laser_angle) * tip_offset
        y0 = head_cy + math.sin(self.laser_angle) * tip_offset

        w = GRID_WIDTH * CELL_SIZE
        h = GRID_HEIGHT * CELL_SIZE
        t_vals = []
        if math.cos(self.laser_angle) != 0:
            t_left = (0 - x0) / math.cos(self.laser_angle)
            t_right = (w - x0) / math.cos(self.laser_angle)
            t_vals.extend([t_left, t_right])
        if math.sin(self.laser_angle) != 0:
            t_top = (0 - y0) / math.sin(self.laser_angle)
            t_bottom = (h - y0) / math.sin(self.laser_angle)
            t_vals.extend([t_top, t_bottom])
        t_vals = [t for t in t_vals if t > 0]
        if t_vals:
            t_edge = min(t_vals)
        else:
            t_edge = 0
        x1 = x0 + math.cos(self.laser_angle) * t_edge
        y1 = y0 + math.sin(self.laser_angle) * t_edge

        # --- Meteor collision check at time of click ---
        if self.meteor_active:
            mx, my = self.meteor_pos
            r = self.meteor_size
            # Distance from meteor center to laser line segment
            dist = self.point_to_segment_distance(mx, my, x0, y0, x1, y1)
            if dist <= r:
                self.meteor_active = False
                self.meteor_frame_count = 0

    def point_to_segment_distance(self, px, py, x0, y0, x1, y1):
        """Return the shortest distance from point (px,py) to segment (x0,y0)-(x1,y1)."""
        # Vector from x0,y0 to x1,y1
        dx = x1 - x0
        dy = y1 - y0
        if dx == dy == 0:
            # The segment is a point
            return math.hypot(px - x0, py - y0)
        # Project point onto the segment, clamped to [0,1]
        t = ((px - x0) * dx + (py - y0) * dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t))
        nearest_x = x0 + t * dx
        nearest_y = y0 + t * dy
        return math.hypot(px - nearest_x, py - nearest_y)

    def update_laser(self):
        if not self.laser_active:
            return

        # Fade color from red to black over laser_max_progress frames
        fade = self.laser_progress / self.laser_max_progress
        r = int(255 * (1 - fade))
        g = int(0 * (1 - fade))
        b = int(0 * (1 - fade))
        color = f"#{r:02x}{g:02x}{b:02x}"

        # Start point: tip of the rectangle
        head_x, head_y = self.snake[0]
        head_cx, head_cy = MathHelpers.cell_center(head_x, head_y)
        rect_length = 30
        tip_offset = rect_length * 0.75
        x0 = head_cx + math.cos(self.laser_angle) * tip_offset
        y0 = head_cy + math.sin(self.laser_angle) * tip_offset

        # End point: where the line hits the edge of the screen
        # Calculate intersection with screen edge
        w = GRID_WIDTH * CELL_SIZE
        h = GRID_HEIGHT * CELL_SIZE
        # Parametric line: x = x0 + t*cos(angle), y = y0 + t*sin(angle)
        # Find t where line hits any edge
        t_vals = []
        if math.cos(self.laser_angle) != 0:
            t_left = (0 - x0) / math.cos(self.laser_angle)
            t_right = (w - x0) / math.cos(self.laser_angle)
            t_vals.extend([t_left, t_right])
        if math.sin(self.laser_angle) != 0:
            t_top = (0 - y0) / math.sin(self.laser_angle)
            t_bottom = (h - y0) / math.sin(self.laser_angle)
            t_vals.extend([t_top, t_bottom])
        # Only consider positive t (forward direction)
        t_vals = [t for t in t_vals if t > 0]
        if t_vals:
            t_edge = min(t_vals)
        else:
            t_edge = 0
        x1 = x0 + math.cos(self.laser_angle) * t_edge
        y1 = y0 + math.sin(self.laser_angle) * t_edge

        # Draw the laser line
        self.laser_line = (x0, y0, x1, y1, color)

        self.laser_progress += 1
        if self.laser_progress >= self.laser_max_progress:
            self.laser_active = False
            self.laser_line = None

    def game_loop(self):
        if not self.game_over:
            self.frame_count += 1
            if self.frame_count % self.move_interval == 0:
                self.move_snake()
            self.update_meteor()
            self.update_laser()
            self.draw()
        else:
            self.draw_game_over()
        self.root.after(1, self.game_loop)

    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

    def draw(self):
        self.canvas.delete("all")
        # Draw food
        x, y = self.food
        self.canvas.create_rectangle(
            x*CELL_SIZE, y*CELL_SIZE,
            (x+1)*CELL_SIZE, (y+1)*CELL_SIZE,
            fill=FOOD_COLOR
        )
        # Draw snake
        for i, (x, y) in enumerate(self.snake):
            color = SNAKE_HEAD_COLOR if i == 0 else SNAKE_BODY_COLOR
            self.canvas.create_rectangle(
                x*CELL_SIZE, y*CELL_SIZE,
                (x+1)*CELL_SIZE, (y+1)*CELL_SIZE,
                fill=color
            )
        # Draw score and high score
        self.canvas.create_text(50, 10, text=f"Score: {self.score}", fill=SCORE_COLOR, anchor="nw", font=FONT_SCORE)
        self.canvas.create_text(50, 30, text=f"High: {self.high_score}", fill=SCORE_COLOR, anchor="nw", font=FONT_SCORE)

        # Draw pointer rectangle on snake head pointing to mouse (pivot at 0.25 of its length)
        head_x, head_y = self.snake[0]
        head_cx, head_cy = MathHelpers.cell_center(head_x, head_y)

        dx = self.mouse_x - head_cx
        dy = self.mouse_y - head_cy
        angle = math.atan2(dy, dx)

        rect_length = 30
        rect_width = 5
        pivot = 0.25  # 0.25 means 25% from the back

        x1, y1, x2, y2 = MathHelpers.line_endpoints(head_cx, head_cy, angle, rect_length, pivot)
        wx, wy = MathHelpers.perp_vector(angle, rect_width)

        points = [
            x1 - wx, y1 - wy,
            x1 + wx, y1 + wy,
            x2 + wx, y2 + wy,
            x2 - wx, y2 - wy
        ]
        self.canvas.create_polygon(points, fill="yellow", outline="orange")

        # Draw laser if active
        if self.laser_line:
            lx0, ly0, lx1, ly1, color = self.laser_line
            self.canvas.create_line(lx0, ly0, lx1, ly1, fill=color, width=2)

        # Draw meteor if active
        if self.meteor_active:
            mx, my = self.meteor_pos
            r = self.meteor_size // 2
            self.canvas.create_oval(mx - r, my - r, mx + r, my + r, fill="white", outline="gray")

    def draw_game_over(self):
        self.draw()
        self.canvas.create_text(GRID_WIDTH*CELL_SIZE//2, GRID_HEIGHT*CELL_SIZE//2, 
                               text="GAME OVER", fill=GAME_OVER_COLOR, font=FONT_GAME_OVER)
        self.canvas.create_text(GRID_WIDTH*CELL_SIZE//2, GRID_HEIGHT*CELL_SIZE//2 + 30, 
                               text=f"Score: {self.score}", fill=SCORE_COLOR, font=FONT_GAME_OVER_SCORE)

if __name__ == "__main__":
    root = tk.Tk()
    game = SnakeGame(root)
    root.mainloop()