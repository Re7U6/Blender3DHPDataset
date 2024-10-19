# Blender3DHumanPoseDataset

Script to generate data for 3D skeletal estimation in blender from a bvh file.

Generate data in npz format used by [VideoPose3D](https://github.com/facebookresearch/VideoPose3D/blob/main/DATASETS.md).

## Prerequisites
- blender 3.3.1 (not tried but may work with 2.8.0 or above)
- tqdm

## How to Use

### Generating Dataset

   `genDataset3D.py` imports the bvh file and generates the following

- keypoints（`data_2d_blender_gt.npz`, `data_3d_blender.npz`）
- camera info（`camera_extrinsics.txt`, `camera_intrinsics.txt`）


```s
$ blender HPD3D.blend
```

### Training and Evaluation on generated datasets

For models based on [VideoPose3D](https://github.com/facebookresearch/VideoPose3D), such as [MixSTE](https://github.com/JinluZhang1126/MixSTE) and [KTPFormer](https://github.com/JihuaPeng/KTPFormer):

Place the keypoint files (`data_2d_blender_gt.npz`, `data_3d_blender.npz`) in the `data/` directory.
Place the camera information files (`camera_extrinsics.txt`, `camera_intrinsics.txt`) and blender_dataset.py in the `common/` directory.

Add the following code for blender in the python file for training and evaluation.

Loading part of the dataset：
```python
print('Loading dataset...')
dataset_path = 'data/data_3d_' + args.dataset + '.npz'
if args.dataset == 'h36m':
    from common.h36m_dataset import Human36mDataset
    dataset = Human36mDataset(dataset_path)
    
    ...

elif args.dataset.startswith('blender'):
    from common.blender_dataset import BlenderDataset
    dataset = BlenderDataset(dataset_path)
```

Training part：
```python
if args.dataset=='h36m':
    w_mpjpe = torch.tensor([1, 1, 2.5, 2.5, 1, 2.5, 2.5, 1, 1, 1, 1.5, 1.5, 4, 4, 1.5, 4, 4]).cuda()

elif args.dataset=='blender':
    w_mpjpe = torch.tensor([1, 1, 2.5, 2.5, 1, 2.5, 2.5, 1, 1, 1, 1.5, 1.5, 4, 4, 1.5, 4, 4]).cuda()
```

Example of execution during Training：
```s
$ python3 run.py -d blender -k gt -c checkpoint -str [subject] -ste [subject]
```

Example of execution at Evaluation：
```s
$ python3 run.py -d blender -k gt -c checkpoint -str [subject] -ste [subject] --evaluation ~.bin
```
