# AquaRecon — experiment report

## Scope

80 real underwater photographs, four scenes, two input variants. This is a sparse multi-view geometry benchmark with an experimental dense-stereo extension. No metric reference was supplied.

## Measured sparse results

|Scene|Input|Registered views|Filtered 3D points|Mean reprojection error (px)|Seconds|
|---|---|---:|---:|---:|---:|
|Cormoran|clahe|20/20|7,321|0.917|30.1|
|Cormoran|raw|20/20|7,958|0.888|31.2|
|Isro|clahe|20/20|7,344|0.925|23.7|
|Isro|raw|20/20|6,375|0.897|18.2|
|Kwaj|clahe|20/20|15,904|0.695|38.8|
|Kwaj|raw|20/20|16,045|0.674|36.9|
|Tokai|clahe|19/20|8,243|0.896|29.5|
|Tokai|raw|19/20|7,941|0.912|25.6|

## Interpretation

All cameras registered in Cormoran, Isro and Kwaj. Tokai registered 19 of 20 in both variants. The missing image is recorded in validation.json. Enhancement is scene-dependent: it increased retained points for Isro and Tokai, but decreased them for Cormoran and Kwaj. It reduced mean reprojection error only for Tokai. These are separate fits to different feature observations, so a lower error alone does not establish superior geometric accuracy.

The strongest raw-image run by retained point count is Kwaj, with 16,045 filtered sparse points and 0.674 px mean reprojection error. These points have at least three observations and at most 2 px mean point error.

## Dense stereo

|Scene|Pairwise dense points before display-only outlier filtering|
|---|---:|
|Cormoran|87,389|
|Isro|46,313|
|Kwaj|177,191|
|Tokai|143,422|

Dense point counts include overlap between pairs, and are not counts of independent surface elements. Some pairs return very few or zero valid points. Dense surfaces have holes and outliers. Inspect these alongside the original images, rather than using them as engineering measurements.

## Verification

Synthetic checks cover signed horizontal/vertical rectification and camera-to-world inverse transforms. All saved sparse models were independently reprojected through their estimated camera models, with finite coordinates and no behind-camera observations. Exact observation counts and observation-weighted RMSE are in validation.json. That RMSE differs from the mean per-point error shown in the main table.

## What is not established

No held-out evaluation, ground-truth surface error, metric scale, calibrated uncertainty, explicit refractive model, automated damage detection or state-of-the-art comparison was performed. The delivered work is a reproducible inspection research prototype.

## Attribution

Submerged3D, Jiang and Anantrasirichai (University of Bristol), 2025. DOI: 10.5281/zenodo.15482420. Geometry engine: COLMAP/PyCOLMAP. Dense matcher: OpenCV SGBM.
