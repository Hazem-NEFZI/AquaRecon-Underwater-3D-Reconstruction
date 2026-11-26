"""AquaRecon: reproducible, CPU underwater structure-from-motion benchmark."""
from pathlib import Path
import argparse, json, time, hashlib, sqlite3
import cv2
import numpy as np
import pycolmap as pc


def enhance(im):
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB)
    lab[:,:,0]=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(lab[:,:,0])
    return cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)


def run(source, output, variant='raw'):
    source,output=Path(source),Path(output); output.mkdir(parents=True,exist_ok=True)
    paths=sorted(source.glob('*.jpg'))
    if len(paths)<3: raise ValueError('At least three JPEG images required')
    manifest=[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
    cfg={'variant':variant,'inputs':manifest,'pycolmap':pc.__version__,'max_features':8192,'camera_model':'SIMPLE_RADIAL','seed':42}
    fingerprint=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    if (output/'metrics.json').exists():
        old=json.loads((output/'metrics.json').read_text())
        if old.get('fingerprint')==fingerprint:return old
        raise RuntimeError('Output configuration differs; choose a new output folder.')
    if (output/'database.db').exists():raise RuntimeError('Incomplete run exists; choose a new output folder.')
    images=source
    if variant=='clahe':
        images=output/'images';images.mkdir(exist_ok=True)
        for p in paths:
            im=cv2.imread(str(p));cv2.imwrite(str(images/(p.stem+'.png')),enhance(im))
    start=time.perf_counter(); db=output/'database.db'
    pc.extract_features(db,images,camera_mode=pc.CameraMode.SINGLE,
        reader_options={'camera_model':'SIMPLE_RADIAL'},
        extraction_options={'num_threads':4,'max_image_size':1280,'sift':{'max_num_features':8192}},device=pc.Device.cpu)
    pc.match_exhaustive(db,matching_options={'num_threads':4},device=pc.Device.cpu)
    options=pc.IncrementalPipelineOptions({'num_threads':4,'random_seed':42,'min_model_size':3,'max_num_models':5,
      'mapper':{'init_min_tri_angle':8.0,'filter_max_reproj_error':3.0},'ba_global_max_num_iterations':50})
    models=pc.incremental_mapping(db,images,output/'models',options=options)
    metrics={'scene':source.parent.name,'variant':variant,'input_images':len(paths),'fingerprint':fingerprint,'config':cfg,
      'seconds':time.perf_counter()-start,'models':len(models),'scale':'arbitrary','status':'failed' if not models else 'reconstructed'}
    if not models:
        (output/'metrics.json').write_text(json.dumps(metrics,indent=2));return metrics
    rec=max(models.values(),key=lambda r:(r.num_reg_images(),r.num_points3D()))
    rec.write(output/'selected') if (output/'selected').exists() else ((output/'selected').mkdir(),rec.write(output/'selected'))
    points=list(rec.points3D.values()); xyz=np.array([p.xyz for p in points]);colors=np.array([p.color for p in points]);err=np.array([p.error for p in points]);track=np.array([p.track.length() for p in points])
    # Quality filtering is explicit and does not change the saved COLMAP model.
    keep=np.isfinite(xyz).all(axis=1)&(err<=2)&(track>=3)
    cameras=[{'name':im.name,'center':im.projection_center().tolist()} for im in rec.images.values() if im.has_pose]
    np.savez_compressed(output/'cloud.npz',xyz=xyz[keep],rgb=colors[keep],error=err[keep],track=track[keep])
    with (output/'cloud.ply').open('w') as f:
        f.write('ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'%keep.sum())
        for p,c in zip(xyz[keep],colors[keep]):f.write(' '.join(map(str,[*p,*c]))+'\n')
    with sqlite3.connect(db) as con:
        verified=con.execute('SELECT COUNT(*) FROM two_view_geometries WHERE rows>=15').fetchone()[0]
    metrics.update(registered_images=rec.num_reg_images(),points_raw=len(points),points_filtered=int(keep.sum()),
      mean_reprojection_px=float(rec.compute_mean_reprojection_error()),median_point_error_px=float(np.median(err)),
      p95_point_error_px=float(np.percentile(err,95)),median_track_length=float(np.median(track)),verified_pairs=verified,
      cameras=cameras,estimated_intrinsics=[{'model':c.model_name,'params':c.params.tolist()} for c in rec.cameras.values()])
    (output/'metrics.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps({k:v for k,v in metrics.items() if k not in ['config','cameras']},indent=2),flush=True)
    return metrics

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,default=Path('results'));ap.add_argument('--scenes',nargs='+',default=['Cormoran','Isro','Kwaj','Tokai']);ap.add_argument('--variants',nargs='+',choices=['raw','clahe'],default=['raw','clahe']);a=ap.parse_args()
    for s in a.scenes:
        for v in a.variants:run(a.data/s/'input',a.out/s/v,v)
