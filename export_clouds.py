"""Export bundled compressed dense clouds to PLY without rerunning reconstruction."""
from pathlib import Path
import numpy as np
for source in (Path(__file__).parent/'results').glob('*/raw/dense.npz'):
    data=np.load(source);xyz,rgb=data['xyz'],data['rgb'];target=source.with_suffix('.ply')
    with target.open('w') as f:
        f.write('ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'%len(xyz))
        for point,color in zip(xyz,rgb):f.write(' '.join(map(str,[*point,*color]))+'\n')
    print(target)
