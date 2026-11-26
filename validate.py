"""Meaningful geometry and saved-run integrity checks, without ground-truth claims."""
from pathlib import Path
import json
import cv2,numpy as np,pycolmap as pc

def check_rectification():
    K=np.array([[500.,0,320],[0,500,240],[0,0,1]])
    points=np.array([[.2,.1,3],[-.3,.2,5],[.4,-.3,4.]])
    for t in [np.array([-.2,0,0]),np.array([0,-.2,0]),np.array([.2,0,0]),np.array([0,.2,0])]:
        R1,R2,P1,P2,Q,*_=cv2.stereoRectify(K,np.zeros(5),K,np.zeros(5),(640,480),np.eye(3),t.reshape(3,1))
        a=points@R1.T; b=(points+t)@R2.T
        pa=a@P1[:,:3].T;pa=pa[:,:2]/pa[:,2:3]
        pb=b@P2[:,:3].T;pb=pb[:,:2]/pb[:,2:3]
        axis=int(abs(P2[1,3])>abs(P2[0,3]));d=pa[:,axis]-pb[:,axis]
        h=np.c_[pa,d,np.ones(len(d))]@Q.T;recovered=h[:,:3]/h[:,3:4]
        np.testing.assert_allclose(recovered,a,atol=1e-9)
    # Camera-to-world inverse used by densification, including nonzero rotation.
    R,_=cv2.Rodrigues(np.array([.2,-.3,.1]));t=np.array([.4,.5,.2]);r,_=cv2.Rodrigues(np.array([.1,.2,0.]));rect=(points@R.T+t)@r.T
    np.testing.assert_allclose((rect@r-t)@R,points,atol=1e-10)

def audit(root):
    checks=[]
    for file in sorted(Path(root).glob('*/*/metrics.json')):
        m=json.loads(file.read_text());p=file.parent
        if m['status']!='reconstructed':checks.append({'run':str(p),'status':'failed reconstruction'});continue
        rec=pc.Reconstruction(p/'selected');cloud=np.load(p/'cloud.npz')
        assert rec.num_reg_images()==m['registered_images']
        assert len(cloud['xyz'])==m['points_filtered']
        assert np.isfinite(cloud['xyz']).all() and (cloud['error']<=2).all() and (cloud['track']>=3).all()
        residuals=[];negative=0
        for im in rec.images.values():
            if not im.has_pose:continue
            cam=rec.cameras[im.camera_id];pose=im.cam_from_world()
            for obs in im.points2D:
                if not obs.has_point3D():continue
                point=pose*rec.points3D[obs.point3D_id].xyz
                negative+=point[2]<=0
                predicted=cam.img_from_cam(point)
                residuals.append(float(np.linalg.norm(predicted-obs.xy)))
        assert negative==0
        assert np.isfinite(residuals).all()
        names={im.name.rsplit('.',1)[0] for im in rec.images.values() if im.has_pose}
        missing=[q['name'] for q in m['config']['inputs'] if q['name'].rsplit('.',1)[0] not in names]
        checks.append({'run':m['scene']+'/'+m['variant'],'observations_checked':len(residuals),'observation_rmse_px':float(np.sqrt(np.mean(np.square(residuals)))),'negative_depth_observations':int(negative),'unregistered':missing,'status':'passed'})
    return checks

if __name__=='__main__':
    check_rectification();root=Path(__file__).parent;result={'synthetic_geometry_tests':'passed: signed horizontal and vertical stereo, inverse pose transform','runs':audit(root/'results')};(root/'results'/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
