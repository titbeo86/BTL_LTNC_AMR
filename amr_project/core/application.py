"""
Application module — AMR Pathfinding Framework v4
Fixes:
  - ENTER: reset về IDLE sau mỗi bước → bấm liên tục được
  - Grid limit: tối đa 50×50
  - Dropdown click-through fix
  - ESC: dùng flag restart thay vì đệ quy
  - AMR auto-scale speed/size theo kích thước ô pixel
  - _reset() dùng API thay vì truy cập private
  - path_points giới hạn 500 điểm
  - field overlay dùng Surface cache
"""

import pygame
import sys
import threading

from core.input      import Input
from core.map        import Maps
from core.graphic    import Graphics
from core.amr        import Amrs
from component.sensor    import Sensors
from component.processor import Processors
from component.actuator  import Actuators
from utils.utils import turn2node, turn2pixel
from core.animator           import AlgoAnimator
from core.map_editor         import MapEditor
from core.waypoint_manager   import WaypointManager


# ─────────────────────────────────────────────────
#  SETUP SCREEN
# ─────────────────────────────────────────────────
class SetupScreen:
    BG      = (13,  15,  20)
    BG2     = (21,  24,  32)
    BORDER  = (42,  47,  66)
    ACCENT  = (0,   229, 255)
    ACCENT2 = (124, 58,  237)
    TEXT    = (226, 232, 240)
    MUTED   = (100, 116, 139)
    SUCCESS = (16,  185, 129)

    # 6 preset, xếp 2 hàng x 3 cột
    PRESETS = [
        ("10x10",  10,  10, 30),
        ("15x15",  15,  15, 25),
        ("20x20",  20,  20, 25),
        ("30x40",  30,  40, 20),
        ("40x40",  40,  40, 15),
        ("50x50",  50,  50, 10),
    ]

    def __init__(self, screen):
        self.screen     = screen
        self.font_main_title = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 12, bold=True)
        self.font_big   = pygame.font.SysFont("arial",   20, bold=True)
        self.font_label = pygame.font.SysFont("consolas", 11)
        self.font_input = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_hint  = pygame.font.SysFont("arial",   11)
        self.font_btn   = pygame.font.SysFont("consolas", 13, bold=True)
        self.values     = {"rows": "20", "cols": "20", "cell": "25"}
        self.focused    = "rows"

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                result = self._handle(event)
                if result:
                    return result
            self._draw()
            pygame.display.flip()
            clock.tick(60)

    def _handle(self, event):
        order = ["rows", "cols", "cell"]
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.focused = order[(order.index(self.focused)+1) % 3]
            elif event.key == pygame.K_RETURN:
                v = self._get_values()
                if v: return v
            elif event.key == pygame.K_BACKSPACE:
                self.values[self.focused] = self.values[self.focused][:-1]
            elif event.unicode.isdigit():
                if len(self.values[self.focused]) < 2:
                    self.values[self.focused] += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            W, H   = self.screen.get_size()
            cx, cy = W//2, H//2
            # Click vào field
            for key, rect in self._field_rects(cx, cy).items():
                if rect.collidepoint(mx, my):
                    self.focused = key
            # Click preset
            for i, (_, r, c, cm) in enumerate(self.PRESETS):
                if self._preset_rect(cx, cy, i).collidepoint(mx, my):
                    self.values = {"rows":str(r),"cols":str(c),"cell":str(cm)}
            # Click start
            if self._start_rect(cx, cy).collidepoint(mx, my):
                v = self._get_values()
                if v: return v
        return None

    def _get_values(self):
        try:
            r  = max(5,  min(50, int(self.values["rows"] or "20")))
            c  = max(5,  min(50, int(self.values["cols"] or "20")))
            cm = max(5,  min(200, int(self.values["cell"] or "25")))
            return (r, c, cm)
        except ValueError:
            return None

    def _field_rects(self, cx, cy):
        return {
            "rows": pygame.Rect(cx-185, cy-55, 110, 46),
            "cols": pygame.Rect(cx-55,  cy-55, 110, 46),
            "cell": pygame.Rect(cx+75,  cy-55, 110, 46),
        }

    def _preset_rect(self, cx, cy, i):
        col = i % 3; row = i // 3
        return pygame.Rect(cx-185 + col*130, cy + 25 + row*38, 110, 30)

    def _start_rect(self, cx, cy):
        return pygame.Rect(cx-185, cy+112, 370, 46)

    def _draw(self):
        W, H   = self.screen.get_size()
        cx, cy = W//2, H//2
        self.screen.fill(self.BG)
        for x in range(0,W,40):
            pygame.draw.line(self.screen,(22,26,36),(x,0),(x,H),1)
        for y in range(0,H,40):
            pygame.draw.line(self.screen,(22,26,36),(0,y),(W,y),1)

        # Card
        card = pygame.Rect(cx-210, cy-185, 420, 370)
        pygame.draw.rect(self.screen, self.BG2,    card, border_radius=14)
        pygame.draw.rect(self.screen, self.BORDER, card, 1, border_radius=14)
        pygame.draw.rect(self.screen, self.ACCENT2,
                         pygame.Rect(cx-210,cy-185,420,4),
                         border_top_left_radius=14,
                         border_top_right_radius=14)

        # Tiêu đề (Cỡ lớn và căn giữa)
        title_surf = self.font_main_title.render("AMR", True, self.ACCENT)
        self.screen.blit(title_surf, (cx - title_surf.get_width()//2, cy-155))
        
        subtitle_surf = self.font_big.render("Cau hinh he thong", True, self.TEXT)
        self.screen.blit(subtitle_surf, (cx - subtitle_surf.get_width()//2, cy-115))

        # Labels
        for txt, center_x in [("SO HANG", cx-130), ("SO COT", cx), ("O (CM)", cx+130)]:
            lbl = self.font_label.render(txt, True, self.MUTED)
            self.screen.blit(lbl, (center_x - lbl.get_width()//2, cy-80))

        # Input fields
        for key, rect in self._field_rects(cx, cy).items():
            focused = (self.focused == key)
            pygame.draw.rect(self.screen,(28,32,48),rect,border_radius=6)
            pygame.draw.rect(self.screen,
                             self.ACCENT if focused else self.BORDER,
                             rect, 2 if focused else 1, border_radius=6)
            vs = self.font_input.render(self.values[key], True, self.TEXT)
            self.screen.blit(vs, (rect.x + rect.w//2 - vs.get_width()//2,
                                  rect.y + rect.h//2 - vs.get_height()//2))
            if focused and pygame.time.get_ticks() % 1000 < 500:
                cursor_x = rect.x + rect.w//2 + vs.get_width()//2 + 2
                pygame.draw.line(self.screen,self.ACCENT,
                                 (cursor_x, rect.y + 11),
                                 (cursor_x, rect.y + rect.h - 11), 2)

        # Hint giới hạn
        hint = self.font_hint.render("Hang/Cot: 5-50  |  Kich thuoc: 5-200cm", True, (80,90,120))
        self.screen.blit(hint, (cx-hint.get_width()//2, cy+2))

        # Preset (2 hàng × 3 cột)
        for i,(label,*_) in enumerate(self.PRESETS):
            r = self._preset_rect(cx, cy, i)
            pygame.draw.rect(self.screen,(28,32,48),r,border_radius=5)
            pygame.draw.rect(self.screen,self.BORDER,r,1,border_radius=5)
            s = self.font_hint.render(label, True, self.MUTED)
            self.screen.blit(s,(r.x+r.w//2-s.get_width()//2,
                                r.y+r.h//2-s.get_height()//2))

        # Start button
        sr = self._start_rect(cx, cy)
        pygame.draw.rect(self.screen, self.ACCENT2, sr, border_radius=10)
        s = self.font_btn.render("KHOI DONG HE THONG  ->",True,(255,255,255))
        self.screen.blit(s,(sr.x+sr.w//2-s.get_width()//2,
                            sr.y+sr.h//2-s.get_height()//2))

        h = self.font_hint.render(
            "Tab = chuyen o  |  Enter = bat dau", True, self.MUTED)
        self.screen.blit(h,(cx-h.get_width()//2, cy+168))


# ─────────────────────────────────────────────────
#  APPLICATION CHÍNH
# ─────────────────────────────────────────────────
class Application(object):

    STATE_IDLE    = "IDLE"
    STATE_MOVING  = "MOVING"
    STATE_ARRIVED = "ARRIVED"
    STATE_BLOCKED = "BLOCKED"
    STATE_REPLAN  = "REPLAN"
    STATE_NO_PATH = "NO PATH"
    STATE_COMPUTING = "COMPUTING"

    DD_Y = 8
    DD_W = 260
    DD_H = 30

    def __init__(self, screenSize=[1400, 800], default_broker_ip="192.168.2.9"):
        self.default_broker_ip = default_broker_ip
        self.graphic   = Graphics(screenSize)
        self.running   = True
        self._restart  = False          # FIX: flag ESC thay vì đệ quy
        self.clock     = pygame.time.Clock()
        self.input     = Input()

        rows, cols, self.cell_cm = SetupScreen(self.graphic.screen).run()

        self.map = Maps(rows=rows+2, cols=cols+2)
        self.map.random_map(obstacle_prob=0.18)

        W = self.graphic.screen.get_width()
        H = self.graphic.screen.get_height()
        start_px = turn2pixel(self.map.map, H, W, 1, 1)

        # FIX: auto-scale AMR size và speed theo kích thước ô pixel
        cell_px_w = W / (cols + 1)
        cell_px_h = H / (rows + 1)
        cell_px   = min(cell_px_w, cell_px_h)
        amr_size  = max(8, int(cell_px * 0.55))
        amr_speed = max(2, int(cell_px * 0.18))

        self.amr          = Amrs(
            amrDimension  = [amr_size, int(amr_size*0.8)],
            position      = list(start_px)
        )
        self.amr.speed    = amr_speed
        self.amr.node_pos = (1, 1)

        self.sensor    = Sensors()
        self.processor = Processors()
        self.actuator  = Actuators()

        self.goal_node   = None
        self.state       = self.STATE_IDLE
        self.auto_run    = False
        self.show_field  = False
        self.show_hud    = True # Toggle hiển thị các bảng thông tin (HUD)
        self.show_head   = True # Toggle hiển thị đầu xe (mũi tên hướng)
        
        self._pathfind_done = False
        self._pathfind_result = False
        self._replan_done = False
        self._replan_result = False

        # Dropdown
        self.dd_open     = False
        self.DD_X        = 260
        self._dd_main    = pygame.Rect(self.DD_X, self.DD_Y,
                                       self.DD_W, self.DD_H)
        self._dd_options = []

        # FIX: cache field overlay surface
        self._field_surf  = None
        self._field_dirty = True

        self._map_surf    = None
        self._map_dirty   = True

        # MQTT — tùy chọn kết nối Pi5
        self.mqtt         = None
        self._mqtt_status = "MQTT: OFF"
        self._pi5_online  = False
        self.amr_target_pos = None

        # Animation
        self.animator     = AlgoAnimator()
        
        # Map Editor
        self.editor       = MapEditor()
        self._save_name   = ""      # Tên file khi lưu

        # Multi-Waypoint
        self.waypoints    = WaypointManager()

    # ── MQTT ─────────────────────────────────────

    def connect_mqtt(self, broker_ip="localhost"):
        try:
            from network.laptop_mqtt import LaptopMQTT
            self.mqtt = LaptopMQTT(broker_ip=broker_ip)
            ok = self.mqtt.connect()
            self._mqtt_status = (f"MQTT:{broker_ip}" if ok else "MQTT:FAIL")
            return ok
        except Exception as e:
            self._mqtt_status = "MQTT:ERR"
            print(f"[MQTT] {e}"); return False

    def _poll_mqtt(self, W, H):
        if self.mqtt is None:
            return
        if not self.mqtt.connected:
            self._mqtt_status = "MQTT:DISC"
            self._sent_cell_mm = None
            return

        # Tự động gửi kích thước ô lên Pi5 khi kết nối hoặc khi thay đổi
        target_cell_mm = self.cell_cm * 10
        if getattr(self, '_sent_cell_mm', None) != target_cell_mm:
            self.mqtt.send_cell_config(target_cell_mm)
            self._sent_cell_mm = target_cell_mm

        for ev in self.mqtt.poll():
            t = ev.get("type","")
            if t == "position":
                r,c = ev["row"], ev["col"]
                h   = ev.get("heading", None)
                if 0<=r<self.map.rows and 0<=c<self.map.cols:
                    self.amr.node_pos = (round(r), round(c))
                    px,py = turn2pixel(self.map.map,H,W,r,c)
                    self.amr_target_pos = [px,py]
                    if self.amr.pos is None:
                        self.amr.pos = [px,py]
                    # Đồng bộ hướng (đầu xe) ảo với thực tế
                    if h is not None:
                        # Hướng Pi5: 0=Bắc, 90=Đông, 180=Nam, 270=Tây
                        # Hướng ảo (Laptop): Lên=90, Phải=0, Xuống=270, Trái=180
                        mapping = {0: 90, 90: 0, 180: 270, 270: 180}
                        if h in mapping:
                            self.amr.heading = mapping[h]
                    # Thêm vết đường đi cho xe ảo
                    self.amr.path_points.append((px,py))
                    if len(self.amr.path_points) > 500:
                        self.amr.path_points = self.amr.path_points[-500:]
            elif t == "obstacle":
                r,c = ev["row"], ev["col"]
                if self.map.is_free(r,c):
                    self.map.add_obstacle(r,c)
                    self._field_dirty = True
                    self._map_dirty   = True
                    print(f"[MQTT] Obstacle ({r},{c}) — Replanning...")
                    if self.processor.has_goal():
                        found = self.processor.replan(
                            self.map.map, self.amr.node_pos)
                        if found:
                            self.mqtt.send_path(self.processor.full_path)
                        else:
                            self.state = self.STATE_NO_PATH
            elif t == "status":
                state = ev.get("state", "?")
                step  = ev.get("step", 0)
                total = ev.get("total", 0)
                self._mqtt_status = f"Pi5:{state}"
                # Cập nhật bước đi trong processor để giao diện hiển thị đúng
                if hasattr(self.processor, '_cur') and self.processor._cur:
                    self.processor._cur._idx = step
                if state == "ARRIVED":
                    self.state = self.STATE_ARRIVED
                    self.auto_run = False
                    if self.amr_target_pos:
                        self.amr.pos = list(self.amr_target_pos)
                elif state == "MOVING":
                    self.state = self.STATE_MOVING
            elif t == "heartbeat_pi5":
                self._pi5_online  = True
                self._mqtt_status = f"MQTT:{self.mqtt.broker_ip} OK"

    # ── Vòng lặp chính ──────────────────────────

    def run(self):
        self.initialize()
        while self.running:
            if self._restart:
                self._restart = False
                if self.mqtt: self.mqtt.disconnect()
                self.__init__([self.graphic.screen.get_width(),
                               self.graphic.screen.get_height()])
                self.initialize()

            W = self.graphic.screen.get_width()
            H = self.graphic.screen.get_height()

            self._handle_input(W, H)
            if not self.running: break
            if self._restart:    continue

            # MQTT poll
            self._poll_mqtt(W, H)

            # Animation tick
            if self.animator.is_loaded():
                self.animator.tick()

            # Handle background task completions
            if self._pathfind_done:
                self._pathfind_done = False
                self.state = self.STATE_IDLE if self._pathfind_result else self.STATE_NO_PATH
                self._field_dirty = True
                
            if self._replan_done:
                self._replan_done = False
                if self._replan_result:
                    self._field_dirty = True
                    valid_dirs = self.sensor.sense(self.map.map)
                    chosen = self.processor.cycle(self.amr.node_pos, valid_dirs)
                    if chosen is None:
                        self.state = self.STATE_NO_PATH
                        self.auto_run = False
                    else:
                        self.state = self.STATE_MOVING
                else:
                    self.state = self.STATE_NO_PATH
                    self.auto_run = False

            # Waypoint auto-advance
            if (self.waypoints.active
                    and self.state == self.STATE_ARRIVED
                    and not self.waypoints.is_done()):
                has_next = self.waypoints.advance()
                if has_next:
                    next_g = self.waypoints.current_goal()
                    if next_g:
                        self.goal_node = next_g
                        self._run_pathfind()
                        if self.processor.full_path:
                            self.state    = self.STATE_MOVING
                            self.auto_run = True
                            valid = self.sensor.sense(self.map.map)
                            self._do_cycle(valid, W, H)

            # SENSOR — Chỉ cập nhật từ sensor nội bộ khi OFFLINE (không kết nối Pi5)
            # Khi ONLINE, vị trí xe được cập nhật từ MQTT (Pi5 gửi về)
            if not (self.mqtt and self.mqtt.connected):
                self.sensor.update_from_pixel(self.amr.pos, self.map.map, W, H)
                self.amr.node_pos = self.sensor.node_pos
            else:
                self.sensor.node_pos = self.amr.node_pos
            valid_dirs = self.sensor.sense(self.map.map)

            # PROCESSOR + ACTUATOR
            self._update_movement(valid_dirs, W, H)

            # Interpolate draw heading towards logical heading (shortest path LERP)
            current_dh = getattr(self.amr, 'draw_heading', self.amr.heading)
            target_h = self.amr.heading
            diff = (target_h - current_dh + 180) % 360 - 180
            if abs(diff) > 0.5:
                self.amr.draw_heading = (current_dh + diff * 0.04) % 360
            else:
                self.amr.draw_heading = target_h

            # DRAW
            self._draw(valid_dirs, W, H)
            pygame.display.flip()
            self.clock.tick(60)

        if self.mqtt: self.mqtt.disconnect()
        pygame.quit()
        sys.exit()

    def initialize(self):
        pass

    def update(self):
        pass

    # ── Di chuyển ────────────────────────────────

    def _smooth_move_to_target(self):
        if not self.amr_target_pos:
            return
        cx, cy = self.amr.pos[0], self.amr.pos[1]
        tx, ty = self.amr_target_pos[0], self.amr_target_pos[1]
        dx = tx - cx
        dy = ty - cy
        dist = (dx**2 + dy**2) ** 0.5
        if dist > 0.5:
            # LERP with easing factor 0.15 to smooth out 10Hz MQTT position packets
            self.amr.pos[0] += dx * 0.15
            self.amr.pos[1] += dy * 0.15
        else:
            self.amr.pos[0] = tx
            self.amr.pos[1] = ty

    def _update_movement(self, valid_dirs, W, H):
        if self.mqtt and self.mqtt.connected:
            # Ở chế độ MQTT, di chuyển mượt theo tọa độ nhận được
            self._smooth_move_to_target()
            return

        if self.state != self.STATE_MOVING:
            return

        if self.actuator.moving:
            arrived = self.actuator.execute(self.amr, self.map.map, W, H)
            # FIX: giới hạn path_points tránh tốn RAM
            if len(self.amr.path_points) > 500:
                self.amr.path_points = self.amr.path_points[-500:]

            if arrived:
                self.processor.confirm_move()
                if self.processor.is_done():
                    self.state    = self.STATE_ARRIVED
                    self.auto_run = False
                elif self.auto_run:
                    self._do_cycle(valid_dirs, W, H)
                else:
                    # FIX: reset về IDLE sau mỗi bước thủ công
                    self.state = self.STATE_IDLE
        else:
            # actuator không moving nhưng state MOVING
            if self.auto_run and not self.processor.is_done():
                self._do_cycle(valid_dirs, W, H)
            elif self.processor.is_done():
                self.state    = self.STATE_ARRIVED
                self.auto_run = False
            else:
                # FIX: không bị kẹt — reset về IDLE
                self.state = self.STATE_IDLE

    # ── Reactive cycle ───────────────────────────

    def _do_cycle(self, valid_dirs, W, H):
        if not self.processor.has_goal():
            self.state = self.STATE_IDLE
            return
        chosen = self.processor.cycle(self.amr.node_pos, valid_dirs)
        if chosen is None:
            self.state = self.STATE_COMPUTING
            def worker(map_data, pos):
                res = self.processor.replan(map_data, pos)
                self._replan_result = res
                self._replan_done = True
                
            t = threading.Thread(target=worker, args=(self.map.map, self.amr.node_pos))
            t.daemon = True
            t.start()
            return
            
        next_node = self.processor.next_node()
        if next_node:
            self.actuator.set_target(next_node, self.map.map, W, H)
            self.state = self.STATE_MOVING

    # ── Pathfind ────────────────────────────────

    def _run_pathfind(self):
        if not self.goal_node or self.state in (self.STATE_MOVING, self.STATE_COMPUTING):
            return
        # Waypoint mode: dùng current waypoint goal
        if self.waypoints.active:
            g = self.waypoints.current_goal()
            if g: self.goal_node = g
            
        self.state = self.STATE_COMPUTING
        
        def worker(map_data, start, goal):
            res = self.processor.set_goal(map_data, start, goal)
            self._pathfind_result = res
            self._pathfind_done = True
            
        t = threading.Thread(target=worker, args=(self.map.map, self.amr.node_pos, self.goal_node))
        t.daemon = True
        t.start()

    # ── Switch thuật toán ────────────────────────

    def _switch_algo(self, idx, W, H):
        had_goal = self.goal_node is not None
        self.actuator.cancel()
        self.auto_run     = False
        self.state        = self.STATE_IDLE
        self._field_dirty = True
        self.processor.switch(idx)
        if had_goal:
            self._run_pathfind()

    # ── Reset ────────────────────────────────────

    def _reset(self, W, H):
        self.actuator.cancel()
        self.processor.reset_current()
        self.goal_node    = None
        self.state        = self.STATE_IDLE
        self.auto_run     = False
        self.dd_open      = False
        self._field_dirty = True
        self._map_dirty   = True
        # Reset animator nếu đang chạy
        if self.animator.is_loaded():
            self.animator.reset()
        start_px = turn2pixel(self.map.map, H, W, 1, 1)
        self.amr.pos         = list(start_px)
        self.amr.heading     = 90
        self.amr.draw_heading = 90
        self.amr_target_pos  = None
        self.amr.node_pos    = (1, 1)
        self.amr.path_points = [tuple(start_px)]
        if self.mqtt and self.mqtt.connected:
            self.mqtt.send_command("RESET", row=1, col=1)

    # ── Input ────────────────────────────────────

    def _handle_input(self, W, H):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.VIDEORESIZE:
                # Cập nhật màn hình mới và đánh dấu dirty để vẽ lại
                self._map_dirty   = True
                self._field_dirty = True

            # ── CHUỘT TRÁI ──
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                consumed = False

                # Editor: kéo vẽ tường
                if self.editor.active:
                    self.editor.on_mouse_down(1, (mx,my), self.map, W, H)
                    self.processor.full_path = []
                    self._field_dirty = True
                    self._map_dirty   = True
                    consumed = True

                # Dropdown main button
                elif self.show_hud and self._dd_main.collidepoint(mx, my):
                    self.dd_open = not self.dd_open
                    consumed = True

                # Dropdown options
                elif self.show_hud and self.dd_open:
                    for i, rect in enumerate(self._dd_options):
                        if rect.collidepoint(mx, my):
                            self._switch_algo(i, W, H)
                            self.dd_open = False
                            consumed = True
                            break
                    if not consumed:
                        self.dd_open = False
                        consumed = True

                # Toggle vật cản bình thường
                if not consumed and self.state != self.STATE_MOVING:
                    node = turn2node(self.map.map, W, H, mx, my)
                    if (node != self.amr.node_pos
                            and node != self.goal_node
                            and node not in self.waypoints.waypoints):
                        self.map.toggle_obstacle(node[0], node[1])
                        self.processor.full_path = []
                        self._field_dirty = True
                        self._map_dirty   = True
                        self.state = self.STATE_IDLE

            # ── CHUỘT PHẢI ──
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                mx, my = event.pos
                mods   = pygame.key.get_mods()
                self.dd_open = False

                if self.editor.active:
                    self.editor.on_mouse_down(3, (mx,my), self.map, W, H)
                    self.processor.full_path = []
                    self._field_dirty = True
                    self._map_dirty   = True
                elif (mods & pygame.KMOD_CTRL) and self.waypoints.active:
                    node = turn2node(self.map.map, W, H, mx, my)
                    if (self.map.is_free(node[0], node[1])
                            and node != self.amr.node_pos):
                        if self.waypoints.add(node):
                            print(f"[WP] Waypoint {len(self.waypoints)}: {node}")
                elif self.state != self.STATE_MOVING:
                    node = turn2node(self.map.map, W, H, mx, my)
                    if (self.map.is_free(node[0], node[1])
                            and node != self.amr.node_pos):
                        self.goal_node    = node
                        self.processor.full_path = []
                        self._field_dirty = True
                        self.state        = self.STATE_IDLE
                        if self.waypoints.active:
                            self.waypoints.clear()

            # ── MOUSE MOTION / UP (editor drag) ──
            elif event.type == pygame.MOUSEMOTION:
                if self.editor.active and pygame.mouse.get_pressed()[0]:
                    self.editor.on_mouse_motion(event.pos, self.map, W, H)
                    self.processor.full_path = []
                    self._field_dirty = True
                    self._map_dirty   = True
                elif self.editor.active and pygame.mouse.get_pressed()[2]:
                    self.editor.on_mouse_motion(event.pos, self.map, W, H)
                    self.processor.full_path = []
                    self._field_dirty = True
                    self._map_dirty   = True

            elif event.type == pygame.MOUSEBUTTONUP:
                self.editor.on_mouse_up()

            # ── PHÍM ──
            elif event.type == pygame.KEYDOWN:
                self.dd_open = False

                # 1-6: chuyển thuật toán
                for i, k in enumerate([pygame.K_1,pygame.K_2,pygame.K_3,
                                        pygame.K_4,pygame.K_5,pygame.K_6]):
                    if event.key == k:
                        self._switch_algo(i, W, H); break

                # SPACE: pathfind
                if event.key == pygame.K_SPACE:
                    self._run_pathfind()

                # ENTER: FIX — 1 bước thủ công, hoạt động lặp được
                elif event.key == pygame.K_RETURN:
                    if (self.processor.full_path
                            and not self.processor.is_done()
                            and self.state == self.STATE_IDLE):
                        if self.mqtt and self.mqtt.connected:
                            # Chuyển giao đường đi cho Pi5
                            self.mqtt.send_path(self.processor.full_path)
                            self.state = self.STATE_MOVING
                        else:
                            valid_dirs = self.sensor.sense(self.map.map)
                            self._do_cycle(valid_dirs, W, H)

                # A: toggle auto
                elif event.key == pygame.K_a:
                    if (self.processor.full_path
                            and not self.processor.is_done()):
                        self.auto_run = not self.auto_run
                        if self.auto_run and self.state == self.STATE_IDLE:
                            self.state = self.STATE_MOVING
                            if self.mqtt and self.mqtt.connected:
                                self.mqtt.send_path(self.processor.full_path)
                            else:
                                valid_dirs = self.sensor.sense(self.map.map)
                                self._do_cycle(valid_dirs, W, H)
                        elif not self.auto_run:
                            if self.mqtt and self.mqtt.connected:
                                self.mqtt.send_stop()

                # F: toggle field overlay
                elif event.key == pygame.K_f:
                    self.show_field = not self.show_field

                # H: toggle HUD panels
                elif event.key == pygame.K_h:
                    self.show_hud = not self.show_hud

                # T: toggle car head marker (đầu xe)
                elif event.key == pygame.K_t:
                    self.show_head = not self.show_head

                # Z: Animation thuật toán hiện tại
                elif event.key == pygame.K_z:
                    if self.animator.is_loaded() and not self.animator.done:
                        self.animator.reset()
                    if self.processor.full_path and self.goal_node:
                        cur = self.processor._cur
                        self.animator.load(
                            algo_name     = cur.NAME,
                            algo_color    = cur.COLOR,
                            algo_desc     = cur.DESC,
                            exploration_log = cur.exploration_log,
                            path          = cur.path,
                            map_data      = self.map.map,
                        )
                        self._bench_open = False
                        print(f"[Animation] {cur.NAME}: {len(cur.exploration_log)} ô khám phá")

                # P: Pause/resume animation
                elif event.key == pygame.K_p:
                    if self.animator.is_loaded():
                        self.animator.toggle_pause()

                # S: Skip animation
                elif event.key == pygame.K_s:
                    if self.animator.is_loaded() and not self.animator.done:
                        self.animator.skip_to_end()

                # ← →: Thay đổi tốc độ animation
                elif event.key == pygame.K_LEFT:
                    speeds = ["slow","normal","fast"]
                    idx = speeds.index(self.animator.speed)
                    self.animator.set_speed(speeds[max(0, idx-1)])
                elif event.key == pygame.K_RIGHT:
                    speeds = ["slow","normal","fast"]
                    idx = speeds.index(self.animator.speed)
                    self.animator.set_speed(speeds[min(2, idx+1)])

                # E: Toggle Map Editor
                elif event.key == pygame.K_e:
                    self.editor.toggle()
                    print(f"[Editor] {'ON' if self.editor.active else 'OFF'}")

                # Ctrl+S: Lưu bản đồ
                elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    import tkinter as tk
                    from tkinter import simpledialog
                    try:
                        root = tk.Tk(); root.withdraw()
                        name = simpledialog.askstring("Lưu bản đồ", "Nhập tên bản đồ:")
                        root.destroy()
                    except Exception:
                        import time; name = f"map_{int(time.time())}"
                    if name:
                        self.editor.save(self.map, self.cell_cm, name)

                # Ctrl+L: Mở panel tải bản đồ
                elif event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self.editor.toggle_panel()

                # Ctrl+P: Preset bản đồ
                elif event.key == pygame.K_p and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    presets = [
                        MapEditor.make_maze(self.map.rows, self.map.cols, self.cell_cm),
                        MapEditor.make_office(self.map.rows, self.map.cols, self.cell_cm),
                        MapEditor.make_warehouse(self.map.rows, self.map.cols, self.cell_cm),
                    ]
                    import random
                    p = random.choice(presets)
                    self.map.map = p["data"]
                    self._reset(W, H)
                    print(f"[Editor] Preset: {p['name']}")

                # 0-9: Tải bản đồ từ panel
                elif self.editor.show_panel:
                    for digit in range(10):
                        k = getattr(pygame, f"K_{digit}")
                        if event.key == k and digit < len(self.editor.panel_maps):
                            fname = self.editor.panel_maps[digit]
                            data  = self.editor.load(fname)
                            if data:
                                self.map.rows = data["rows"]
                                self.map.cols = data["cols"]
                                self.map.map  = data["data"]
                                self.cell_cm  = data.get("cell_mm", self.cell_cm)
                                self._reset(W, H)
                                self.editor.show_panel = False
                                print(f"[Editor] Loaded: {data['name']}")

                # W: Toggle Waypoint Mode
                elif event.key == pygame.K_w:
                    self.waypoints.toggle()
                    print(f"[WP] {'ON — Ctrl+Click phai de them diem dich' if self.waypoints.active else 'OFF'}")

                # L: Toggle loop waypoints
                elif event.key == pygame.K_l and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    if self.waypoints.active:
                        self.waypoints.toggle_loop()

                # Backspace: Xóa waypoint cuối
                elif event.key == pygame.K_BACKSPACE:
                    if self.waypoints.active and self.waypoints.waypoints:
                        self.waypoints.remove_last()
                        print(f"[WP] Còn {len(self.waypoints)} waypoints")

                # Ctrl+R: Xóa tất cả waypoints
                elif event.key == pygame.K_r and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self.waypoints.clear()
                    print("[WP] Đã xóa tất cả waypoints")

                # R: reset AMR
                elif event.key == pygame.K_r:
                    self._reset(W, H)

                # N: bản đồ mới
                elif event.key == pygame.K_n:
                    self.map.random_map(obstacle_prob=0.18)
                    self._reset(W, H)

                # M: kết nối MQTT
                elif event.key == pygame.K_m:
                    if self.mqtt and self.mqtt.connected:
                        self.mqtt.disconnect()
                        self._mqtt_status = "MQTT: OFF"
                        self.mqtt = None
                        print("[MQTT] Đã ngắt kết nối.")
                    else:
                        print(f"[MQTT] Đang kết nối tới Broker IP: {self.default_broker_ip}...")
                        self.connect_mqtt(self.default_broker_ip)

                # ESC: về setup — FIX: dùng flag, không đệ quy
                elif event.key == pygame.K_ESCAPE:
                    self._restart = True

    # ── Vẽ ──────────────────────────────────────

    def _draw(self, valid_dirs, W, H):
        self.graphic.screen.fill((13, 15, 20))

        # Field overlay — FIX: dùng cached surface
        if self.show_field:
            ed = self.processor.extra_data
            if "field" in ed:
                if self._field_dirty or self._field_surf is None:
                    self._field_surf  = self.graphic.build_field_surface(
                        ed["field"], self.map.map,
                        ed.get("field_type","cost"), W, H)
                    self._field_dirty = False
                if self._field_surf:
                    self.graphic.screen.blit(self._field_surf, (0, 0))

        # Lưới + vật cản
        if self._map_dirty or self._map_surf is None:
            self._map_surf = self.graphic.build_map_surface(self.map.map)
            self._map_dirty = False
        self.graphic.screen.blit(self._map_surf, (0, 0))

        # Đường đi
        if self.processor.full_path:
            self.graphic.draw_path(
                self.processor.full_path, self.map.map,
                self.processor.current_color)

        # Lịch sử — FIX: chỉ vẽ khi ô đủ lớn
        if self.processor.history:
            cell_px = min(W/(self.map.cols-1), H/(self.map.rows-1))
            if cell_px >= 14:
                self.graphic.draw_history_arrows(
                    self.processor.history, self.map.map)

        # Hướng hợp lệ — FIX: chỉ vẽ khi ô đủ lớn
        cell_px = min(W/(self.map.cols-1), H/(self.map.rows-1))
        if valid_dirs and self.state != self.STATE_ARRIVED and cell_px >= 12:
            self.graphic.draw_valid_dirs(
                self.amr.node_pos, valid_dirs, self.map.map)

        # Waypoints
        if self.waypoints.active and self.waypoints.waypoints:
            self.graphic.draw_waypoints(
                self.waypoints.waypoints,
                self.waypoints.current,
                self.map.map)

        # Goal (chỉ khi không có waypoints)
        if self.goal_node and not self.waypoints.active:
            self.graphic.draw_goal(self.goal_node, self.map.map)

        # AMR
        self.graphic.drawAmr(self.amr, show_head=self.show_head)

        # HUD + Panels
        if self.show_hud:
            steps_done = (self.processor.total_steps()
                          - self.processor.remaining_steps())
            self.graphic.draw_hud(
                amr_node    = self.amr.node_pos,
                status      = self.state,
                steps_done  = steps_done,
                total_steps = self.processor.total_steps(),
                cell_cm     = self.cell_cm,
                valid_dirs  = valid_dirs,
                chosen_dir  = self.processor.chosen_dir,
                algo_name   = self.processor.current_name,
                algo_color  = self.processor.current_color,
                compute_ms  = self.processor.compute_ms,
                auto_run    = self.auto_run,
                mqtt_status = self._mqtt_status,
            )

            # Dropdown — vẽ sau cùng (nổi lên trên)
            main_rect, option_rects = self.graphic.draw_dropdown(
                algo_names   = self.processor.algo_names,
                algo_colors  = [a.COLOR for a in self.processor._algos],
                selected_idx = self.processor.current_index,
                open_        = self.dd_open,
                x=self.DD_X, y=self.DD_Y,
                w=self.DD_W, h=self.DD_H,
            )
            self._dd_main    = main_rect
            self._dd_options = option_rects

            self.graphic.draw_instruction()

            # Map Editor HUD
            self.graphic.draw_editor_hud(
                active      = self.editor.active,
                mode        = self.editor.mode,
                map_changed = self.editor.map_changed,
                show_panel  = self.editor.show_panel,
                panel_maps  = self.editor.panel_maps,
                cell_mm     = self.cell_cm,
            )

            # Waypoint HUD
            if self.waypoints.active or self.waypoints.waypoints:
                self.graphic.draw_waypoint_hud(
                    active     = self.waypoints.active,
                    waypoints  = self.waypoints.waypoints,
                    current_idx= self.waypoints.current,
                    loop_mode  = self.waypoints.loop_mode,
                    cell_mm    = self.cell_cm,
                )

        # Animation overlay (trước dropdown)
        if self.animator.is_loaded():
            self.animator.draw(self.graphic.screen, self.map.map, show_hud=self.show_hud)

        pass
