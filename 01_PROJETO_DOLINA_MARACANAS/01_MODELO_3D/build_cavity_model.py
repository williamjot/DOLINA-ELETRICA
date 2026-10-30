"""Build a georeferenced parametric model of Dolina dos Maracanas.

The model is constrained by the supplied L1/L2 survey lines and their
topographic profiles. It is an interpretive geometry, not a cave survey.
"""

from __future__ import annotations

import csv
import json
import math
import struct
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer
from scipy.io import savemat
from scipy.interpolate import PchipInterpolator


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input_reference"


def read_parameters() -> dict:
    return json.loads((ROOT / "parameters.json").read_text(encoding="utf-8"))


def read_kmz_longest_line(path: Path) -> np.ndarray:
    with zipfile.ZipFile(path) as archive:
        kml_name = next(name for name in archive.namelist() if name.lower().endswith(".kml"))
        root = ET.fromstring(archive.read(kml_name))
    blocks = []
    for node in root.findall(".//{*}LineString/{*}coordinates"):
        rows = []
        for token in (node.text or "").split():
            values = token.split(",")
            if len(values) >= 2:
                rows.append((float(values[0]), float(values[1])))
        if len(rows) >= 2:
            blocks.append(np.asarray(rows, dtype=float))
    if not blocks:
        raise ValueError(f"No LineString found in {path}")
    return max(blocks, key=len)


def read_topography_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    stations, elevation = [], []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = csv.reader(stream)
        next(rows, None)
        for row in rows:
            if not row:
                continue
            stations.append(float(row[1]))
            elevation.append(float(row[3]))
    return np.asarray(stations), np.asarray(elevation)


def cumulative_distance(xy: np.ndarray) -> np.ndarray:
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]


def sample_polyline(xy: np.ndarray, n: int) -> np.ndarray:
    distance = cumulative_distance(xy)
    target = np.linspace(0.0, distance[-1], n)
    return np.column_stack(
        [np.interp(target, distance, xy[:, 0]), np.interp(target, distance, xy[:, 1])]
    )


def point_at_half_length(xy: np.ndarray) -> np.ndarray:
    distance = cumulative_distance(xy)
    half = distance[-1] / 2.0
    return np.array(
        [np.interp(half, distance, xy[:, 0]), np.interp(half, distance, xy[:, 1])]
    )


def line_azimuth_from_north(xy: np.ndarray) -> float:
    vector = xy[-1] - xy[0]
    return float((math.degrees(math.atan2(vector[0], vector[1])) + 360.0) % 360.0)


def circular_mean_degrees(values: list[float]) -> float:
    radians = np.radians(values)
    return float((math.degrees(math.atan2(np.mean(np.sin(radians)), np.mean(np.cos(radians)))) + 360.0) % 360.0)


def fit_topography_plane(xyz: np.ndarray, center_xy: np.ndarray) -> np.ndarray:
    dxdy = xyz[:, :2] - center_xy
    design = np.column_stack([np.ones(len(xyz)), dxdy])
    coefficient, *_ = np.linalg.lstsq(design, xyz[:, 2], rcond=None)
    return coefficient


def plane_z(coefficient: np.ndarray, xy: np.ndarray, center_xy: np.ndarray) -> np.ndarray:
    delta = xy - center_xy
    return coefficient[0] + coefficient[1] * delta[..., 0] + coefficient[2] * delta[..., 1]


def make_mesh(params: dict, center_xy: np.ndarray, azimuth: float, topo_plane: np.ndarray):
    n_theta = int(params["n_azimuth"])
    n_depth = int(params["n_depth"])
    a = float(params["major_diameter_m"]) / 2.0
    b = float(params["minor_diameter_m"]) / 2.0
    depth = float(params["depth_m"])
    roughness = float(params["angular_roughness_fraction"])

    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    t = np.linspace(0.0, 1.0, n_depth)
    shape = PchipInterpolator(
        np.asarray(params["wall_depth_fraction"], dtype=float),
        np.asarray(params["wall_radius_factor"], dtype=float),
    )(t)

    # Azimuth is clockwise from north; alpha is counter-clockwise from easting.
    alpha = math.radians(90.0 - azimuth)
    ca, sa = math.cos(alpha), math.sin(alpha)
    angular = 1.0 + roughness * np.sin(3.0 * theta + 0.35) + 0.6 * roughness * np.sin(7.0 * theta - 1.10)

    vertices = []
    for depth_index, fraction in enumerate(t):
        radius = shape[depth_index] * angular
        u = a * radius * np.cos(theta)
        v = b * radius * np.sin(theta)
        dx = u * ca - v * sa
        dy = u * sa + v * ca
        xy = np.column_stack([center_xy[0] + dx, center_xy[1] + dy])
        z = plane_z(topo_plane, xy, center_xy) - fraction * depth
        vertices.append(np.column_stack([xy, z]))
    wall_vertices = np.vstack(vertices)

    faces = []
    for i in range(n_depth - 1):
        for j in range(n_theta):
            jn = (j + 1) % n_theta
            p00 = i * n_theta + j
            p01 = i * n_theta + jn
            p10 = (i + 1) * n_theta + j
            p11 = (i + 1) * n_theta + jn
            faces.append((p00, p10, p11))
            faces.append((p00, p11, p01))

    bottom_center = np.array([[center_xy[0], center_xy[1], topo_plane[0] - depth]])
    open_vertices = np.vstack([wall_vertices, bottom_center])
    bottom_index = len(open_vertices) - 1
    bottom_ring = (n_depth - 1) * n_theta
    for j in range(n_theta):
        jn = (j + 1) % n_theta
        faces.append((bottom_ring + j, bottom_index, bottom_ring + jn))
    open_faces = np.asarray(faces, dtype=np.int32)

    top_center = np.array([[center_xy[0], center_xy[1], topo_plane[0]]])
    closed_vertices = np.vstack([open_vertices, top_center])
    closed_faces = open_faces.tolist()
    top_index = len(closed_vertices) - 1
    for j in range(n_theta):
        jn = (j + 1) % n_theta
        closed_faces.append((j, jn, top_index))
    closed_faces = np.asarray(closed_faces, dtype=np.int32)
    return open_vertices, open_faces, closed_vertices, closed_faces


def localize(vertices: np.ndarray, center_xy: np.ndarray, center_z: float) -> np.ndarray:
    result = vertices.copy()
    result[:, 0] -= center_xy[0]
    result[:, 1] -= center_xy[1]
    result[:, 2] -= center_z
    return result


def write_binary_stl(path: Path, vertices: np.ndarray, faces: np.ndarray):
    with path.open("wb") as stream:
        stream.write(b"Dolina dos Maracanas parametric mesh".ljust(80, b" "))
        stream.write(struct.pack("<I", len(faces)))
        for face in faces:
            tri = vertices[face].astype(np.float32)
            normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            length = float(np.linalg.norm(normal))
            if length:
                normal /= length
            stream.write(struct.pack("<12fH", *normal, *tri[0], *tri[1], *tri[2], 0))


def write_obj(path: Path, vertices: np.ndarray, faces: np.ndarray):
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("# Dolina dos Maracanas parametric surface\n")
        for x, y, z in vertices:
            stream.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for a, b, c in faces + 1:
            stream.write(f"f {a} {b} {c}\n")


def write_vertex_face_csv(prefix: str, vertices: np.ndarray, faces: np.ndarray):
    np.savetxt(
        ROOT / f"{prefix}_vertices.csv",
        vertices,
        delimiter=",",
        header="x_m,y_m,z_m",
        comments="",
        fmt="%.6f",
    )
    np.savetxt(
        ROOT / f"{prefix}_faces_0based.csv",
        faces,
        delimiter=",",
        header="v0,v1,v2",
        comments="",
        fmt="%d",
    )


def write_electrodes(path: Path, station: np.ndarray, lonlat: np.ndarray, xyz: np.ndarray):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["electrode", "station_m", "longitude", "latitude", "easting_m", "northing_m", "elevation_m"])
        for i, (s, ll, point) in enumerate(zip(station, lonlat, xyz), start=1):
            writer.writerow([i, f"{s:.3f}", f"{ll[0]:.10f}", f"{ll[1]:.10f}", f"{point[0]:.3f}", f"{point[1]:.3f}", f"{point[2]:.3f}"])


def build():
    params = read_parameters()
    to_utm = Transformer.from_crs(4326, params["crs_epsg"], always_xy=True)
    to_lonlat = Transformer.from_crs(params["crs_epsg"], 4326, always_xy=True)

    l1_lonlat = read_kmz_longest_line(INPUT / "L1_linha.kmz")
    l2_lonlat_raw = read_kmz_longest_line(INPUT / "L2.kmz")
    l1_station, l1_z = read_topography_csv(INPUT / "Linha01_Dolina_10m.csv")
    l2_station, l2_z = read_topography_csv(INPUT / "Linha02_Dolina_10m.csv")

    l1_xy = np.column_stack(to_utm.transform(l1_lonlat[:, 0], l1_lonlat[:, 1]))
    l2_xy_raw = np.column_stack(to_utm.transform(l2_lonlat_raw[:, 0], l2_lonlat_raw[:, 1]))
    l1_xy = sample_polyline(l1_xy, len(l1_station))
    l2_xy = sample_polyline(l2_xy_raw, len(l2_station))
    l1_lonlat = np.column_stack(to_lonlat.transform(l1_xy[:, 0], l1_xy[:, 1]))
    l2_lonlat = np.column_stack(to_lonlat.transform(l2_xy[:, 0], l2_xy[:, 1]))
    l1_xyz = np.column_stack([l1_xy, l1_z])
    l2_xyz = np.column_stack([l2_xy, l2_z])

    midpoint_l1 = point_at_half_length(l1_xy)
    midpoint_l2 = point_at_half_length(l2_xy)
    center_xy = (midpoint_l1 + midpoint_l2) / 2.0
    separation = float(np.linalg.norm(midpoint_l2 - midpoint_l1))
    azimuth = circular_mean_degrees([line_azimuth_from_north(l1_xy), line_azimuth_from_north(l2_xy)])
    topo_plane = fit_topography_plane(np.vstack([l1_xyz, l2_xyz]), center_xy)
    center_z = float(topo_plane[0])

    open_utm, faces_open, closed_utm, faces_closed = make_mesh(params, center_xy, azimuth, topo_plane)
    open_local = localize(open_utm, center_xy, center_z)
    closed_local = localize(closed_utm, center_xy, center_z)
    l1_local = localize(l1_xyz, center_xy, center_z)
    l2_local = localize(l2_xyz, center_xy, center_z)

    depth_levels = np.linspace(0.0, float(params["section_depth_m"]), int(params["section_depth_samples"]))
    l1_section = np.stack([np.tile(l1_local[:, 0], (len(depth_levels), 1)), np.tile(l1_local[:, 1], (len(depth_levels), 1)), l1_local[:, 2][None, :] - depth_levels[:, None]], axis=2)
    l2_section = np.stack([np.tile(l2_local[:, 0], (len(depth_levels), 1)), np.tile(l2_local[:, 1], (len(depth_levels), 1)), l2_local[:, 2][None, :] - depth_levels[:, None]], axis=2)

    metadata = {
        **params,
        "coordinate_system": "SIRGAS 2000 / UTM zone 23S",
        "center_easting_m": float(center_xy[0]),
        "center_northing_m": float(center_xy[1]),
        "center_reference_elevation_m": center_z,
        "major_axis_azimuth_deg_from_north": azimuth,
        "survey_line_midpoint_separation_m": separation,
        "L1_geodesic_projected_length_m": float(cumulative_distance(l1_xy)[-1]),
        "L2_geodesic_projected_length_m": float(cumulative_distance(l2_xy)[-1]),
        "topography_plane": {"z0_m": float(topo_plane[0]), "dz_dx": float(topo_plane[1]), "dz_dy": float(topo_plane[2])},
        "interpretation": "Synthetic collapse-doline wall and floor constrained by two survey lines; not a surveyed cave geometry.",
    }

    np.savez_compressed(
        ROOT / "dolina_model.npz",
        vertices_open_local=open_local,
        vertices_open_utm=open_utm,
        faces_open_0based=faces_open,
        vertices_closed_local=closed_local,
        vertices_closed_utm=closed_utm,
        faces_closed_0based=faces_closed,
        L1_xyz_local=l1_local,
        L1_xyz_utm=l1_xyz,
        L1_station_m=l1_station,
        L2_xyz_local=l2_local,
        L2_xyz_utm=l2_xyz,
        L2_station_m=l2_station,
        L1_section_plane_local=l1_section,
        L2_section_plane_local=l2_section,
        depth_levels_m=depth_levels,
        center_utm=np.array([center_xy[0], center_xy[1], center_z]),
        metadata_json=np.array(json.dumps(metadata, ensure_ascii=False)),
    )

    savemat(
        ROOT / "dolina_model.mat",
        {
            "vertices_open_local": open_local,
            "vertices_open_utm": open_utm,
            "faces_open": faces_open + 1,
            "vertices_closed_local": closed_local,
            "vertices_closed_utm": closed_utm,
            "faces_closed": faces_closed + 1,
            "L1_xyz_local": l1_local,
            "L1_xyz_utm": l1_xyz,
            "L1_station_m": l1_station,
            "L2_xyz_local": l2_local,
            "L2_xyz_utm": l2_xyz,
            "L2_station_m": l2_station,
            "L1_section_plane_local": l1_section,
            "L2_section_plane_local": l2_section,
            "depth_levels_m": depth_levels,
            "center_utm": np.array([center_xy[0], center_xy[1], center_z]),
            "major_diameter_m": float(params["major_diameter_m"]),
            "minor_diameter_m": float(params["minor_diameter_m"]),
            "depth_m": float(params["depth_m"]),
            "major_axis_azimuth_deg": azimuth,
            "survey_line_separation_m": separation,
        },
        do_compression=True,
    )

    write_binary_stl(ROOT / "dolina_surface_open_local.stl", open_local, faces_open)
    write_binary_stl(ROOT / "dolina_volume_closed_local.stl", closed_local, faces_closed)
    write_obj(ROOT / "dolina_surface_open_local.obj", open_local, faces_open)
    write_obj(ROOT / "dolina_volume_closed_local.obj", closed_local, faces_closed)
    write_vertex_face_csv("dolina_surface_open_local", open_local, faces_open)
    write_electrodes(ROOT / "L1_electrodes_utm.csv", l1_station, l1_lonlat, l1_xyz)
    write_electrodes(ROOT / "L2_electrodes_utm.csv", l2_station, l2_lonlat, l2_xyz)
    (ROOT / "model_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    top_ring = open_utm[: int(params["n_azimuth"])]
    np.savetxt(
        ROOT / "rim_outline_utm.csv",
        top_ring,
        delimiter=",",
        header="easting_m,northing_m,elevation_m",
        comments="",
        fmt="%.6f",
    )
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    build()
