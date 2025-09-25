import os


def create_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)


class MarkdownReport:
    def __init__(self, map_name, disp_count, vert_count):
        self.map_name = map_name
        self.content = '<style>img{width:55%;height:auto}</style>\n\n'

        create_dir('reports')
        create_dir('reports/images')
        create_dir(f'reports/images/{map_name}')

        self.write(f'# {map_name}\n')
        self.write(f'Total displacement count: {disp_count} \\')
        self.write(f'Total vertices count: {vert_count}')

    def next_displacement(self, idx, setpos):
        self.write(f'### Displacement {idx}')
        self.write('```')
        self.write(setpos)
        self.write('```')
        self.write('|Image|Angle|Plane dist diff|Height|Start|End|')
        self.write('|---|---|---|---|---|---|')

    def add_spot(self, img, angle, plane_dist_diff, height, start_coord, end_coord, start_power, end_power):
        img = img.split('reports/')[1]
        self.write(f'|![]({img})|{int(angle)}|{plane_dist_diff:.2f}|{height:.2f}|{start_coord}  [{start_power}]|{end_coord}  [{end_power}]|')

    def write(self, text):
        self.content += f'{text}\n'

    def save(self):
        with open(f'reports/{self.map_name}.md', 'w') as f:
            f.write(self.content)


# --- BEGIN: Vertex + Grid text writer (replaces SpotTextWriter) ------------
def _round3(x):
    try:    return round(float(x), 3)
    except: return x

class SpotTextWriter:
    """
    Writes both:
      • SPOT blocks (existing)
      • DISPGRID blocks with DVERTs for every displacement

    File: reports/<map>_verts.txt
    """
    def __init__(self, map_name: str):
        create_dir('reports')
        self.map_name = map_name
        self.path = f'reports/{map_name}_verts.txt'
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f'# Exploita Spots + Full Displacement Grid for {map_name}\n')

    # ---------- DISPGRID ----------
    def begin_grid(self, disp_idx: int):
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(f'DISPGRID,{int(disp_idx)}\n')

    def write_dvert(self, p):
        x, y, z = _round3(p[0]), _round3(p[1]), _round3(p[2])
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(f'DVERT,{x},{y},{z}\n')

    def end_grid(self):
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write('ENDGRID\n')

    # ---------- SPOT (unchanged interface) ----------
    def write_spot(self, spot_id, disp_idx, angle_deg, plane_diff, height,
                   start_power, end_power, start_coord, end_coord, verts):
        def _xyz(p): return (_round3(p[0]), _round3(p[1]), _round3(p[2]))
        sx, sy, sz = _xyz(start_coord); ex, ey, ez = _xyz(end_coord)
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(f'SPOT,{int(spot_id)},DISP,{int(disp_idx)},ANGLE,{_round3(angle_deg)},'
                    f'PLANE_DIFF,{_round3(plane_diff)},HEIGHT,{_round3(height)},'
                    f'START_POW2,{int(start_power)},END_POW2,{int(end_power)}\n')
            f.write(f'START,{sx},{sy},{sz}\n')
            f.write(f'END,{ex},{ey},{ez}\n')
            for v in verts:
                vx,vy,vz = _xyz(v)
                f.write(f'VERT,{vx},{vy},{vz}\n')
            f.write('ENDSPOT\n')
# --- END: Vertex + Grid text writer ----------------------------------------



# --- NEW: All-displacement grid writer (appends to the same file) -----------

class AllDispTextWriter:
    """
    Appends per-displacement grid data to the same Lua-friendly file:
      DISPGRID,<disp_idx>,POWER,<p>,POST,<post_spacing>
      DVERT,<x>,<y>,<z>   (post*post items, row-major)
      ...
      ENDDISP
    """
    def __init__(self, map_name: str, path: str = None):
        self.map_name = map_name
        self.path = path or f'reports/{map_name}_verts.txt'
        # header marker for clarity (kept as a comment, safe to ignore)
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(f'# All Displacement Grids for {map_name}\n')

    def _w(self, line: str):
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    def begin_displacement(self, disp_idx: int, power: int, post_spacing: int):
        self._w(f'DISPGRID,{int(disp_idx)},POWER,{int(power)},POST,{int(post_spacing)}')

    def write_vert(self, xyz):
        x, y, z = _round3(xyz[0]), _round3(xyz[1]), _round3(xyz[2])
        self._w(f'DVERT,{x},{y},{z}')

    def end_displacement(self):
        self._w('ENDDISP')
# --- END: All-displacement grid writer --------------------------------------
