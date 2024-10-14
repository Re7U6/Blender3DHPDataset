import bpy
import math
from pathlib import Path
from tqdm import tqdm

import bmesh
import numpy as np
# np.set_printoptions(suppress=True)


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

subjects=['Train', 'Validate']

# bandaiデータセットを使う場合、rootと手は使わないので隠す
# ただし足はヘッドを使うため残す
bones_to_hide = ['joint_Root', 'Hand_R', 'Hand_L', 'Toes_R', 'Toes_L']


def initialize_armature():
    '''
    アーマチュアの初期化
    '''
    # アーマチュアとアクションデータを削除
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            obj.select_set(True)
        else:
            obj.select_set(False)
    bpy.ops.object.delete()
    bpy.ops.outliner.orphans_purge()
    # for action in bpy.data.actions:
    #     bpy.data.actions.remove(action)


def setup_bvh(bvh_file):
    '''
    モーションデータ（.bvh）のセットアップ
    '''
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

    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
    bpy.ops.object.mode_set(mode='EDIT')

    for bone_name in bones_to_hide:
        bone = armature.data.edit_bones.get(bone_name)
        if bone:
            armature.data.edit_bones.remove(bone)

    # Headが無いときは
    # for bone_name in bones_to_hide:
    #     bone = armature.data.edit_bones.get(bone_name)
    #     if bone:
    #         armature.data.edit_bones.remove(bone)
    #
    # edit_bones = armature.data.edit_bones
    # head_bone = edit_bones.get('Head')
    # neck_bone = edit_bones.get('Neck')
    # if head_bone.length < 0.5:
    #     edit_bones.remove(head_bone)
    #     new_head_bone = edit_bones.new('Head')
    #     direction = (neck_bone.tail - neck_bone.head).normalized()
    #     head_length = neck_bone.length
    #     new_head_bone.head = neck_bone.tail
    #     new_head_bone.tail = neck_bone.tail + direction * head_length
    #     new_head_bone.parent = neck_bone

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
        vert.co.z *= 0.4
        # vert.co.z -= 0.5
        vert.select = False
        if vert.co.z < -0.5 or vert.co.z == 2:
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

    bpy.context.view_layer.update()
    camera_position = camera.location
    camera_world_rotation = camera.matrix_world.to_quaternion()
    quaternion = camera_world_rotation
    azimuth = camera_world_rotation.to_euler()[2]
    azimuth = round(math.degrees(azimuth))

    return [camera_position, azimuth, quaternion]


def camera_resolution(x=224, y=224, per=100):
    '''
    カメラ解像度設定
    '''
    bpy.context.scene.render.resolution_x = x
    bpy.context.scene.render.resolution_y = y
    bpy.context.scene.render.resolution_percentage = per


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
    '''
    キーポイントの並び替え
    '''
    key = bone_mapping[bone_name]
    value = bone_order[key]
    keypoint_list[value] = coordinats



def main(input_path, output_path):
    resolution_x = 1920 # x横解像度
    resolution_y = 1080 # y縦解像度

    data_dir = Path(input_path)
    bvh_files = [path for path in data_dir.iterdir() if path.suffix == '.bvh']

    # カメラ解像度の初期化
    camera_resolution(resolution_x, resolution_y, 100)

    # 環境の初期化
    if bpy.ops.objects:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
    bpy.ops.outliner.orphans_purge()
    for action in bpy.data.actions:
        bpy.data.actions.remove(action)

    # 環境の設定
    sphere_name, camera_name, vertex_count = setup_environment(radius=5, segments=8, ring_count=10, focal_length=35.0)

    output_3d = {}
    output_2d = {}

    for idx, bvh_file in enumerate(tqdm(bvh_files, desc=f'bvh処理ちう')):
        output_3d[f'data{idx+1}'] = {}
        output_2d[f'data{idx+1}'] = {}
        # アーマチュア周りを初期化
        initialize_armature()

        # bvhデータをロード
        setup_bvh(bvh_file)

        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

        for vertex_index in tqdm(range(vertex_count), desc=f'bvh処理状況{idx+1}/{len(bvh_files)}'):
            # カメラの位置設定
            camera_status = setup_camera(vertex_index, sphere_name, camera_name)

            # キーフレーム範囲を取得
            start_frame, end_frame = get_keyframe_range()

            positions_2d = []
            positions_3d = []
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
                    sort_keypoints(coordinates2d, bone_name, keypoint_2d)
                    sort_keypoints(coordinates3d, bone_name, keypoint_3d)

                # 2d座標に0を含まないようにする
                if all(0 not in i for i in keypoint_2d):
                    positions_2d.append(keypoint_2d)
                    positions_3d.append(keypoint_3d)

            # 空データは使わない
            if len(positions_2d) != 0:
                positions_2d = [np.round(np.array(positions_2d, dtype=np.float32), 6)] # 2dは配列の中に
                positions_3d = np.round(np.array(positions_3d, dtype=np.float32), 6)
                output_2d[f'data{idx+1}'][f'C{vertex_index+1}'] = positions_2d
                output_3d[f'data{idx+1}'][f'C{vertex_index+1}'] = positions_3d

        # if idx == 0:
        #     break

    # カメラ情報を保存
    for vertex_index in range(vertex_count):
        camera_position, azimuth, quaternion = setup_camera(vertex_index, sphere_name, camera_name)
        camera_position = [x * 1000 for x in list(camera_position)]
        with open('camera.txt', 'a') as file:
            file.write("{\n")
            file.write(f"    'id': 'C{vertex_index+1}',\n")
            file.write(f"    'orientation': {list(quaternion)},\n")
            file.write(f"    'translation': {camera_position},\n")
            file.write(f"    'azimuth': {azimuth},\n")
            file.write("    'focal_length': [35.0],\n")
            file.write("    'res_w': 1920,\n")
            file.write("    'res_h': 1080,\n")
            file.write("},\n")


    print("3dデータ保存ちう...")
    np.savez_compressed('data_3d_blender.npz', positions_3d=output_3d)

    metadata = {
        'num_joints': 17,
        'keypoints_symmetry': [[4, 5, 6, 11, 12, 13], [1, 2, 3, 14, 15, 16]]
    }
    print("2dデータ保存ちう...")
    np.savez_compressed('data_2d_blender_gt.npz', positions_2d=output_2d, metadata=metadata)

    print("完了！")

if __name__ == '__main__':
    input_path = '/home/masuryui/Bandai-Namco-Research-Motiondataset/dataset/Bandai-Namco-Research-Motiondataset-1/data'
    output_path = '/home/masuryui/Desktop/data'
    main(input_path, output_path)
