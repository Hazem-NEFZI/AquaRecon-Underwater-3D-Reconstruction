"""Experimental CPU stereo densification using estimated SfM cameras.
Rejects left/right inconsistencies, weak texture, invalid remaps and negative depth.
Output is a pairwise point cloud, not a certified mesh or a fused MVS surface.
"""
from pathlib import Path
import argparse,json
import cv2,numpy as np,pycolmap as pc


def dense(model_dir, originals, max_pairs=8):
    model_dir,originals=Path(model_dir),Path(originals)
    rec=pc.Reconstruction(model_dir/'selected')
    ims=sorted([i for i in rec.images.values() if i.has_pose],key=lambda i:i.name)
    allxyz=[];allrgb=[];reports=[]
    # Adjacent captured images reduce viewpoint differences; names encode capture order.
    candidates=list(zip(ims[:-1],ims[1:]))
    indices=np.linspace(0,len(candidates)-1,min(max_pairs,len(candidates))).astype(int)
    for pair_index in indices:
        a,b=candidates[pair_index]; ca,cb=rec.cameras[a.camera_id],rec.cameras[b.camera_id]
        def calib(c):
            if c.model_name!='SIMPLE_RADIAL':raise ValueError('Densifier currently supports SIMPLE_RADIAL only')
            f,cx,cy,k=c.params
            return np.array([[f,0,cx],[0,f,cy],[0,0,1.]],float),np.array([k,0,0,0,0.])
        K1,D1=calib(ca);K2,D2=calib(cb)
        A=a.cam_from_world();B=b.cam_from_world();Ra=A.rotation.matrix();Rb=B.rotation.matrix();ta=A.translation;tb=B.translation
        R=Rb@Ra.T;t=tb-R@ta;size=(ca.width,ca.height)
        r1,r2,p1,p2,Q,roi1,roi2=cv2.stereoRectify(K1,D1,K2,D2,size,R,t.reshape(3,1),flags=cv2.CALIB_ZERO_DISPARITY,alpha=0)
        vertical=abs(p2[1,3])>abs(p2[0,3])
        def load(im):
            path=originals/(Path(im.name).stem+'.jpg');img=cv2.imread(str(path))
            if img is None:raise FileNotFoundError(path)
            return img
        x1,y1=cv2.initUndistortRectifyMap(K1,D1,r1,p1,size,cv2.CV_32FC1)
        x2,y2=cv2.initUndistortRectifyMap(K2,D2,r2,p2,size,cv2.CV_32FC1)
        im1=cv2.remap(load(a),x1,y1,cv2.INTER_LINEAR);im2=cv2.remap(load(b),x2,y2,cv2.INTER_LINEAR)
        if vertical:
            im1=im1.transpose(1,0,2);im2=im2.transpose(1,0,2)
            x1=x1.T;y1=y1.T;x2=x2.T;y2=y2.T
        width,height=im1.shape[1],im1.shape[0]
        gray1=cv2.cvtColor(im1,cv2.COLOR_BGR2GRAY);gray2=cv2.cvtColor(im2,cv2.COLOR_BGR2GRAY)
        cl=cv2.createCLAHE(2.0,(8,8));g1=cl.apply(gray1);g2=cl.apply(gray2)
        nd=256; md=0 if p2[1 if vertical else 0,3]<0 else -nd
        def matcher(min_d):return cv2.StereoSGBM_create(minDisparity=min_d,numDisparities=nd,blockSize=5,P1=8*25,P2=32*25,disp12MaxDiff=1,uniquenessRatio=12,speckleWindowSize=100,speckleRange=2,mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
        dl=matcher(md).compute(g1,g2).astype(float)/16
        mr=-md-nd+1;dr=matcher(mr).compute(g2,g1).astype(float)/16
        yy,xx=np.indices(dl.shape);xr=np.rint(xx-dl).astype(int);inside=(xr>=0)&(xr<width);xc=np.clip(xr,0,width-1)
        valid1=(x1>=1)&(x1<size[0]-2)&(y1>=1)&(y1<size[1]-2)
        valid2=(x2>=1)&(x2<size[0]-2)&(y2>=1)&(y2<size[1]-2)
        texture=cv2.GaussianBlur(gray1.astype(np.float32)**2,(9,9),0)-cv2.GaussianBlur(gray1.astype(np.float32),(9,9),0)**2
        mask=(dl>md)&(dl<md+nd-1)&inside&(dr[yy,xc]>mr)&(np.abs(dl+dr[yy,xc])<1)&valid1&valid2[yy,xc]&(texture>16)
        hom=np.stack([yy if vertical else xx,xx if vertical else yy,dl,np.ones_like(dl)],axis=-1)@Q.T
        with np.errstate(divide='ignore',invalid='ignore'):
            pts=hom[:,:,:3]/hom[:,:,3:4]
        mask&=np.isfinite(pts).all(2)&(pts[:,:,2]>0)
        # Limit depths against the sparse reconstruction's visible depth envelope.
        sparse=np.array([p.xyz for p in rec.points3D.values()]);z=(sparse@Ra.T+ta)@r1.T
        positive=z[:,2][z[:,2]>0]
        low,high=np.percentile(positive,[1,99]);mask&=(pts[:,:,2]>low*.5)&(pts[:,:,2]<high*1.5)
        # Pixel-stride subsampling limits output size without filling gaps.
        mask&=(xx%3==0)&(yy%3==0)
        world=(pts[mask]@r1-ta)@Ra
        colors=im1[mask][:,::-1];allxyz.append(world);allrgb.append(colors)
        reports.append({'pair':int(pair_index),'images':[a.name,b.name],'points':len(world),'status':'ok'})
        if len(reports)==1:
            cv2.imwrite(str(model_dir/'rectified.jpg'),np.hstack([im1,im2]))
            normalized=np.clip((np.abs(dl)/nd)*255,0,255).astype('uint8');vis=cv2.applyColorMap(normalized,cv2.COLORMAP_TURBO)
            # Full-resolution validity for visualization uses same subsampling: retain explicit holes.
            vis[~mask]=[15,23,31];cv2.imwrite(str(model_dir/'disparity.jpg'),vis)
        print('dense',model_dir.parent.name,pair_index,len(world),flush=True)
    xyz=np.concatenate(allxyz) if allxyz else np.empty((0,3));rgb=np.concatenate(allrgb) if allrgb else np.empty((0,3),dtype='uint8')
    np.savez_compressed(model_dir/'dense.npz',xyz=xyz,rgb=rgb)
    with (model_dir/'dense.ply').open('w') as f:
        f.write('ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'%len(xyz))
        for p,c in zip(xyz,rgb):f.write(' '.join(map(str,[*p,*c]))+'\n')
    (model_dir/'dense_metrics.json').write_text(json.dumps({'points':len(xyz),'pairs':reports,'note':'Pairwise stereo, arbitrary scale, estimated pinhole calibration; not multiview-fused or ground-truth validated.'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--images',type=Path,required=True);a=p.parse_args();dense(a.model,a.images)
