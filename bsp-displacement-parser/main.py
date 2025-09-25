import numpy as np
import random
from string import ascii_lowercase, digits
from valvebsp import Bsp
from valvebsp.lumps import *

from displacement import Displacement, DispOrientation
from md_report import MarkdownReport, SpotTextWriter, AllDispTextWriter  # added AllDispTextWriter
from utils import angle_bc


# untested
TF_PLAYER = 83
TF_PLAYER_DUCKING = 63
TF_SENTRY_LVL3_HEIGHT = 87
TF_DISPENSER_HEIGHT = 83
TF_TELEPORT_HEIGHT = 12


class Criteria:
    min_height = TF_PLAYER_DUCKING
    min_plane_dist_diff = 8
    min_angle = 150
    max_angle = 170
    power_diff_tolerance = 45


class BspData:
    def __init__(self, bsp):
        self.m_displacements = bsp[LUMP_DISPINFO]
        self.m_displacement_verts = bsp[LUMP_DISP_VERTS]
        self.m_planes = bsp[LUMP_PLANES]
        self.m_faces = bsp[LUMP_FACES]
        self.m_surf_edges = bsp[LUMP_SURFEDGES]
        self.m_edges = bsp[LUMP_EDGES]
        self.m_verts = bsp[LUMP_VERTEXES]


def edge_vector(edge):
    return edge.end - edge.start


def tris_ang(tris):
    tr_1 = tris[0].np_verts
    tr_2 = tris[1].np_verts

    ang = angle_bc(tr_1, tr_2)

    if ang < 90:
        ang = 180 - ang

    return ang


def closest_power_of_two(num):
    num = abs(int(num))

    n = num
    n -= 1
    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    n += 1
    p = n >> 1

    if (n - num) > (num - p):
        return p, num - p
    else:
        return n, n - num


def has_negative_power_of_two_coord(vert, tolerance, f = False):
    min_diff = 2 ** 32
    mp = 0
    for i in range(2):  # don't test z?
        if vert.coord[i] >= 0:
            if vert.coord[i] < tolerance:
                power, diff = 0, vert.coord[i] + 2
            else:
                continue
        else:
            power, diff = closest_power_of_two(vert.coord[i])
        if diff < min_diff:
            min_diff = diff
            mp = power

    if f:
        return mp, min_diff
    else:
        return min_diff <= tolerance


def rand_img_name():
    return ''.join(random.choices(ascii_lowercase + digits, k=10)) + '.jpg'


def main(map_name):
    bsp = Bsp(f'maps/{map_name}.bsp', 'TF2')
    bsp_data = BspData(bsp)

    md = MarkdownReport(map_name, len(bsp_data.m_displacements), len(bsp_data.m_displacement_verts))

    # ---- writers: SPOTs (existing) + ALL GRID VERTS (new) -------------------
    spot_txt = SpotTextWriter(map_name)
    grid_txt = AllDispTextWriter(map_name)   # writes DISPGRID/POWER/POST + DVERT + ENDDISP

    spot_index = 0  # global running id across the whole map

    for i in range(0, len(bsp_data.m_displacements)):
        try:
            disp = Displacement(i, bsp_data)

            # --- NEW: write per-displacement grid once, in the Lua-friendly format
            grid_txt.begin_displacement(disp_idx=disp.idx, power=disp.power, post_spacing=disp.post_spacing)
            for sv in disp.surface:           # row-major, size = post_spacing*post_spacing
                grid_txt.write_vert(sv.coord)
            grid_txt.end_displacement()

        except AssertionError:
            print(f'[Parse Error] {i} Bad disp, unpack first?, power = {bsp_data.m_displacements[i].power}')
            continue

        # Skip horizontal/down-facing as before
        if disp.orientation in [DispOrientation.HORIZONTAL, DispOrientation.HORIZONTAL_DOWN]:
            continue

        print(f'[IDX] {i}')
        heading_added = False

        surface = disp.surface
        for edge in disp.surface_edges:
            if edge.is_tr_edge or len(edge.triangles) != 2:
                continue

            is_ceiling, high, low = edge.is_ceiling(disp.orientation)
            diff = abs(high - low)
            if not is_ceiling:
                continue

            colormap = ['r' if e.idx in [edge.start.idx, edge.end.idx] else 'y' for e in surface]
            edge_vec = edge_vector(edge)
            tris = list(edge.triangles)
            try:
                ang = tris_ang(tris)
            except:
                ang = -1

            if diff < Criteria.min_plane_dist_diff or not (Criteria.min_angle < ang < Criteria.max_angle) or abs(edge_vec[2]) < Criteria.min_height:
                continue

            if not has_negative_power_of_two_coord(edge.start, Criteria.power_diff_tolerance) and not has_negative_power_of_two_coord(edge.end, Criteria.power_diff_tolerance):
                continue

            other_verts = (set(tris[0].verts) | set(tris[1].verts)) - {edge.start, edge.end}

            for b in tris:
                b.color = 'r'

            img_name = f'reports/images/{map_name}/{rand_img_name()}'
            disp.draw_triangulated(colormap=colormap, save_to=img_name)

            if not heading_added:
                md.next_displacement(i, disp.get_facing_setpos())
                heading_added = True

            # Start/End power-of-two info
            start_pow_info = has_negative_power_of_two_coord(edge.start, Criteria.power_diff_tolerance, True)
            end_pow_info   = has_negative_power_of_two_coord(edge.end,   Criteria.power_diff_tolerance, True)
            start_pow = start_pow_info[0]
            end_pow   = end_pow_info[0]

            md.add_spot(
                img_name, ang, diff, abs(edge_vec[2]),
                edge.start.coord, edge.end.coord,
                start_pow_info, end_pow_info
            )

            # export SPOT verts (existing flow)
            unique = {}
            for t in tris:
                for v in t.verts:
                    c = v.coord
                    key = (float(c[0]), float(c[1]), float(c[2]))
                    unique[key] = key

            spot_index += 1
            spot_txt.write_spot(
                spot_id=spot_index,
                disp_idx=disp.idx,
                angle_deg=ang,
                plane_diff=diff,
                height=abs(edge_vec[2]),
                start_power=start_pow,
                end_power=end_pow,
                start_coord=edge.start.coord,
                end_coord=edge.end.coord,
                verts=list(unique.values())
            )

            for b in tris:
                b.reset_color()

    md.save()



def main_interactive(map_name, index):
    bsp = Bsp(f'maps/{map_name}.bsp', 'TF2')
    bsp_data = BspData(bsp)

    disp = Displacement(index, bsp_data)
    print(disp.orientation)
    print('[SETPOS] ', disp.get_facing_setpos())
    disp.draw_triangulated(close=False)


if __name__ == '__main__':
    main('cp_coldfront')
