"""
Graphic module — AMR Pathfinding Framework v4
Fix:
  - build_field_surface(): trả về Surface cache thay vì vẽ trực tiếp
  - draw_field_overlay(): deprecated, giữ compat
  - draw_path(): skip số bước khi ô quá nhỏ
  - Tất cả hàm guard khi map quá nhỏ
"""

import pygame, math, numpy
from utils.utils import (turn2pixel, transformationMatrix2d,
                         apply_transformation)


class Graphics(object):

    def __init__(self, screenSize):
        pygame.init()
        self.screen = pygame.display.set_mode(screenSize, pygame.RESIZABLE)
        pygame.display.set_caption("AMR")
        self.font_tiny  = pygame.font.SysFont("consolas", 11)
        self.font_small = pygame.font.SysFont("consolas", 13)
        self.font_med   = pygame.font.SysFont("consolas", 15, bold=True)
        self.font_big   = pygame.font.SysFont("consolas", 17, bold=True)

    # ═══════════════════════════════════════════════
    #  GỐC GIỮ NGUYÊN
    # ═══════════════════════════════════════════════

    def drawDottedLine(self, color, p0, p1, dot=5, gap=10):
        dx, dy = p1[0]-p0[0], p1[1]-p0[1]
        dist = math.hypot(dx, dy)
        if dist < 1: return
        dx /= dist; dy /= dist
        n = int(dist // (dot+gap)) + 1
        for i in range(n):
            sx = p0[0]+(dot+gap)*i*dx; sy = p0[1]+(dot+gap)*i*dy
            ex = sx+dot*dx;            ey = sy+dot*dy
            pygame.draw.line(self.screen, color, (sx,sy),(ex,ey), 2)

    def build_map_surface(self, map_data, color=(55, 60, 75)):
        """Builds and returns a cached surface for the grid and obstacles."""
        H = self.screen.get_height()
        W = self.screen.get_width()
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        
        rows = len(map_data)
        cols = len(map_data[0])
        if rows < 2 or cols < 2: return surf

        cw = W / (cols - 1); ch = H / (rows - 1)

        for row in range(rows):
            p1 = turn2pixel(map_data,H,W,row,0)
            p2 = turn2pixel(map_data,H,W,row,cols-1)
            pygame.draw.line(surf,color,p1,p2,1)
        for col in range(cols):
            p1 = turn2pixel(map_data,H,W,0,col)
            p2 = turn2pixel(map_data,H,W,rows-1,col)
            pygame.draw.line(surf,color,p1,p2,1)

        for r in range(rows):
            for c in range(cols):
                if map_data[r][c]:
                    px,py = turn2pixel(map_data,H,W,r,c)
                    rect = pygame.Rect(px-cw*.45,py-ch*.45,cw*.9,ch*.9)
                    pygame.draw.rect(surf,(145,35,35),rect,
                                     border_radius=max(1,int(min(cw,ch)*0.15)))
                    if cw > 6 and ch > 6:
                        pygame.draw.rect(surf,(210,65,65),rect,1,
                                         border_radius=max(1,int(min(cw,ch)*0.15)))
        return surf

    def drawAmr(self, amr, show_head=True):
        pts = numpy.array([[-amr.width/2,-amr.height/2],
                           [ amr.width/2,-amr.height/2],
                           [ amr.width/2, amr.height/2],
                           [-amr.width/2, amr.height/2]])
        angle = (360 - amr.draw_heading) % 360
        T  = transformationMatrix2d(rotation_deg=angle, translation=amr.pos)
        tp = apply_transformation(pts, T)
        pygame.draw.polygon(self.screen,(200,120,40),tp)
        pygame.draw.lines(self.screen,(255,180,80),True,tp,2)
        
        if show_head:
            # Vẽ mũi tên chỉ đầu xe (đầu xe luôn hướng về phía trước khi chạy)
            arrow_pts = numpy.array([[amr.width/2, -amr.height/3],
                                     [amr.width/2 + amr.width/3, 0],
                                     [amr.width/2, amr.height/3]])
            ap_arrow = apply_transformation(arrow_pts, T)
            pygame.draw.polygon(self.screen, (255, 60, 60), ap_arrow)
            
            ax = numpy.array([[0,0],[amr.width,0],[0,0],[0,amr.height]])
            ap = apply_transformation(ax, T)
            pygame.draw.line(self.screen,(255,60,60),ap[0],ap[1],2)
            pygame.draw.line(self.screen,(60,220,60),ap[2],ap[3],2)
            
        pygame.draw.circle(self.screen,amr.color,
                           (int(amr.pos[0]),int(amr.pos[1])),
                           max(2,amr.width//6))

    # ═══════════════════════════════════════════════
    #  FIELD OVERLAY — dùng cached Surface
    # ═══════════════════════════════════════════════

    def build_field_surface(self, field, map_data, field_type, W, H):
        """
        Xây dựng Surface heatmap một lần, cache lại dùng nhiều frame.
        FIX: không vẽ từng ô mỗi frame → không lag với 100x100.
        """
        rows, cols = len(map_data), len(map_data[0])
        if rows < 2 or cols < 2: return None
        cw = W/(cols-1); ch = H/(rows-1)

        vals = [field[r][c]
                for r in range(rows) for c in range(cols)
                if field[r][c] != float('inf') and map_data[r][c] == 0]
        if not vals: return None
        vmax = max(vals) or 1
        vmin = min(v for v in vals if v > 0) if any(v>0 for v in vals) else 0

        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        show_nums = (cw > 22 and ch > 18)

        for r in range(rows):
            for c in range(cols):
                if map_data[r][c] != 0: continue
                v = field[r][c]
                if v == float('inf'): continue
                t = min(1.0, v/vmax) if vmax > 0 else 0

                if field_type == "pheromone":
                    # Pheromone: vàng nhạt (thấp) → vàng đậm/cam (cao)
                    red   = int(255 * t)
                    green = int(180 * t)
                    blue  = 0
                elif field_type == "q_value":
                    # Q-value: xanh đậm (thấp) → xanh sáng (cao)
                    red   = 0
                    green = int(120 + 135 * t)
                    blue  = int(200 * (1-t))
                else:
                    # Cost field (GWF): đỏ→xanh
                    red   = int(180*t)
                    green = int(80*(1-t))
                    blue  = int(180*(1-t))
                
                red   = max(0, min(255, red))
                green = max(0, min(255, green))
                blue  = max(0, min(255, blue))

                px,py = turn2pixel(map_data, H, W, r, c)
                rect = pygame.Rect(px-cw*.45,py-ch*.45,
                                   max(1,cw*.9),max(1,ch*.9))
                pygame.draw.rect(surf,(red,green,blue,50),rect,
                                 border_radius=max(1,int(min(cw,ch)*0.1)))
                if show_nums and v < 9999:
                    label = f"{int(v)}" if field_type=="cost" else f"{v:.1f}"
                    s = self.font_tiny.render(label,True,(180,180,180,150))
                    surf.blit(s,(int(px)-s.get_width()//2,
                                 int(py)-s.get_height()//2))
        return surf

    # ═══════════════════════════════════════════════
    #  VẼ PATH, GOAL, VALID DIRS, HISTORY
    # ═══════════════════════════════════════════════

    def draw_path(self, path_nodes, map_data, color=(245,200,50)):
        H = self.screen.get_height()
        W = self.screen.get_width()
        if len(path_nodes) < 2: return
        rows, cols = len(map_data), len(map_data[0])
        if rows < 2 or cols < 2: return

        cw = W/(cols-1); ch = H/(rows-1)
        show_nums = (cw > 16 and ch > 14)

        pixels = [turn2pixel(map_data,H,W,r,c) for r,c in path_nodes]
        for i in range(len(pixels)-1):
            self.drawDottedLine(color,pixels[i],pixels[i+1])

        if show_nums:
            for i,(px,py) in enumerate(pixels[1:],1):
                s = self.font_tiny.render(str(i),True,color)
                self.screen.blit(s,(int(px)+2,int(py)-11))

    def draw_goal(self, goal_node, map_data):
        H = self.screen.get_height()
        W = self.screen.get_width()
        rows, cols = len(map_data), len(map_data[0])
        if rows < 2 or cols < 2: return
        px,py = turn2pixel(map_data,H,W,goal_node[0],goal_node[1])
        cw = W/(cols-1); ch = H/(rows-1)
        rect = pygame.Rect(px-cw*.45,py-ch*.45,cw*.9,ch*.9)
        pygame.draw.rect(self.screen,(20,150,80),rect,
                         border_radius=max(1,int(min(cw,ch)*0.15)))
        pygame.draw.rect(self.screen,(80,255,150),rect,2,
                         border_radius=max(1,int(min(cw,ch)*0.15)))
        if cw > 14 and ch > 14:
            s = self.font_med.render("G",True,(255,255,255))
            self.screen.blit(s,(int(px)-s.get_width()//2,
                                int(py)-s.get_height()//2))

    def draw_valid_dirs(self, node_pos, valid_dirs, map_data):
        H = self.screen.get_height()
        W = self.screen.get_width()
        rows, cols = len(map_data), len(map_data[0])
        if rows < 2 or cols < 2: return
        cw = W/(cols-1); ch = H/(rows-1)
        DIR_DELTA = {90:(-1,0),270:(1,0),180:(0,-1),0:(0,1)}
        DIR_LABEL = {90:"↑",270:"↓",180:"←",0:"→"}
        r,c = node_pos
        show_label = (cw > 18 and ch > 16)
        for d in valid_dirs:
            dr,dc = DIR_DELTA[d]; nr,nc = r+dr,c+dc
            px,py = turn2pixel(map_data,H,W,nr,nc)
            rect = pygame.Rect(px-cw*.45,py-ch*.45,cw*.9,ch*.9)
            sf = pygame.Surface((int(max(1,cw*.9)),int(max(1,ch*.9))),
                                 pygame.SRCALPHA)
            sf.fill((0,229,255,40))
            self.screen.blit(sf,(rect.x,rect.y))
            pygame.draw.rect(self.screen,(0,229,255),rect,1,
                             border_radius=max(1,int(min(cw,ch)*0.1)))
            if show_label:
                s = self.font_small.render(DIR_LABEL[d],True,(0,229,255))
                self.screen.blit(s,(int(px)-s.get_width()//2,
                                    int(py)-s.get_height()//2))

    def draw_history_arrows(self, history, map_data):
        H = self.screen.get_height()
        W = self.screen.get_width()
        rows, cols = len(map_data), len(map_data[0])
        if rows < 2 or cols < 2: return
        LABEL = {90:"↑",270:"↓",180:"←",0:"→"}
        # FIX: chỉ vẽ 50 bước gần nhất
        for e in history[-50:]:
            px,py = turn2pixel(map_data,H,W,e["node"][0],e["node"][1])
            s = self.font_tiny.render(LABEL.get(e["chosen"],"?"),
                                      True,(100,100,200))
            self.screen.blit(s,(int(px)-s.get_width()//2,
                                int(py)-s.get_height()//2))

    # ═══════════════════════════════════════════════
    #  DROPDOWN
    # ═══════════════════════════════════════════════

    def draw_dropdown(self, algo_names, algo_colors,
                      selected_idx, open_, x, y, w, h):
        BG_BOX   = (21,  24,  32)
        BG_HOVER = (35,  40,  55)
        BORDER   = (60,  70, 100)
        TEXT_COL = (200, 200, 210)

        main_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen,BG_BOX,main_rect,border_radius=6)
        pygame.draw.rect(self.screen,
                         algo_colors[selected_idx],
                         main_rect,2,border_radius=6)
        label = f"Algo: {algo_names[selected_idx]}"
        s = self.font_small.render(label,True,algo_colors[selected_idx])
        self.screen.blit(s,(x+10,y+h//2-s.get_height()//2))
        arrow = "▲" if open_ else "▼"
        a = self.font_small.render(arrow,True,TEXT_COL)
        self.screen.blit(a,(x+w-a.get_width()-8,y+h//2-a.get_height()//2))

        option_rects = []
        if open_:
            for i,(name,color) in enumerate(zip(algo_names,algo_colors)):
                oy = y+h+i*h
                rect = pygame.Rect(x,oy,w,h)
                bg = BG_HOVER if i==selected_idx else BG_BOX
                pygame.draw.rect(self.screen,bg,rect)
                pygame.draw.rect(self.screen,
                                 color if i==selected_idx else BORDER,
                                 rect,1)
                pygame.draw.circle(self.screen,color,(x+12,oy+h//2),5)
                ns = self.font_small.render(name,True,
                     color if i==selected_idx else TEXT_COL)
                self.screen.blit(ns,(x+22,oy+h//2-ns.get_height()//2))
                option_rects.append(rect)

        return main_rect, option_rects

    # ═══════════════════════════════════════════════
    #  HUD & INSTRUCTION
    # ═══════════════════════════════════════════════

    def draw_hud(self, amr_node, status, steps_done, total_steps,
                 cell_cm, valid_dirs, chosen_dir,
                 algo_name, algo_color, compute_ms, auto_run,
                 mqtt_status="MQTT: OFF"):
        STATUS_COLOR = {
            "IDLE":    (150,150,150),"MOVING": (80,220,120),
            "ARRIVED": (80,180,255),"BLOCKED":(255,80,80),
            "REPLAN":  (255,200,50),"NO PATH":(255,80,80),
        }
        DIR_NAME = {90:"LEN",270:"XUONG",180:"TRAI",0:"PHAI",None:"-"}
        mode = "AUTO [A]" if auto_run else "MANUAL [ENTER]"
        mqtt_color = (80,220,120) if "OK" in mqtt_status else (150,150,150)
        lines = [
            ("Algo      : ", algo_name,                       algo_color),
            ("AMR node  : ", f"({amr_node[0]}, {amr_node[1]})",(200,200,200)),
            ("Status    : ", status,
             STATUS_COLOR.get(status,(200,200,200))),
            ("Buoc      : ", f"{steps_done}/{total_steps}",   (200,200,200)),
            ("O (cm)    : ", str(cell_cm),                    (200,200,200)),
            ("Tinh toan : ", f"{compute_ms} ms",              (160,200,160)),
            ("Huong HLe : ",
             " ".join(str(d) for d in valid_dirs) or "-",     (0,229,255)),
            ("Chon      : ", DIR_NAME.get(chosen_dir,"-"),    (255,200,50)),
            ("Mode      : ", mode,                            (160,160,220)),
            ("Network   : ", mqtt_status,                     mqtt_color),
        ]
        ph = len(lines)*21+16
        panel = pygame.Surface((280,ph),pygame.SRCALPHA)
        panel.fill((15,20,30,235))
        self.screen.blit(panel,(8,8))
        pygame.draw.rect(self.screen,(100,120,160),(8,8,280,ph),1,border_radius=4)
        for i,(label,value,color) in enumerate(lines):
            ls = self.font_small.render(label,True,(160,170,190))
            vs = self.font_small.render(value,True,color)
            self.screen.blit(ls,(16,16+i*21))
            self.screen.blit(vs,(16+ls.get_width(),16+i*21))

    def draw_instruction(self):
        lines = [
            "Chuot trai  : Dat/xoa vat can",
            "Chuot phai  : Dat dich (Goal)",
            "SPACE       : Tinh duong (Pathfind)",
            "ENTER       : 1 buoc thu cong",
            "A           : Tu dong chay / dung",
            "Z           : ANIMATION thuat toan hien tai",
            "P / S       : Pause / Skip animation",
            "< / >       : Toc do animation",
            "F           : Field overlay (GWF/ACO/QL)",
            "1-6         : Chuyen thuat toan",
            "H           : An/hien panel thong tin (HUD)",
            "T           : An/hien dau xe (Head marker)",
            "R/N/ESC     : Reset / Ban do moi / Cau hinh",
        ]
        H = self.screen.get_height()
        pw,ph = 350, len(lines)*18+16
        panel = pygame.Surface((pw,ph),pygame.SRCALPHA)
        panel.fill((15,20,30,235))
        self.screen.blit(panel,(8,H-ph-8))
        pygame.draw.rect(self.screen,(100,120,160),(8,H-ph-8,pw,ph),1,border_radius=4)
        for i,line in enumerate(lines):
            s = self.font_tiny.render(line,True,(200,210,220))
            self.screen.blit(s,(16,H-ph+8+i*18))

    # ═══════════════════════════════════════════════
    #  MAP EDITOR
    # ═══════════════════════════════════════════════

    def draw_editor_hud(self, active, mode, map_changed, show_panel,
                        panel_maps, cell_mm):
        """Hiển thị trạng thái editor góc trên phải."""
        W = self.screen.get_width()
        font_b = pygame.font.SysFont("consolas", 14, bold=True)
        font_s = pygame.font.SysFont("consolas", 12)
        font_xs= pygame.font.SysFont("consolas", 11)

        if not active and not show_panel:
            # Chỉ hiện hint nhỏ
            s = self.font_tiny.render("[E] Map Editor", True, (60, 70, 100))
            self.screen.blit(s, (W - s.get_width() - 8, 8))
            return

        PW, PH = 250, 130 if not show_panel else 130 + len(panel_maps)*20 + 20
        px = W - PW - 8
        py = 8
        bg = pygame.Surface((PW, PH), pygame.SRCALPHA)
        bg.fill((10, 14, 26, 220))
        self.screen.blit(bg, (px, py))
        col = (255, 200, 50) if active else (60, 70, 100)
        pygame.draw.rect(self.screen, col, (px, py, PW, PH), 1, border_radius=6)

        # Title
        title = font_b.render(
            "✏ MAP EDITOR" if active else "MAP EDITOR",
            True, col)
        self.screen.blit(title, (px+8, py+8))

        # Mode & status
        mode_col = (239,68,68) if mode=="DRAW" else (100,200,100)
        mode_s = font_s.render(
            f"Mode: {'VẼ TƯỜNG' if mode=='DRAW' else 'XÓA TƯỜNG'}",
            True, mode_col)
        self.screen.blit(mode_s, (px+8, py+28))

        unsaved = font_xs.render(
            "* Chưa lưu" if map_changed else "Đã lưu",
            True, (255,200,50) if map_changed else (80,180,80))
        self.screen.blit(unsaved, (px+8, py+46))

        hints = [
            "Keo chuot trai : Ve tuong",
            "Keo chuot phai : Xoa tuong",
            "Ctrl+S : Luu ban do",
            "Ctrl+L : Danh sach ban do",
            "Ctrl+P : Preset (maze/office/wh)",
        ]
        for i, h in enumerate(hints):
            s = self.font_tiny.render(h, True, (160, 170, 190))
            self.screen.blit(s, (px+8, py+64+i*14))

        if show_panel and panel_maps:
            sep_y = py + 130
            pygame.draw.line(self.screen, (42,47,66),
                             (px+4, sep_y), (px+PW-4, sep_y), 1)
            load_t = font_xs.render("DANH SACH BAN DO:", True, (100,120,180))
            self.screen.blit(load_t, (px+8, sep_y+4))
            for i, fname in enumerate(panel_maps[:8]):
                name = fname.replace('.json','')[:28]
                key_s= font_xs.render(f"[{i}]", True, (0,229,255))
                nm_s = font_xs.render(name, True, (180,190,210))
                self.screen.blit(key_s, (px+8,  sep_y+20+i*20))
                self.screen.blit(nm_s,  (px+34, sep_y+20+i*20))

    # ═══════════════════════════════════════════════
    #  WAYPOINTS
    # ═══════════════════════════════════════════════

    def draw_waypoints(self, waypoints, current_idx, map_data):
        """Vẽ các waypoint được đánh số trên map."""
        H = self.screen.get_height()
        W = self.screen.get_width()
        rows = len(map_data); cols = len(map_data[0])
        if rows < 2 or cols < 2: return
        cw = W/(cols-1); ch = H/(rows-1)

        font_wp = pygame.font.SysFont("Courier", max(9, int(min(cw,ch)*0.5)),
                                       bold=True)
        for i, (r, c) in enumerate(waypoints):
            px, py = turn2pixel(map_data, H, W, r, c)
            done   = (i < current_idx)
            active = (i == current_idx)

            # Màu theo trạng thái
            if done:
                fill = (30, 80, 30);  border = (60, 160, 60)
            elif active:
                flash = (pygame.time.get_ticks()//300)%2==0
                fill  = (0,180,80) if flash else (0,120,60)
                border= (80,255,140)
            else:
                fill  = (20, 40, 80); border = (60,120,200)

            rect = pygame.Rect(px-cw*.42, py-ch*.42, cw*.84, ch*.84)
            pygame.draw.rect(self.screen, fill, rect, border_radius=4)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=4)

            # Số thứ tự
            num_s = font_wp.render(str(i+1), True, (255,255,255))
            self.screen.blit(num_s, (int(px)-num_s.get_width()//2,
                                     int(py)-num_s.get_height()//2))

    def draw_waypoint_hud(self, active, waypoints, current_idx,
                          loop_mode, cell_mm):
        """Panel thông tin waypoint góc trên."""
        if not active and not waypoints:
            return
        W = self.screen.get_height()
        font_b = pygame.font.SysFont("consolas", 13, bold=True)
        font_s = pygame.font.SysFont("consolas", 12)
        font_xs= pygame.font.SysFont("consolas", 11)

        PW = 240
        px = self.screen.get_width()//2 - PW//2
        py = 8
        PH = 26 + len(waypoints)*18 + 30 if waypoints else 60

        bg = pygame.Surface((PW, PH), pygame.SRCALPHA)
        bg.fill((10,14,26,210))
        self.screen.blit(bg, (px, py))
        pygame.draw.rect(self.screen, (60,120,220),
                         (px,py,PW,PH), 1, border_radius=6)

        mode_col = (60,200,120) if active else (100,100,120)
        t = font_b.render(
            f"WAYPOINT {'ON' if active else 'OFF'} "
            f"[{'LOOP' if loop_mode else 'ONCE'}]",
            True, mode_col)
        self.screen.blit(t, (px+8, py+6))

        if not waypoints:
            s = font_xs.render("Ctrl+Click phai de them waypoint",
                               True, (160, 170, 190))
            self.screen.blit(s, (px+8, py+24))
            return

        for i,(r,c) in enumerate(waypoints):
            done   = i < current_idx
            active_wp = i == current_idx
            col    = (60,160,60) if done else \
                     (80,255,140) if active_wp else (100,120,180)
            prefix = "✓" if done else ("►" if active_wp else f"{i+1}.")
            s = font_s.render(f" {prefix} ({r:2d},{c:2d})", True, col)
            self.screen.blit(s, (px+6, py+24+i*18))

        hints = font_xs.render(
            "[W]OFF  [L]Loop  [BS]Del  [CR]Clear",
            True, (160, 170, 190))
        self.screen.blit(hints, (px+6, py+PH-18))

