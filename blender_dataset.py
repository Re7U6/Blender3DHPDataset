import numpy as np
import copy
from common.skeleton import Skeleton
from common.mocap_dataset import MocapDataset
from common.camera import normalize_screen_coordinates

blender_skeleton = Skeleton(parents=[-1, 0, 1, 2, 3, 0, 4, 5, 6, 0, 7, 8, 9, 10, 8,
                            11, 12, 13, 8, 14, 15, 16],
                            joints_left=[4, 5, 6, 11, 12, 13],
                            joints_right=[1, 2, 3, 14, 15, 16])

blender_cameras_intrinsic_params = [
    {
        'id': '',
        'center': [],
        'focal_length': [],
        'radial_distortion': [],
        'tangential_distortion': [],
        'res_w': 1,
        'res_h': 1,
        'azimuth': 1,
    },
    {
        'id': '',
        'center': [],
        'focal_length': [],
        'radial_distortion': [],
        'tangential_distortion': [],
        'res_w': 1,
        'res_h': 1,
        'azimuth': 1,
    },
]

blender_cameras_extrinsic_params = {
    'S1': [
        {
            'orientation': [],
            'translation': [],
        },
        {
            'orientation': [],
            'translation': [],
        },
        {
            'orientation': [],
            'translation': [],
        },
        {
            'orientation': [],
            'translation': [],
        },
    ],
    'S2': [
        {
            'orientation': [],
            'translation': [],
        },
        {
            'orientation': [],
            'translation': [],
        },
        {
            'orientation': [],
            'translation': [],
        },
        {
            'orientation': [],
            'translation': [],
        },
    ],
}

class blenderDataset(MocapDataset):
    def __init__(self, path):
        super().__init__(fps=60, skeleton=blender_skeleton)

        self.cameras = copy.deepcopy(blender_cameras_extrinsic_params)
        for cameras in self._cameras.values():
            for i, cam in enumerate(cameras):
                cam.update(blender_cameras_intrinsic_params[i])
                for k, v in cam.items():
                    if k not in ['id', 'res_w', 'res_h']:
                        cam[k] = np.array(v, dtype=np.float32)

                # カメラフレームの正規化
                if 'center' in cam:
                    cam['center'] = normalize_screen_coordinates(cam['center'], w=cam['res_w'], h=cam['res_h']).astype(
                        'float32')
                if 'focal_length' in cam:
                    cam['focal_length'] = cam['focal_length'] / cam['res_w'] * 2
                if 'translation' in cam:
                    cam['translation'] = cam['translation']/1000 # ミリメートルをメートルに変換

                # 固有パラメータ・ベクトルの追加
                if 'center' in cam:
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