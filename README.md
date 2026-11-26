# AquaRecon
## Underwater multi-view reconstruction and inspection research

**Hazem Nefzi — IMR, SIGMA Clermont**

A working computer-vision portfolio project on **80 real shipwreck photographs**, comparing raw inputs with luminance-only contrast enhancement. Built on established COLMAP geometry, with a custom reproducible experiment pipeline, quality filtering, CPU stereo densification and an offline inspection interface.

### Open the result first
1. Extract this ZIP fully.
2. Double-click **AquaRecon.html**. Use Chrome, Edge or Firefox with WebGL enabled.
3. Select a wreck, rotate the reconstruction and change the geometry to **Experimental dense stereo**. Dense results are provided for the raw-image runs only.
4. Choose reprojection-error colouring for sparse points. Toggle camera positions or select two points to measure a separation in arbitrary reconstruction units.

No Python installation, server or internet connection is required to inspect the saved demo. The HTML embeds its data and Plotly. Different reconstructions are independently oriented/scaled; this is not a registered before/after change-detection tool.

### What was actually implemented
- Audited all 80 input images and recorded SHA-256 identifiers.
- Reconstructed each scene twice: original RGB vs CLAHE on luminance (clip limit 2, 8×8 tiles).
- Shared SIMPLE_RADIAL camera per scene, initialized by COLMAP and refined with bundle adjustment. No calibration was provided in the ZIP.
- SIFT with RootSIFT normalization, exhaustive feature matching, robust geometric verification, incremental SfM and bundle adjustment through PyCOLMAP.
- Exported points with ≥3 observations and mean point reprojection error ≤2 pixels.
- Added pairwise SGBM stereo using estimated poses, horizontal or vertical rectification, left-right consistency, texture and valid-image masks, positive depth and a sparse-depth envelope.
- Produced interactive original/enhanced image comparisons, camera poses, error colouring, benchmark CSV, COLMAP models and PLY clouds.

**Contribution:** integration, experiment design, quality controls, evaluation and inspection interface. SIFT, COLMAP, SGBM and CLAHE are established methods, not new algorithms invented in this project.

### Reproduce on Windows
Use Python 3.12 (64-bit). In PowerShell, open this extracted project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python reconstruct.py --data "C:\path\to\Submerged3D" --out rerun_results
```

The data path must contain `Cormoran/input`, `Isro/input`, `Kwaj/input`, and `Tokai/input`. Use your original Submerged3D ZIP; full source photos are not duplicated in this package.

For one scene:

```powershell
.\.venv\Scripts\python reconstruct.py --data "C:\path\to\Submerged3D" --out rerun_results --scenes Kwaj --variants raw
.\.venv\Scripts\python densify.py --model rerun_results/Kwaj/raw --images "C:\path\to\Submerged3D\Kwaj\input"
```

The saved results folder excludes the large matching databases and enhanced source images. Use a new output directory to reproduce an experiment. Completed runs with the same input fingerprint are reused; incomplete runs are refused rather than silently mixed with new data. Four CPU threads are requested. The initial sparse experiments used OpenCV 5.1.0 for CLAHE, while dense stereo and the packaged dependency pin use OpenCV 4.11.0. Exact numerical reproduction across versions/platforms is not guaranteed. Runtime varies by hardware; no CUDA GPU is required. Tested here on Linux, Python 3.12; the PowerShell instructions have not been executed on Windows.

To build your own viewer, put completed experiment folders beneath a project directory's `results/`, copy `viewer_template.html` there, then run:

```powershell
.\.venv\Scripts\python build_demo.py --root . --data "C:\path\to\Submerged3D"
.\.venv\Scripts\python validate.py
```

### Read the results correctly
`results/benchmark.csv` records all eight runs. Reprojection error measures **internal agreement with the same input observations**, not held-out prediction or physical accuracy. Registration rate reports completeness of estimated camera poses, not complete surface coverage. The viewer displays at most 45,000 sampled points per cloud to keep navigation responsive; complete compressed clouds remain available. Run `python export_clouds.py` to export the bundled dense arrays to PLY for CloudCompare or MeshLab. Sparse PLY files are included directly.

The dense PLY files contain pairwise estimates before display-only statistical outlier filtering. The viewer removes points whose mean distance to eight neighbours exceeds the global mean plus two standard deviations. It retains holes rather than inventing surface geometry. The sparse-depth envelope rejects implausibly distant/near stereo points but is not a proof of correctness.

### Industrial relevance and honest limitations
This project targets the **visual survey stage of underwater inspection**: recover visible structure, review photographic evidence and identify missing observations. It is not certified for defect sizing, crack/corrosion detection, structural assessment or autonomous navigation.

- No metric scale, supplied underwater calibration, ground-truth geometry, IMU, depth sensor or surveyed targets are included.
- Refraction at the housing/water interface is not explicitly modelled. A fitted radial camera is an approximation.
- Untextured water, occlusions, illumination changes and sparse viewpoints cause holes and outliers.
- Pairwise dense clouds are not multiview-fused, watertight meshes or Gaussian splats.
- Shared intrinsics assume one fixed camera/lens setting per scene; this assumption needs independent confirmation for industrial use.
- No cross-dataset generalization or state-of-the-art superiority is claimed.

**Next validation milestone:** underwater calibration plus known-length targets or a reference scan, then evaluate metric error and repeatability. Add multiview depth consistency and calibrated uncertainty before defect measurements. An image-enhancement step is retained only when supported by measurements; it is not assumed to improve every scene.

### Data and software attribution
Submerged3D: Zhuodong Jiang and Nantheera Anantrasirichai, University of Bristol (2025), https://doi.org/10.5281/zenodo.15482420. Four scenes with 20 RGB 720p shipwreck images each. Related research: *RUSplatting: Robust 3D Gaussian Splatting for Sparse-View Underwater Scene Reconstruction*, BMVC 2025, https://theflash987.github.io/RUSplatting.page/ . This project does **not** implement RUSplatting.

The archive includes no license file. Check the dataset's current terms before publicly redistributing photographs or derived assets. This private package includes small representative previews and derived results for your supplied data. Dataset ownership remains with its creators.

- COLMAP/PyCOLMAP: https://colmap.github.io/pycolmap/index.html
- OpenCV calibration and stereo: https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
- Plotly: https://plotly.com/python/

### CV wording after you have run and understood the project
**AquaRecon — Reconstruction 3D sous-marine (projet personnel)**  
Développement d'un pipeline Python de reconstruction multi-vues sur 80 images réelles d'épaves : estimation des poses, ajustement de faisceaux, filtrage géométrique et visualisation 3D interactive. Comparaison des images brutes et rehaussées sur quatre scènes, avec analyse des erreurs de reprojection et des limites de reconstruction.

**Technologies:** Python, OpenCV, COLMAP/PyCOLMAP, NumPy, SciPy, Plotly, géométrie multi-vues.

### Validation scope for the interface
Viewer scene selection, dense-to-sparse fallback, error-colour configuration, camera toggle, reset and distance calculation passed a JavaScript logic test. The local headless Chromium process crashed while loading the page, so end-to-end WebGL rendering could not be verified here. The static reconstruction preview was generated directly from the computed point clouds and visually inspected. Please open the HTML in a current desktop browser with WebGL enabled.
