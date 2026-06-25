"""
core/animator.py — Algorithm Animation
Visualize từng bước khám phá của thuật toán:
  Phase 1 EXPLORE : hiển thị từng ô được khám phá theo thứ tự
  Phase 2 TRACE   : vẽ đường đi sáng dần từ start → goal
  Phase 3 DONE    : hiển thị kết quả hoàn chỉnh

Màu sắc:
  Explored (cũ)  : xám xanh mờ
  Frontier (mới) : sáng flash theo màu thuật toán
  Path            : màu thuật toán, sáng rõ
  Start / Goal    : cố định
"""

import pygame
from utils.utils import turn2pixel


# Tốc độ animation (ms giữa 2 frame)
SPEEDS = {
    "slow":   120,
    "normal":  50,
    "fast":    15,
}


class AlgoAnimator:

    PHASE_EXPLORE = "EXPLORE"
    PHASE_TRACE   = "TRACE"
    PHASE_DONE    = "DONE"

    def __init__(self):
        self.reset()

    def load(self, algo_name, algo_color, algo_desc,
             exploration_log, path, map_data):
        """Nạp dữ liệu một thuật toán để animate."""
        self.algo_name     = algo_name
        self.algo_color    = algo_color
        self.algo_desc     = algo_desc
        self.expl_log      = list(exploration_log)
        self.path          = list(path)
        self.map_data      = map_data

        self.phase         = self.PHASE_EXPLORE
        self.expl_idx      = 0     # Con trỏ trong exploration_log
        self.path_idx      = 0     # Con trỏ trong path
        self.explored_set  = set()
        self.frontier      = set()
        self.path_drawn    = []
        self.done          = False
        self._last_tick    = 0
        self.speed         = "normal"
        self.paused        = False

        # Thống kê
        self.total_explored = len(self.expl_log)
        self.total_path     = len(self.path)

    def reset(self):
        self.algo_name      = ""
        self.algo_color     = (150, 150, 150)
        self.algo_desc      = ""
        self.expl_log       = []
        self.path           = []
        self.map_data       = None
        self.phase          = self.PHASE_EXPLORE
        self.expl_idx       = 0
        self.path_idx       = 0
        self.explored_set   = set()
        self.frontier       = set()
        self.path_drawn     = []
        self.done           = False
        self._last_tick     = 0
        self.speed          = "normal"
        self.paused         = False
        self.total_explored = 0
        self.total_path     = 0

    def is_loaded(self):
        return bool(self.expl_log or self.path)

    def toggle_pause(self):
        self.paused = not self.paused

    def set_speed(self, speed: str):
        if speed in SPEEDS:
            self.speed = speed

    def tick(self):
        """
        Gọi mỗi frame. Tự động advance theo tốc độ.
        Trả về True nếu có thay đổi state.
        """
        if self.done or self.paused or not self.is_loaded():
            return False

        now  = pygame.time.get_ticks()
        wait = SPEEDS[self.speed]
        if now - self._last_tick < wait:
            return False
        self._last_tick = now

        return self._advance()

    def _advance(self):
        """Advance 1 bước animation. Trả về True nếu có thay đổi."""
        if self.phase == self.PHASE_EXPLORE:
            # Advance N cells mỗi bước (tốc độ nhanh hơn cho lưới lớn)
            n_step = max(1, len(self.expl_log) // 80)
            changed = False
            self.frontier.clear()
            for _ in range(n_step):
                if self.expl_idx >= len(self.expl_log):
                    # Hết explore → chuyển sang trace
                    self.phase = self.PHASE_TRACE
                    break
                cell = self.expl_log[self.expl_idx]
                self.explored_set.add(cell)
                self.frontier.add(cell)
                self.expl_idx += 1
                changed = True
            return changed

        elif self.phase == self.PHASE_TRACE:
            # Vẽ từng node trong path
            if self.path_idx >= len(self.path):
                self.phase = self.PHASE_DONE
                self.done  = True
                return True

            cell = self.path[self.path_idx]
            self.path_drawn.append(cell)
            self.path_idx += 1
            return True

        return False

    def skip_to_end(self):
        """Bỏ qua animation, hiện kết quả ngay."""
        self.explored_set = set(self.expl_log)
        self.frontier.clear()
        self.path_drawn   = list(self.path)
        self.phase        = self.PHASE_DONE
        self.done         = True

    # ── Vẽ ──────────────────────────────────────

    def draw(self, screen, map_data, show_hud=True):
        """Vẽ trạng thái animation hiện tại lên screen."""
        if not self.is_loaded() or map_data is None:
            return

        H = screen.get_height()
        W = screen.get_width()
        rows = len(map_data)
        cols = len(map_data[0])
        if rows < 2 or cols < 2:
            return

        cw = W / (cols - 1)
        ch = H / (rows - 1)

        # Surface alpha để không che map
        surf = pygame.Surface((W, H), pygame.SRCALPHA)

        # Vẽ ô đã explored
        ec = self.algo_color
        for (r, c) in self.explored_set:
            if map_data[r][c]: continue
            px, py = turn2pixel(map_data, H, W, r, c)
            rect = pygame.Rect(px-cw*.42, py-ch*.42, cw*.84, ch*.84)
            pygame.draw.rect(surf, (ec[0]//4, ec[1]//4, ec[2]//4, 90),
                             rect, border_radius=max(1,int(min(cw,ch)*0.1)))

        # Vẽ frontier (flash sáng)
        if self.phase == self.PHASE_EXPLORE:
            flash = (pygame.time.get_ticks() // 120) % 2 == 0
            for (r, c) in self.frontier:
                if map_data[r][c]: continue
                px, py = turn2pixel(map_data, H, W, r, c)
                rect = pygame.Rect(px-cw*.44, py-ch*.44, cw*.88, ch*.88)
                alpha = 180 if flash else 100
                pygame.draw.rect(surf, (*ec, alpha), rect,
                                 border_radius=max(1,int(min(cw,ch)*0.1)))

        screen.blit(surf, (0, 0))

        # Vẽ path đang trace (sáng, không alpha)
        for i, (r, c) in enumerate(self.path_drawn):
            px, py = turn2pixel(map_data, H, W, r, c)
            rect = pygame.Rect(px-cw*.42, py-ch*.42, cw*.84, ch*.84)
            # Gradient sáng dần từ đầu → cuối path
            brightness = 0.5 + 0.5 * (i / max(len(self.path_drawn), 1))
            col = tuple(int(c * brightness) for c in ec)
            pygame.draw.rect(screen, col, rect,
                             border_radius=max(1,int(min(cw,ch)*0.12)))

        # HUD animation
        if show_hud:
            self._draw_hud(screen, W, H)

    def _draw_hud(self, screen, W, H):
        """Hiển thị thông tin animation góc trên phải."""
        font_b = pygame.font.SysFont("consolas", 13, bold=True)
        font_s = pygame.font.SysFont("consolas", 12)
        font_xs= pygame.font.SysFont("consolas", 11)

        PW, PH = 280, 145
        px = W - PW - 8
        py = 8

        bg = pygame.Surface((PW, PH), pygame.SRCALPHA)
        bg.fill((10, 12, 22, 215))
        screen.blit(bg, (px, py))
        pygame.draw.rect(screen, self.algo_color, (px, py, PW, PH), 1, border_radius=6)

        # Tên thuật toán
        t = font_b.render(self.algo_name, True, self.algo_color)
        screen.blit(t, (px+8, py+8))

        # Phase
        phase_labels = {
            self.PHASE_EXPLORE: "🔍 Đang khám phá...",
            self.PHASE_TRACE:   "✏  Truy vết đường đi...",
            self.PHASE_DONE:    "✅ Hoàn thành!",
        }
        ph_s = font_s.render(phase_labels.get(self.phase, ""), True, (200, 200, 200))
        screen.blit(ph_s, (px+8, py+28))

        # Progress bar explore
        if self.total_explored > 0:
            prog = self.expl_idx / self.total_explored
            bw   = PW - 16
            pygame.draw.rect(screen, (30, 35, 50), (px+8, py+50, bw, 10), border_radius=4)
            pygame.draw.rect(screen, self.algo_color,
                             (px+8, py+50, int(bw*prog), 10), border_radius=4)
            exp_s = font_xs.render(
                f"Kham pha: {self.expl_idx}/{self.total_explored}", True, (160,170,190))
            screen.blit(exp_s, (px+8, py+64))

        # Progress bar path
        if self.total_path > 0:
            prog2 = self.path_idx / self.total_path
            bw    = PW - 16
            pygame.draw.rect(screen, (30, 35, 50), (px+8, py+82, bw, 10), border_radius=4)
            col2  = tuple(max(0, c-80) for c in self.algo_color)
            pygame.draw.rect(screen, col2,
                             (px+8, py+82, int(bw*prog2), 10), border_radius=4)
            path_s= font_xs.render(
                f"Duong di: {self.path_idx}/{self.total_path}", True, (160,170,190))
            screen.blit(path_s, (px+8, py+96))

        # Controls
        ctrl_y = py + PH - 24
        pygame.draw.line(screen, (42,47,66), (px+4, ctrl_y-2), (px+PW-4, ctrl_y-2), 1)
        sp_label = {"slow":"CHAM","normal":"BINH THUONG","fast":"NHANH"}
        pause_txt = "▶ TIEP" if self.paused else "⏸ DUNG"
        ctrl_s = font_xs.render(
            f"[P]{pause_txt}  [←→]Toc do:{sp_label[self.speed]}  [S]Bo qua",
            True, (160, 170, 190))
        screen.blit(ctrl_s, (px+6, ctrl_y+4))
