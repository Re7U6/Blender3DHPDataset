from distutils.core import setup

import bpy
import bmesh
import math
import os
import random
import json

from pathlib import Path

from blenderproc.python.types.MeshObjectUtility import scene_ray_cast
from mathutils import Vector

# H3.6Mに準ずる32個の関節点のうち、動作に関わる17個の関節点を用いる
# H3.6Mとbvhのキーポイントの対応付けを以下のように定義する
bone_mapping = {
    'Hips': 'Hip',
    'UpperLeg_R': 'RHip',
    'LowerLeg_R': 'RKnee',
    'Foot_R': 'RFoot' ,
    'UpperLeg_L': 'LHip',
    'LowerLeg_L': 'LKnee',
    'Foot_L': 'LFoot',
    'Spine': 'Spine',
    'Chest': 'Thorax',
    'Neck': 'Neck',
    'Head': 'Head',
    'Shoulder_R': 'RShoulder',
    'UpperArm_R': 'RElbow',
    'LowerArm_R': 'RWrist',
    'Shoulder_L': 'LShoulder',
    'UpperArm_L': 'LElbow',
    'LowerArm_L': 'LWrist'
}
bone_order = {
    'Hip': 0,
    'RHip': 1,
    'RKnee': 2,
    'RFoot': 3,
    'LHip': 4,
    'LKnee': 5,
    'LFoot': 6,
    'Spine': 7,
    'Thorax': 8,
    'Neck': 9,
    'Head': 10,
    'LShoulder': 11,
    'LElbow': 12,
    'LWrist': 13,
    'RShoulder': 14,
    'RElbow': 15,
    'RWrist': 16
}



# bandaiデータセットを使う場合、rootと手は使わないので隠す
# ただし足はヘッドを使うため残す
bones_to_hide = ['joint_Root', 'Hand_R', 'Hand_L', 'Toes_R', 'Toes_L']


def setup_bvh(bvh_file):
    '''
    モーションデータ（.bvh）のセットアップ
    '''

    # すべてのオブジェクト、モーションデータを削除
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.outliner.orphans_purge()
    for action in bpy.data.actions:
        bpy.data.actions.remove(action)

    # import bvh
    bpy.ops.import_anim.bvh(
        filepath=str(bvh_file),
        filter_glob='*.bvh',
        target='ARMATURE',
        global_scale=0.01,
        frame_start=1,
        use_fps_scale=False,
        use_cyclic=False,
        rotate_mode='NATIVE',
        axis_forward='-Z',
        axis_up='Y'
    )

    armature = bpy.data.objects[-1]
    bpy.ops.object.mode_set(mode='EDIT')

    for bone_name in bones_to_hide:
        bone = armature.data.edit_bones.get(bone_name)
        if bone:
            armature.data.edit_bones.remove(bone)

    bpy.ops.object.mode_set(mode='OBJECT')

def get_keyframe_range():
    '''
    キーフレームが存在するフレームの最大と最小を返す
    '''
    keyframes = set()
    for obj in bpy.data.objects:
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for keyframe in fcurve.keyframe_points:
                    keyframes.add(int(keyframe.co[0]))
    return min(keyframes), max(keyframes)

def setup_environment(radius=5, segments=8, ring_count=10, focal_length=35.0):
    '''
    カメラとカメラを動かすsphere空間を設定
    '''
    # sphereを設定
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        segments=segments,
        ring_count=ring_count,
        location=(0, 0, 1)
    )
    uv_sphere = bpy.context.object
    sphere_name = uv_sphere.name
    bpy.ops.object.mode_set(mode='EDIT')
    mesh = bmesh.from_edit_mesh(uv_sphere.data)

    # 球全体を下に動かし、球の下半分と一番上の頂点を削除
    for vert in mesh.verts:
        vert.co.z -= 0.5
        vert.select = False
        if vert.co.z < -0.5 or vert.co.z == 4.5:
            vert.select = True

    bmesh.ops.delete(mesh, geom=[v for v in mesh.verts if v.select], context='VERTS')
    bmesh.update_edit_mesh(uv_sphere.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    vertex_count = len(uv_sphere.data.vertices)


    # カメラを設定
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera_name = camera.name
    camera.data.lens = focal_length
    target_object = bpy.data.objects.get('Sphere')

    constraint = camera.constraints.new(type='TRACK_TO')
    constraint.target = target_object
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    return sphere_name, camera_name, vertex_count

def setup_camera(vertex_index, sphere_name='Sphere', camera_name='Camera'):
    '''
    カメラの位置設定
    '''
    sphere_name = sphere_name
    camera_name = camera_name
    vertex_index = vertex_index

    obj = bpy.data.objects.get(sphere_name)
    camera = bpy.data.objects.get(camera_name)

    if 0 <= vertex_index < len(obj.data.vertices):
        vertex_world_position = obj.matrix_world @ obj.data.vertices[vertex_index].co
        camera.location = vertex_world_position

    camera_position = camera.location
    camera_world_rotation = camera.matrix_world.to_quaternion()
    quaternion = camera_world_rotation
    azimuth = camera_world_rotation.to_euler()[2]
    azimuth = round(math.degrees(azimuth))

    return camera_position, azimuth, quaternion


def camera_resolution(x=224, y=224, per=100):
    '''
    カメラ解像度設定
    '''
    bpy.context.scene.render.resolution_x = x
    bpy.context.scene.render.resolution_y = y
    bpy.context.scene.render.resolution_percentage = per

def get_3d_coordinates():



def get_coordinates(scene, camera, bone, resolution_x, resolution_y):
    '''
    カメラビューにおける二次元座標を取得
    '''
    cam_inv_matrix = camera.matrix_world.inverted()  # カメラの逆行列（ビュー空間への変換用）

    # 足ボーンの場合はヘッドをそれ以外ではテールの座標を取得
    if bone.name in ['UpperLeg_R', 'UpperLeg_L', 'LowerLeg_R', 'LowerLeg_L', 'Foot_R', 'Foot_L', 'Hips', 'Spine']:
        bone_world_pos = bone.head
    else:
        bone_world_pos = bone.tail  # ボーンのワールド座標を取得
    view_pos = cam_inv_matrix @ bone_world_pos  # ビュー空間への変換
    view_pos_4d = view_pos.to_4d()  # 4次元ベクトルに変換

    # カメラのプロジェクションマトリックスを取得
    render = scene.render
    aspect_ratio = render.resolution_x / render.resolution_y
    projection_matrix = camera.calc_matrix_camera(
        bpy.context.evaluated_depsgraph_get(),
        x=render.resolution_x,
        y=render.resolution_y,
        scale_x=aspect_ratio
    )
    clip_space = projection_matrix @ view_pos_4d  # クリップ空間への変換
    ndc = clip_space.xy / clip_space.w  # 正規化デバイス座標（NDC）への変換

    # スクリーン座標への変換
    coordinate_x = (ndc.x + 1) * render.resolution_x / 2
    coordinate_y = (1 - ndc.y) * render.resolution_y / 2

    if coordinate_x < 0 or coordinate_y < 0 or coordinate_x > resolution_x or coordinate_y > resolution_y:
        coordinate_x = coordinate_y = 0

    coordinate_x = round(coordinate_x)
    coordinate_y = round(coordinate_y)

    return [coordinate_x, coordinate_y], list(bone_world_pos), bone.name

def sort_keypoints(coordinats, bone_name, keypoint_list):
    key = bone_mapping[bone_name]
    value = bone_order[key]
    keypoint_list[value] = coordinats


def save_keypoints(annotations, output_path):
    with open(os.path.join(output_path, 'pose.json'), 'w') as f:
        for anno in annotations:
            line = json.dumps(anno)
            f.write(line + '\n')


def main(num_data, input_path, output_path):
    resolution_x = 1920 # x横解像度
    resolution_y = 1080 # y縦解像度

    data_dir = Path(input_path)
    bvh_files = [path for path in data_dir.iterdir() if path.suffix == '.bvh']

    # カメラ解像度の初期化
    camera_resolution(resolution_x, resolution_y, 100)

    annotations = []
    # 環境の作成
    sphere_name, camera_name, vertex_count = setup_environment(radius=5, segments=8, ring_count=10, focal_length=35.0)

    for i in range(num_data):
        # bvhデータのロード
        bvh_file = random.choice(bvh_files)
        setup_bvh(bvh_file)

        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

        keypoints_2d = []
        keypoints_3d = []
        camera = []
        # キーフレーム範囲を取得
        start_frame, end_frame = get_keyframe_range()

        for vertex_index in range(vertex_count):
            # カメラの位置設定
            camera_position, azimuth, quaternion, scene = setup_camera(vertex_index, sphere_name, camera_name)

            for frame in range(start_frame, end_frame + 1):
                # フレームのロード
                bpy.context.scene.frame_set(frame)
                scene = bpy.context.scene
                camera = bpy.data.objects['Camera']

                keypoint_2d = [0 for _ in range(17)]
                keypoint_3d = [0 for _ in range(17)]
                # ボーンのカメラビューにおける2D座標を取得
                for bone in armature.pose.bones:
                    coordinates2d, coordinates3d,bone_name = get_coordinates(scene, camera, bone, resolution_x, resolution_y)
                    if 0 in coordinates2d:
                        break
                    sort_keypoints(coordinates2d, bone_name, keypoint_2d)
                    sort_keypoints(coordinates3d, bone_name, keypoint_3d)

                keypoints_2d.append(keypoint_2d)
                keypoints_3d.append(keypoint_2d)




if __name__ == '__main__':
    input_path = '/home/masuryui/Bandai-Namco-Research-Motiondataset/dataset/Bandai-Namco-Research-Motiondataset-1/data'
    output_path = '/home/masuryui/Desktop/data'
    num_data = 50
    main(num_data, input_path, output_path)
