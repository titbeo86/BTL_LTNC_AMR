"""
Processor module — Framework 6 thuật toán pathfinding AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1] BFS             — Breadth-First Search (cổ điển)
  [2] Dijkstra        — Optimal shortest path (cổ điển)
  [3] Q-Learning      — Reinforcement Learning (AI học tăng cường)
  [4] Greedy          — Best-First Greedy (cổ điển)
  [5] GWF             — Gradient Wavefront Field (TỰ THIẾT KẾ)
  [6] ACO             — Ant Colony Optimization (AI bầy đàn)
"""

from collections import deque
import heapq
import time
import random
import numpy as np


# ═══════════════════════════════════════════════════
#  BASE CLASS
# ═══════════════════════════════════════════════════
class BasePathfinder:
    NAME  = "Base"
    DESC  = ""
    COLOR = (150, 150, 150)

    DIR_DELTA = {
        90:  (-1,  0),   # Lên
        270: ( 1,  0),   # Xuống
        180: ( 0, -1),   # Trái
        0:   ( 0,  1),   # Phải
    }

    def __init__(self):
        self.path           = []
        self.goal           = None
        self._idx           = 0
        self.history        = []
        self.chosen_dir     = None
        self.extra_data     = {}
        self.compute_ms     = 0
        self._counter       = 0
        self.exploration_log= []  # [(r,c),...] thứ tự khám phá (cho animation)

    # ── API chung ──────────────────────────────────
    def set_goal(self, map_data, start, goal):
        self.goal    = goal
        self._idx    = 0
        self.history = []
        self.exploration_log = []
        t0 = time.perf_counter()
        ok = self._compute(map_data, start, goal)
        self.compute_ms = round((time.perf_counter() - t0) * 1000, 2)
        return ok

    def replan(self, map_data, current_pos):
        if self.goal is None:
            return False
        self._idx = 0
        self.exploration_log = []
        t0 = time.perf_counter()
        ok = self._compute(map_data, current_pos, self.goal)
        self.compute_ms = round((time.perf_counter() - t0) * 1000, 2)
        return ok

    def _compute(self, map_data, start, goal):
        raise NotImplementedError

    def cycle(self, current_node, valid_dirs):
        """
        1 chu kỳ reactive:
          - Chọn hướng tối ưu từ tập valid_dirs dựa trên path
          - Lưu lịch sử
          - Trả về hướng (int) hoặc None
        """
        self.chosen_dir = None
        if not self.path:
            return None
        nxt = self._idx + 1
        if nxt >= len(self.path):
            return None

        next_node = self.path[nxt]
        dr = next_node[0] - current_node[0]
        dc = next_node[1] - current_node[1]

        needed = None
        for h, (hdr, hdc) in self.DIR_DELTA.items():
            if hdr == dr and hdc == dc:
                needed = h
                break

        if needed in valid_dirs:
            self.chosen_dir = needed
            self.history.append({
                "node": current_node,
                "valid": list(valid_dirs),
                "chosen": needed,
            })
        return self.chosen_dir

    def confirm_move(self):
        if self._idx + 1 < len(self.path):
            self._idx += 1

    def next_node(self):
        i = self._idx + 1
        return self.path[i] if self.path and i < len(self.path) else None

    def is_done(self):
        return bool(self.path) and self._idx >= len(self.path) - 1

    def has_goal(self):
        return self.goal is not None

    def remaining_steps(self):
        return max(0, len(self.path) - 1 - self._idx) if self.path else 0

    def total_steps(self):
        return max(0, len(self.path) - 1)

    def reset(self):
        self.path           = []
        self.goal           = None
        self._idx           = 0
        self.history        = []
        self.chosen_dir     = None
        self.extra_data     = {}
        self.compute_ms     = 0
        self.exploration_log= []


# ═══════════════════════════════════════════════════
#  1. BFS
# ═══════════════════════════════════════════════════
class BFSPathfinder(BasePathfinder):
    NAME  = "BFS"
    DESC  = "Breadth-First Search  |  Optimal  |  O(V+E)"
    COLOR = (80, 180, 255)

    def _compute(self, map_data, start, goal):
        rows, cols = len(map_data), len(map_data[0])
        visited = {start: None}
        q = deque([start])
        while q:
            r, c = q.popleft()
            self.exploration_log.append((r, c))
            if (r, c) == goal:
                break
            for _, (dr, dc) in self.DIR_DELTA.items():
                nb = (r+dr, c+dc)
                if (0 <= nb[0] < rows and 0 <= nb[1] < cols
                        and map_data[nb[0]][nb[1]] == 0
                        and nb not in visited):
                    visited[nb] = (r, c)
                    q.append(nb)
        if goal not in visited:
            self.path = []; return False
        path, cur = [], goal
        while cur: path.append(cur); cur = visited[cur]
        self.path = path[::-1]; return True


# ═══════════════════════════════════════════════════
#  2. DIJKSTRA
# ═══════════════════════════════════════════════════
class DijkstraPathfinder(BasePathfinder):
    NAME  = "Dijkstra"
    DESC  = "Optimal shortest path  |  O((V+E)logV)"
    COLOR = (255, 200, 50)

    def _compute(self, map_data, start, goal):
        rows, cols = len(map_data), len(map_data[0])
        dist = {start: 0}; prev = {start: None}
        pq = [(0, self._counter, start)]; self._counter += 1
        while pq:
            d, _, node = heapq.heappop(pq)
            if d > dist.get(node, float('inf')): continue
            self.exploration_log.append(node)
            if node == goal: break
            r, c = node
            for _, (dr, dc) in self.DIR_DELTA.items():
                nb = (r+dr, c+dc)
                if (0 <= nb[0] < rows and 0 <= nb[1] < cols
                        and map_data[nb[0]][nb[1]] == 0
                        and d+1 < dist.get(nb, float('inf'))):
                    dist[nb] = d+1; prev[nb] = node
                    heapq.heappush(pq, (d+1, self._counter, nb))
                    self._counter += 1
        if goal not in prev:
            self.path = []; return False
        path, cur = [], goal
        while cur: path.append(cur); cur = prev[cur]
        self.path = path[::-1]; return True


# ═══════════════════════════════════════════════════
#  3. A*
# ═══════════════════════════════════════════════════
class QLearningPathfinder(BasePathfinder):
    """
    Q-Learning — Reinforcement Learning tìm đường
    ───────────────────────────────────────────────
    Nguyên lý:
      Agent học cách di chuyển qua thử-và-sai.
      State   : (row, col) — vị trí hiện tại trên lưới
      Action  : 4 hướng (lên/xuống/trái/phải)
      Reward  : +100 đến đích | -1 mỗi bước | -10 va chướng ngại
      Q-table : Q[r,c,a] = giá trị kỳ vọng khi ở (r,c) chọn action a

    Công thức Bellman:
      Q(s,a) ← Q(s,a) + α[r + γ·max Q(s',a') − Q(s,a)]
      α = learning rate, γ = discount factor

    Training:
      N_EPISODES lần, mỗi lần bắt đầu từ vị trí ngẫu nhiên
      → Q-table học được policy tối ưu cho toàn bản đồ
      Inference: greedy theo Q-table từ start → goal

    Chứng minh hội tụ:
      Q-Learning đảm bảo hội tụ về policy tối ưu nếu
      mỗi (state, action) được thăm đủ nhiều lần (điều kiện Robbins-Monro)
    """
    NAME  = "Q-Learning (RL)"
    DESC  = "Reinforcement Learning  |  Tu hoc qua thu-sai"
    COLOR = (255, 100, 200)

    # Hyperparameters
    ALPHA         = 0.3     # Learning rate
    GAMMA         = 0.9     # Discount factor
    EPS_START     = 1.0     # Epsilon khởi đầu (100% khám phá)
    EPS_END       = 0.05    # Epsilon cuối (5% khám phá)
    N_EPISODES    = 600     # Số episodes train
    MAX_STEPS     = 300     # Số bước tối đa mỗi episode
    REWARD_GOAL   = 100
    REWARD_STEP   = -1
    REWARD_WALL   = -10

    # Actions: right, up, left, down
    _ACTIONS = [(0,1), (-1,0), (0,-1), (1,0)]

    def __init__(self):
        super().__init__()
        self.q_table      = None
        self.train_rewards= []   # Lịch sử reward để visualize
        self.episodes_done= 0
        self._explored_set_rl= set()

    def _compute(self, map_data, start, goal):
        rows, cols = len(map_data), len(map_data[0])
        self._explored_set_rl.clear()

        # ── Khởi tạo Q-table ──
        Q = np.zeros((rows, cols, 4), dtype=np.float32)

        # Danh sách ô trống để random start
        free = [(r,c) for r in range(rows) for c in range(cols)
                if map_data[r][c] == 0]
        if not free: self.path=[]; return False

        # ── Training ──
        eps       = self.EPS_START
        eps_decay = (self.EPS_START - self.EPS_END) / self.N_EPISODES
        rewards   = []

        for ep in range(self.N_EPISODES):
            s = random.choice(free)
            total_r = 0

            for _ in range(self.MAX_STEPS):
                r, c = s

                # ε-greedy policy
                if random.random() < eps:
                    a = random.randint(0, 3)
                else:
                    a = int(np.argmax(Q[r, c]))

                dr, dc = self._ACTIONS[a]
                nr, nc = r+dr, c+dc

                # Reward
                if not (0<=nr<rows and 0<=nc<cols) or map_data[nr][nc]:
                    reward = self.REWARD_WALL
                    ns = s
                elif (nr, nc) == goal:
                    reward = self.REWARD_GOAL
                    ns = (nr, nc)
                else:
                    reward = self.REWARD_STEP
                    ns = (nr, nc)

                # Bellman update
                Q[r,c,a] += self.ALPHA * (
                    reward + self.GAMMA * np.max(Q[ns[0],ns[1]]) - Q[r,c,a]
                )

                # Lưu ngẫu nhiên một số bước học vào log để hiển thị animation
                if random.random() < 0.05 and (r, c) not in self._explored_set_rl:
                    self._explored_set_rl.add((r, c))
                    self.exploration_log.append((r, c))

                total_r += reward
                s = ns
                if s == goal: break

            rewards.append(total_r)
            eps = max(self.EPS_END, eps - eps_decay)

        self.q_table       = Q
        self.train_rewards = rewards
        self.episodes_done = self.N_EPISODES

        # Lưu Q-values để visualize như field overlay
        # Normalize Q-value tốt nhất tại mỗi ô
        q_max = np.max(Q, axis=2)  # rows × cols
        self.extra_data["field"]      = [list(map(float, row)) for row in q_max]
        self.extra_data["field_type"] = "q_value"

        # ── Trích xuất đường đi (greedy policy) ──
        return self._extract_path(Q, map_data, start, goal, rows, cols)

    def _extract_path(self, Q, map_data, start, goal, rows, cols):
        path    = [start]
        cur     = start
        visited = {cur}
        limit   = rows * cols

        while cur != goal and len(path) < limit:
            r, c = cur
            self.exploration_log.append((r, c))
            # Sắp xếp actions theo Q-value, ưu tiên cao nhất
            actions = sorted(range(4), key=lambda a: -Q[r,c,a])
            moved = False
            for a in actions:
                dr, dc = self._ACTIONS[a]
                nb = (r+dr, c+dc)
                if (0<=nb[0]<rows and 0<=nb[1]<cols
                        and map_data[nb[0]][nb[1]]==0
                        and nb not in visited):
                    path.append(nb)
                    visited.add(nb)
                    cur = nb
                    moved = True
                    break
            if not moved:
                # Kẹt → fallback Dijkstra
                return self._dijkstra_fallback(map_data, start, goal)

        if cur != goal:
            return self._dijkstra_fallback(map_data, start, goal)
        self.path = path
        return True

    def _dijkstra_fallback(self, map_data, start, goal):
        rows, cols = len(map_data), len(map_data[0])
        dist={start:0}; prev={start:None}
        pq=[(0,self._counter,start)]; self._counter+=1
        while pq:
            d,_,node=heapq.heappop(pq)
            if d>dist.get(node,float('inf')): continue
            if node==goal: break
            r,c=node
            for _,(dr,dc) in self.DIR_DELTA.items():
                nb=(r+dr,c+dc)
                if(0<=nb[0]<rows and 0<=nb[1]<cols
                   and map_data[nb[0]][nb[1]]==0
                   and d+1<dist.get(nb,float('inf'))):
                    dist[nb]=d+1; prev[nb]=node
                    heapq.heappush(pq,(d+1,self._counter,nb))
                    self._counter+=1
        if goal not in prev: self.path=[]; return False
        path,cur=[],goal
        while cur: path.append(cur); cur=prev[cur]
        self.path=path[::-1]; return True

    def reset(self):
        super().reset()
        self.q_table       = None
        self.train_rewards = []
        self.episodes_done = 0


# ═══════════════════════════════════════════════════
#  4. GREEDY BEST-FIRST
# ═══════════════════════════════════════════════════
class GreedyPathfinder(BasePathfinder):
    NAME  = "Greedy"
    DESC  = "Best-First Greedy  |  Nhanh, khong toi uu"
    COLOR = (255, 140, 50)

    def _h(self, a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def _compute(self, map_data, start, goal):
        rows, cols = len(map_data), len(map_data[0])
        visited = {start: None}
        pq = [(self._h(start, goal), self._counter, start)]
        self._counter += 1
        while pq:
            _, _, node = heapq.heappop(pq)
            self.exploration_log.append(node)
            if node == goal: break
            r, c = node
            for _, (dr, dc) in self.DIR_DELTA.items():
                nb = (r+dr, c+dc)
                if (0 <= nb[0] < rows and 0 <= nb[1] < cols
                        and map_data[nb[0]][nb[1]] == 0
                        and nb not in visited):
                    visited[nb] = node
                    heapq.heappush(pq, (self._h(nb, goal),
                                        self._counter, nb))
                    self._counter += 1
        if goal not in visited:
            self.path = []; return False
        path, cur = [], goal
        while cur: path.append(cur); cur = visited[cur]
        self.path = path[::-1]; return True


# ═══════════════════════════════════════════════════
#  5. GWF — GRADIENT WAVEFRONT FIELD (TỰ THIẾT KẾ)
# ═══════════════════════════════════════════════════
class GWFPathfinder(BasePathfinder):
    """
    Gradient Wavefront Field — Thuật toán tự thiết kế
    ─────────────────────────────────────────────────
    Nguyên lý:
      Pha 1 — BUILD FIELD:
        BFS từ Goal ra ngoài → cost[r][c] = khoảng cách đến Goal
        cost[goal] = 0, lan ra mỗi bước +1

      Pha 2 — REACTIVE CYCLE:
        Sensor → valid_dirs
        Processor: chọn neighbor có cost nhỏ nhất trong valid_dirs
        → di chuyển 1 ô (leo gradient xuống)

    Chứng minh tối ưu:
      Bổ đề: cost[n] = d_BFS(n, goal) — khoảng cách ngắn nhất
        (BFS trên đồ thị không trọng số đảm bảo điều này)
      Định lý: leo gradient cost giảm 1 mỗi bước
        → sau cost[start] bước đến goal = đường ngắn nhất  (QED)

    Ưu điểm so với Dijkstra/A*:
      ✓ Không cần tính lại khi start thay đổi (field cố định theo goal)
      ✓ Replanning chỉ rebuild field — O(V), không cần queue mới
      ✓ Có thể thêm λ·penalty(n) cho vùng nguy hiểm mà vẫn tối ưu
    """
    NAME  = "GWF (Tu thiet ke)"
    DESC  = "Gradient Wavefront  |  Goal->All BFS  |  Toi uu"
    COLOR = (200, 80, 255)

    def __init__(self):
        super().__init__()
        self.cost_field = None
        self._rows = self._cols = 0

    def set_goal(self, map_data, start, goal):
        self.goal = goal; self._idx = 0; self.history = []
        t0 = time.perf_counter()
        self._build_field(map_data, goal)
        ok = self._trace_gradient(map_data, start, goal)
        self.compute_ms = round((time.perf_counter()-t0)*1000, 2)
        return ok

    def replan(self, map_data, current_pos):
        if not self.goal: return False
        self._idx = 0
        t0 = time.perf_counter()
        self._build_field(map_data, self.goal)
        ok = self._trace_gradient(map_data, current_pos, self.goal)
        self.compute_ms = round((time.perf_counter()-t0)*1000, 2)
        return ok

    def _build_field(self, map_data, goal):
        """BFS từ goal → tạo trường chi phí O(V)."""
        rows, cols = len(map_data), len(map_data[0])
        self._rows, self._cols = rows, cols
        INF = float('inf')
        cost = [[INF]*cols for _ in range(rows)]
        cost[goal[0]][goal[1]] = 0
        q = deque([goal])
        while q:
            r, c = q.popleft()
            self.exploration_log.append((r, c))
            for _, (dr, dc) in self.DIR_DELTA.items():
                nr, nc = r+dr, c+dc
                if (0 <= nr < rows and 0 <= nc < cols
                        and map_data[nr][nc] == 0
                        and cost[nr][nc] == INF):
                    cost[nr][nc] = cost[r][c] + 1
                    q.append((nr, nc))
        self.cost_field = cost
        self.extra_data["field"] = cost
        self.extra_data["field_type"] = "cost"

    def _trace_gradient(self, map_data, start, goal):
        """Leo gradient cost từ start → goal."""
        if (self.cost_field is None
                or self.cost_field[start[0]][start[1]] == float('inf')):
            self.path = []; return False
        path, cur = [start], start
        limit = self._rows * self._cols
        while cur != goal and len(path) < limit:
            r, c = cur
            best, best_c = None, self.cost_field[r][c]
            for _, (dr, dc) in self.DIR_DELTA.items():
                nr, nc = r+dr, c+dc
                if (0 <= nr < self._rows and 0 <= nc < self._cols
                        and self.cost_field[nr][nc] < best_c):
                    best_c = self.cost_field[nr][nc]; best = (nr, nc)
            if best is None: self.path = []; return False
            path.append(best); cur = best
        if cur != goal: self.path = []; return False
        self.path = path; return True

    def reset(self):
        super().reset()
        self.cost_field = None


# ═══════════════════════════════════════════════════
#  6. ACO — ANT COLONY OPTIMIZATION (AI BẦY ĐÀN)
# ═══════════════════════════════════════════════════
class ACOPathfinder(BasePathfinder):
    """
    Ant Colony Optimization — Tối ưu hóa đàn kiến
    ───────────────────────────────────────────────
    Nguyên lý sinh học:
      Kiến thật tìm đường ngắn nhất bằng pheromone:
        1. Kiến đi ngẫu nhiên, để lại pheromone
        2. Đường ngắn → nhiều kiến đi → nhiều pheromone
        3. Kiến sau ưu tiên đường nhiều pheromone hơn
        4. Pheromone bay hơi theo thời gian (tránh kẹt cục bộ)

    Công thức xác suất chọn ô tiếp theo:
      p(i→j) = [τ(j)^α × η(j)^β] / Σ[τ(k)^α × η(k)^β]
      τ(j) = pheromone tại ô j
      η(j) = 1 / d(j, goal) — heuristic khoảng cách

    Cập nhật pheromone:
      τ ← τ × (1-ρ)          (bay hơi)
      τ(path) += Q / L        (gia cường đường tốt)
      Q = hằng số, L = độ dài đường

    Visualization: heatmap pheromone → thấy đường kiến hình thành
    Chứng minh: ACO hội tụ về global optimum khi N_ANTS→∞, ρ→0
    """
    NAME  = "ACO (Ant Colony)"
    DESC  = "Ant Colony Optimization  |  AI bay dan"
    COLOR = (255, 180, 30)

    # Hyperparameters
    N_ANTS    = 25      # Số kiến mỗi iteration
    N_ITER    = 60      # Số vòng lặp
    ALPHA     = 1.2     # Trọng số pheromone τ
    BETA      = 2.5     # Trọng số heuristic η
    RHO       = 0.25    # Tốc độ bay hơi (0=không bay, 1=bay hết)
    Q         = 100.0   # Lượng pheromone deposit
    TAU_INIT  = 0.1     # Pheromone khởi tạo
    TAU_MIN   = 0.01    # Pheromone tối thiểu (tránh về 0)

    def __init__(self):
        super().__init__()
        self.pheromone        = None
        self.best_length      = float('inf')
        self._explored_set_aco= set()

    def _compute(self, map_data, start, goal):
        rows, cols = len(map_data), len(map_data[0])

        # ── Khởi tạo pheromone uniform ──
        tau = np.full((rows, cols), self.TAU_INIT, dtype=np.float64)
        # Obstacle = 0 pheromone
        for r in range(rows):
            for c in range(cols):
                if map_data[r][c]: tau[r,c] = 0.0

        # ── Heuristic: 1 / (manhattan + 1) ──
        eta = np.zeros((rows, cols), dtype=np.float64)
        for r in range(rows):
            for c in range(cols):
                if not map_data[r][c]:
                    d = abs(r-goal[0]) + abs(c-goal[1])
                    eta[r,c] = 1.0 / (d + 1)

        DIRS = list(self.DIR_DELTA.values())
        best_path   = None
        best_len    = float('inf')

        self._explored_set_aco = set()
        for iteration in range(self.N_ITER):
            all_paths = []

            for _ in range(self.N_ANTS):
                path = self._ant_walk(map_data, start, goal,
                                      tau, eta, rows, cols, DIRS)
                if path is not None:
                    all_paths.append(path)
                    if len(path) < best_len:
                        best_len  = len(path)
                        best_path = path[:]
                    # Log cells từ mỗi ant (deduplicated)
                    for cell in path:
                        if cell not in self._explored_set_aco:
                            self._explored_set_aco.add(cell)
                            self.exploration_log.append(cell)

            # ── Bay hơi pheromone ──
            tau *= (1.0 - self.RHO)
            tau  = np.maximum(tau, self.TAU_MIN)

            # ── Deposit pheromone cho các đường thành công ──
            for path in all_paths:
                deposit = self.Q / len(path)
                for node in path:
                    tau[node[0], node[1]] += deposit

            # Bonus: đường tốt nhất deposit thêm
            if best_path:
                bonus = self.Q / best_len
                for node in best_path:
                    tau[node[0], node[1]] += bonus * 0.5

        # Lưu pheromone để visualize
        self.pheromone = tau
        self.extra_data["field"]      = [list(map(float, row)) for row in tau]
        self.extra_data["field_type"] = "pheromone"
        self.best_length = best_len

        if best_path is None:
            return self._dijkstra_fallback(map_data, start, goal)

        self.path = best_path
        return True

    def _ant_walk(self, map_data, start, goal,
                  tau, eta, rows, cols, DIRS):
        """1 con kiến đi từ start → goal theo xác suất τ^α × η^β."""
        path    = [start]
        visited = {start}
        cur     = start
        limit   = rows * cols

        while cur != goal and len(path) < limit:
            r, c = cur

            # Tìm các ô hàng xóm hợp lệ
            candidates = []
            for dr, dc in DIRS:
                nr, nc = r+dr, c+dc
                nb = (nr, nc)
                if (0<=nr<rows and 0<=nc<cols
                        and map_data[nr][nc]==0
                        and nb not in visited):
                    candidates.append(nb)

            if not candidates:
                return None  # Kiến bị kẹt

            # Tính xác suất chọn theo τ^α × η^β
            scores = np.array([
                (tau[n[0],n[1]] ** self.ALPHA) *
                (eta[n[0],n[1]] ** self.BETA)
                for n in candidates
            ])
            total = scores.sum()
            if total == 0:
                # Fallback: chọn ngẫu nhiên
                nxt = random.choice(candidates)
            else:
                probs = scores / total
                idx   = np.random.choice(len(candidates), p=probs)
                nxt   = candidates[idx]

            path.append(nxt)
            visited.add(nxt)
            cur = nxt

        return path if cur == goal else None

    def _dijkstra_fallback(self, map_data, start, goal):
        rows,cols=len(map_data),len(map_data[0])
        dist={start:0}; prev={start:None}
        pq=[(0,self._counter,start)]; self._counter+=1
        while pq:
            d,_,node=heapq.heappop(pq)
            if d>dist.get(node,float('inf')): continue
            if node==goal: break
            r,c=node
            for _,(dr,dc) in self.DIR_DELTA.items():
                nb=(r+dr,c+dc)
                if(0<=nb[0]<rows and 0<=nb[1]<cols
                   and map_data[nb[0]][nb[1]]==0
                   and d+1<dist.get(nb,float('inf'))):
                    dist[nb]=d+1; prev[nb]=node
                    heapq.heappush(pq,(d+1,self._counter,nb))
                    self._counter+=1
        if goal not in prev: self.path=[]; return False
        path,cur=[],goal
        while cur: path.append(cur); cur=prev[cur]
        self.path=path[::-1]; return True

    def reset(self):
        super().reset()
        self.pheromone        = None
        self.best_length      = float('inf')
        self._explored_set_aco= set()
# ═══════════════════════════════════════════════════
#  MANAGER — Processors (API không đổi với application.py)
# ═══════════════════════════════════════════════════
class Processors:

    ALGO_CLASSES = [
        BFSPathfinder,
        DijkstraPathfinder,
        QLearningPathfinder,
        GreedyPathfinder,
        GWFPathfinder,
        ACOPathfinder,
    ]

    def __init__(self):
        self._idx      = 0
        self._algos    = [cls() for cls in self.ALGO_CLASSES]
        self._cur      = self._algos[0]

    # ── Thông tin thuật toán ───────────────────────
    @property
    def algo_count(self):
        return len(self.ALGO_CLASSES)

    @property
    def algo_names(self):
        return [cls.NAME for cls in self.ALGO_CLASSES]

    @property
    def current_index(self):
        return self._idx

    @property
    def current_name(self):
        return self._cur.NAME

    @property
    def current_desc(self):
        return self._cur.DESC

    @property
    def current_color(self):
        return self._cur.COLOR

    @property
    def compute_ms(self):
        return self._cur.compute_ms

    def switch(self, index):
        """Chuyển thuật toán, giữ lại goal nếu có."""
        if not (0 <= index < len(self._algos)):
            return
        old_goal = self._cur.goal
        self._idx = index
        self._cur = self._algos[index]
        self._cur.reset()
        self._cur.goal = old_goal

    # ── Forward API (giữ nguyên interface) ────────
    def set_goal(self, map_data, start, goal):
        return self._cur.set_goal(map_data, start, goal)

    def replan(self, map_data, current_pos):
        return self._cur.replan(map_data, current_pos)

    def cycle(self, current_node, valid_dirs):
        return self._cur.cycle(current_node, valid_dirs)

    def confirm_move(self):
        self._cur.confirm_move()

    def next_node(self):
        return self._cur.next_node()

    def is_done(self):
        return self._cur.is_done()

    def has_goal(self):
        return self._cur.has_goal()

    def remaining_steps(self):
        return self._cur.remaining_steps()

    def total_steps(self):
        return self._cur.total_steps()

    @property
    def full_path(self):
        return self._cur.path

    @full_path.setter
    def full_path(self, v):
        self._cur.path = v

    @property
    def history(self):
        return self._cur.history

    @history.setter
    def history(self, v):
        self._cur.history = v

    @property
    def chosen_dir(self):
        return self._cur.chosen_dir

    @property
    def extra_data(self):
        return self._cur.extra_data

    def reset_current(self):
        old_goal = self._cur.goal
        self._cur.reset()
        self._cur.goal = old_goal
