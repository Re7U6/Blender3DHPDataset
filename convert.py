import argparse
import os
import numpy as np
import h5py
from glob import glob


import sys
sys.path.append('../')
from blender_dataset import blenderDataset
from camera import world_to_camera, project_to_2d, image_coordinates

output_filename = 'data_3d_origin'
output_filename_2d = 'data_2d_origin_gt'
subjects = ['Train', 'Validate']

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='original 3d/2d skeleton dataset converter')

    # blenderで作成した座標データをデータセットに変換
    parser.add_argument('-3d', '--convert-3d', default = '', type=str, help='3d data directory')
    parser.add_argument('-2d', '--convert-2d', default='', type=str, help='2d data directory')

    args = parser.parse_args()

    if os.path.exists(output_filename + '.npz'):
        print('既に', output_filename + '.npz は存在するよ')
        exit(0)
    if os.path.exists(output_filename_2d + '.npz'):
        print('既に', output_filename_2d + '.npz は存在するよ')
        exit(0)

    if args.convert_3d and args.convert_2d:
        print('blenderの3d座標データ：', args.convert_3d)
        print('blenderの2d座標データ：', args.convert_2d)


        output = {}
        output_2d = {}
        for subject in subjects:
            output[subject] = {}
            output_2d[subject] = {}


            file_list = glob('blender/' + subject + '/3D_positions/*.h5')
            file_list2d = glob('blender/' + subject + '/2D_positions/*.h5')

            assert len(file_list) == len(file_list2d), "3dのデータ数" + str(len(file_list)) + "と2dのデータ数" + str(len(file_list2d)) + "が一致していないお"

            print('3dデータ変換...')
            for f3 in file_list:
                scene = os.path.splitext(os.path.basename(f3))[0]
                with h5py.File(f3) as hf3:
                    positions = hf3['3D_positions'][:].reshape(-1, 17, 3)
                    positions /= 1000 # ミリメートルに変換
                    output[subject][scene] = positions



            print('2dデータ変換...')
            for f2 in file_list2d:
                scene = os.path.splitext(os.path.basename(f2))[0]
                with h5py.File(f2) as hf2:
                    positions_2d = hf2['2D_positions'][:].reshape(-1, 17, 2)
                    output_2d[subject][scene] = positions_2d

        print('3dデータ保存ちう...')
        np.savez_compressed(output_filename, positinos_3d=output)


        metadata = {
            'num_joints': 17,
            'keypoints_symmetry': [[4, 5, 6, 11, 12, 13], [1, 2, 3, 14, 15, 16]]
        }
        print('2dデータ保存ちう...')
        np.savez_compressed(output_filename_2d, positinos_2d=output_2d, metadata=metadata)

        print('終了')

    else:
        print('blenderで作成した3d・2dデータのディレクトリが必要です')