import numpy as np
import copy
import ast
from common.skeleton import Skeleton
from common.mocap_dataset import MocapDataset
from common.camera import normalize_screen_coordinates

# スケルトンの親子関係と左右の定義
blender_skeleton = Skeleton(parents=[-1, 0, 1, 2, 0, 4, 5, 0, 7, 8, 9, 8, 11, 12, 8,14, 15],
                            joints_left=[4, 5, 6, 11, 12, 13],
                            joints_right=[1, 2, 3, 14, 15, 16])

# カメラの内部・外部パラメータをtxtファイルから読み込み
with open('common/camera_intrinsics.txt', 'r') as file:
   intrinsic = file.read()
blender_cameras_intrinsic_params = ast.literal_eval(intrinsic)

with open('common/camera_extrinsics.txt', 'r') as file:
   extrinsic = file.read()
blender_cameras_extrinsic_params = ast.literal_eval(extrinsic)


class BlenderDataset(MocapDataset):
    def __init__(self, path):
        super().__init__(fps=30, skeleton=blender_skeleton)

        self._cameras = copy.deepcopy(blender_cameras_extrinsic_params)
        for cameras in self._cameras.values():
            for i, cam in enumerate(cameras):
                cam.update(blender_cameras_intrinsic_params[i])
                for k, v in cam.items():
                    if k not in ['id', 'res_w', 'res_h']:
                        cam[k] = np.array(v, dtype='float32')

                # カメラフレームの正規化
                cam['center'] = normalize_screen_coordinates(cam['center'], w=cam['res_w'], h=cam['res_h']).astype('float32')
                cam['focal_length'] = cam['focal_length'] / cam['res_w'] * 2
                if 'translation' in cam:
                    cam['translation'] = cam['translation']/1000 # ミリメートルをメートルに変換

                # 固有パラメータ・ベクトルの追加
                cam['intrinsic'] = np.concatenate((cam['focal_length'],
                                                   cam['center'],
                                                   cam['radial_distortion'],
                                                   cam['tangential_distortion']))

        # シリアライズされたデータセットを読み込む
        data = np.load(path, allow_pickle=True)['positions_3d'].item()

        self._data = {}
        for subject, actions in data.items():
            self._data[subject] = {}
            for action_name, positions in actions.items():
                self._data[subject][action_name] = {
                    'positions': positions,
                    'cameras': self._cameras[subject],
                }