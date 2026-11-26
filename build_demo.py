"""Build a completely offline HTML explorer from measured reconstruction outputs."""
from pathlib import Path
import argparse,json,base64,csv
import numpy as np,cv2,pycolmap as pc
from scipy.spatial import cKDTree
from plotly.offline import get_plotlyjs


def build(root,data):
    root,data=Path(root),Path(data); assets={};rows=[]
    for metric in sorted((root/'results').glob('*/*/metrics.json')):
        m=json.loads(metric.read_text());rows.append({k:v for k,v in m.items() if k not in ['config','cameras','estimated_intrinsics']})
        if m['status']!='reconstructed':continue
        folder=metric.parent;cloud=np.load(folder/'cloud.npz');xyz=cloud['xyz'];center=np.median(xyz,axis=0);scale=float(np.percentile(np.linalg.norm(xyz-center,axis=1),90))
        rec=pc.Reconstruction(folder/'selected');views=sorted([im for im in rec.images.values() if im.has_pose],key=lambda im:im.name)
        rotation=views[len(views)//2].cam_from_world().rotation.matrix()
        basis=np.array([[1,0,0],[0,0,1],[0,-1,0.]])@rotation
        key=m['scene']+'/'+m['variant'];rng=np.random.default_rng(42)
        def pack(x,c,err=None,track=None):
            ind=np.arange(len(x));
            if len(x)>45000:ind=rng.choice(len(x),45000,replace=False)
            return {'xyz':np.round(((x[ind]-center)@basis.T)/scale,5).tolist(),'rgb':c[ind].tolist(),'error':np.round(err[ind],3).tolist() if err is not None else None,'track':track[ind].tolist() if track is not None else None}
        payload={'metrics':m,'sparse':pack(xyz,cloud['rgb'],cloud['error'],cloud['track']),'center':center.tolist(),'scale':scale,
          'cameras':np.round(((np.array([c['center'] for c in sorted(m['cameras'],key=lambda c:c['name'])])-center)@basis.T)/scale,5).tolist()}
        if (folder/'dense.npz').exists():
            dense=np.load(folder/'dense.npz');x=dense['xyz'];c=dense['rgb']
            if len(x)>20:
                dist,_=cKDTree(x).query(x,k=9,workers=4);avg=dist[:,1:].mean(axis=1);keep=avg<=np.mean(avg)+2*np.std(avg)
                payload['dense']=pack(x[keep],c[keep]);payload['dense_count']=int(keep.sum());payload['dense_total']=len(x)
        p=sorted((data/m['scene']/'input').glob('*.jpg'))[8];im=cv2.imread(str(p));im=cv2.resize(im,(640,360));lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB);lab[:,:,0]=cv2.createCLAHE(2,(8,8)).apply(lab[:,:,0]);en=cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
        def uri(a):return 'data:image/jpeg;base64,'+base64.b64encode(cv2.imencode('.jpg',a,[cv2.IMWRITE_JPEG_QUALITY,80])[1]).decode()
        payload['original']=uri(im);payload['enhanced']=uri(en);assets[key]=payload
    with (root/'results'/'benchmark.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    template=(root/'viewer_template.html').read_text();html=template.replace('/*PLOTLY*/',get_plotlyjs()).replace('/*DATA*/',json.dumps(assets,separators=(',',':')))
    (root/'AquaRecon.html').write_text(html)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--data',type=Path,required=True);a=p.parse_args();build(a.root,a.data)
