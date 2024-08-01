import bpy
import os
import random
import json

from pathlib import Path
from mathutils import Vector


def get_keyframe_range():
    '''
    return max and min keyframes
    '''
    keyframes = set()
    for obj in bpy.data.objects:
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for keyframe in fcurve.keyframe_points:
                    keyframes.add(int(keyframe.co[0]))
    return min(keyframes), max(keyframes)


def setup(bvh_file):
    '''

    Args:
        bvh_file: motion data (bvh)
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

    for armature_data in bpy.data.armatures:
        armature = None
        for obj in bpy.data.objects:
            if obj.data == armature_data:
                armature = obj
                break

        if armature:
            # rootボーンを隠す
            armature_data.bones[0].hide = True

            # face（node, eye x 2, ear x 2）ボーンを追加
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')

            head2nose = Vector((-0.03, 0, 0.04))
            nose2eyeR = Vector((0.02, 0.02, -0.0075))
            nose2eyeL = Vector((0.02, -0.02, -0.0075))
            eyeR2earR = Vector((-0.01, 0.025, -0.02))
            eyeL2earL = Vector((-0.01, -0.025, -0.02))

            edit_bones = armature.data.edit_bones
            parent_bone = edit_bones["Head"]
            new_bone = edit_bones.new("Nose")
            new_bone.head = parent_bone.tail
            new_bone.tail = new_bone.head + head2nose
            new_bone.parent = parent_bone

            edit_bones = armature.data.edit_bones
            parent_bone = edit_bones["Nose"]
            new_bone = edit_bones.new("Eye_R")
            new_bone.head = parent_bone.tail
            new_bone.tail = new_bone.head + nose2eyeR
            new_bone.parent = parent_bone

            edit_bones = armature.data.edit_bones
            parent_bone = edit_bones["Nose"]
            new_bone = edit_bones.new("Eye_L")
            new_bone.head = parent_bone.tail
            new_bone.tail = new_bone.head + nose2eyeL
            new_bone.parent = parent_bone

            edit_bones = armature.data.edit_bones
            parent_bone = edit_bones["Eye_R"]
            new_bone = edit_bones.new("Ear_R")
            new_bone.head = parent_bone.tail
            new_bone.tail = new_bone.head + eyeR2earR
            new_bone.parent = parent_bone

            edit_bones = armature.data.edit_bones
            parent_bone = edit_bones["Eye_L"]
            new_bone = edit_bones.new("Ear_L")
            new_bone.head = parent_bone.tail
            new_bone.tail = new_bone.head + eyeL2earL
            new_bone.parent = parent_bone

            bpy.ops.object.mode_set(mode='OBJECT')


def camera_resolution(x=224, y=224, per=100):
    '''
    camera resolution settings
    '''
    bpy.context.scene.render.resolution_x = x
    bpy.context.scene.render.resolution_y = y
    bpy.context.scene.render.resolution_percentage = per


def random_camera(target, camera_area, scope):
    '''
    return random camera position
    '''
    while True:
        pos_x = random.uniform(camera_area[0], camera_area[1])
        pos_y = random.uniform(camera_area[2], camera_area[3])
        pos_z = random.uniform(camera_area[4], camera_area[5])
        camera_position = Vector((pos_x, pos_y, pos_z))

        # ターゲットと近すぎる場合を除外
        position_value = (camera_position - target).length
        if position_value >= scope:
            break

    return camera_position


def get_2d_coordinates_from_bone(scene, camera, bone, resolution_x, resolution_y):
    '''
    return 2d bone coordinates in the camera view
    '''
    cam_inv_matrix = camera.matrix_world.inverted()  # カメラの逆行列（ビュー空間への変換用）
    if bone.name in ['UpperLeg_R', 'UpperLeg_L', 'LowerLeg_R', 'LowerLeg_L', 'Foot_R', 'Foot_L']:
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
    i = 1

    if coordinate_x < 0 or coordinate_y < 0 or coordinate_x > resolution_x or coordinate_y > resolution_y:
        coordinate_x = coordinate_y = 0
        i = 0

    coordinate_x = round(coordinate_x)
    coordinate_y = round(coordinate_y)

    return coordinate_x, coordinate_y, i


def sort_keypoints(key_dict):
    keypoints = key_dict['Nose'] + \
                key_dict['Chest'] + \
                key_dict['Shoulder_R'] + \
                key_dict['UpperArm_R'] + \
                key_dict['LowerArm_R'] + \
                key_dict['Shoulder_L'] + \
                key_dict['UpperArm_L'] + \
                key_dict['LowerArm_L'] + \
                key_dict['UpperLeg_R'] + \
                key_dict['LowerLeg_R'] + \
                key_dict['Foot_R'] + \
                key_dict['UpperLeg_L'] + \
                key_dict['LowerLeg_L'] + \
                key_dict['Foot_L'] + \
                key_dict['Eye_R'] + \
                key_dict['Ear_R'] + \
                key_dict['Eye_L'] + \
                key_dict['Ear_L']

    return keypoints


def make_annotation(annotations, id, keypoints):
    anno = {
        'data_id': id,
        'keypoints': keypoints
    }
    annotations.append(anno)


def write_annotations(annotations, output_path):
    with open(os.path.join(output_path, 'pose.json'), 'w') as f:
        for anno in annotations:
            line = json.dumps(anno)
            f.write(line + '\n')


def main(num_data, input_path, output_path):
    camera_area = (-4, 4, -4, 4, 0.5, 1)
    scope = 2
    resolution_x = 320 # 横解像度
    resolution_y = 240 # 縦解像度

    data_dir = Path(input_path)
    bvh_files = [path for path in data_dir.iterdir() if path.suffix == '.bvh']

    # カメラ解像度の初期化
    camera_resolution(resolution_x, resolution_y, 100)

    annotations = []
    for i in range(num_data):
        bvh_file = random.choice(bvh_files)
        setup(bvh_file)

        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

        target = armature.pose.bones[2]
        target = armature.matrix_world @ target.head

        # カメラの位置設定
        camera_position = random_camera(target, camera_area, scope)
        bpy.ops.object.camera_add(location=camera_position)
        camera = bpy.context.object

        # トラッキングコンストレイントを追加
        constraint = camera.constraints.new(type='TRACK_TO')
        constraint.target = armature
        constraint.subtarget = armature.data.bones[2].name

        # キーフレーム範囲を取得
        start_frame, end_frame = get_keyframe_range()
        random_frame = random.randint(start_frame, end_frame)
        bpy.context.scene.frame_set(random_frame)

#         for area in bpy.context.screen.areas:
#             if area.type == 'VIEW_3D':
#                 # ビュー3Dエリアのスペースのタイプを確認
#                 override = bpy.context.copy()
#                 override['area'] = area
#                 # カメラビューに切り替える
#                 bpy.ops.view3d.view_camera(override)
#                 break
#
        # カメラオブジェクトを取得
        scene = bpy.context.scene
        camera = bpy.data.objects['Camera']

        key_dict = {}
        keypoints = []
        # ボーンのカメラビューにおける2D座標を取得
        for bone in armature.pose.bones:
            anno = get_2d_coordinates_from_bone(scene, camera, bone, resolution_x, resolution_y)
            key_dict[bone.name] = anno

        keypoints = list(sort_keypoints(key_dict))
        make_annotation(annotations, i+1, keypoints)

    # 書き込み
    write_annotations(annotations, output_path)

if __name__ == '__main__':
    input_path = '/home/masuryui/Bandai-Namco-Research-Motiondataset/dataset/Bandai-Namco-Research-Motiondataset-1/data'
    output_path = '/home/masuryui/Desktop/data'
    num_data = 50
    main(num_data, input_path, output_path)
