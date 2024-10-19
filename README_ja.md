# Blender3DHumanPoseDataset

Blenderでbvhファイルから3D骨格推定用のデータセットを作成するスクリプト

[VideoPose3D](https://github.com/facebookresearch/VideoPose3D/blob/main/DATASETS.md)で用いられるnpz形式のデータを生成する。

## 環境
- blender 3.3.1 (試してはいないが2.8.0以上ならいけそう)
- tqdm

## 使い方

### データセットの生成

   `genDataset3D.py`はbvhファイルを読み込み、

- キーポイント（`data_2d_blender_gt.npz`, `data_3d_blender.npz`）
- カメラ情報（`camera_extrinsics.txt`, `camera_intrinsics.txt`）

   を生成する。以下のコマンドでbvhファイルが格納されたディレクトリと

```s
$ blender HPD3D.blend
```

### 生成したデータセットで学習・評価

[VideoPose3D](https://github.com/facebookresearch/VideoPose3D)をベースとした[MixSTE](https://github.com/JinluZhang1126/MixSTE)や[KTPFormer](https://github.com/JihuaPeng/KTPFormer)といったモデルで
   
`data/`にキーポイント（`data_2d_blender_gt.npz`, `data_3d_blender.npz`）

`common/`にカメラ情報（`camera_extrinsics.txt`, `camera_intrinsics.txt`）と
   `blender_dataset.py`を配置する。

学習・評価を行うpythonファイルにてblenderに関する以下のコード追記する。

データセットを読み込み部分：
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

学習部分：
```python
if args.dataset=='h36m':
    w_mpjpe = torch.tensor([1, 1, 2.5, 2.5, 1, 2.5, 2.5, 1, 1, 1, 1.5, 1.5, 4, 4, 1.5, 4, 4]).cuda()

elif args.dataset=='blender':
    w_mpjpe = torch.tensor([1, 1, 2.5, 2.5, 1, 2.5, 2.5, 1, 1, 1, 1.5, 1.5, 4, 4, 1.5, 4, 4]).cuda()
```

学習時の実行例：
```s
$ python3 run.py -d blender -k gt -c checkpoint -str [subject] -ste [subject]
```

評価時の実行例：
```s
$ python3 run.py -d blender -k gt -c checkpoint -str [subject] -ste [subject] --evaluation ~.bin
```

