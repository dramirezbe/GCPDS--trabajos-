import SimpleITK as sitk
# Descarga bajo demanda (usa HTTP) y cache local
from downloaddata import fetch_data as fdata  # parte de SimpleITK-Notebooks

# Carga un tiempo respiratorio concreto
fixed = sitk.ReadImage(fdata("POPI/meta/00-P.mhd"), sitk.sitkFloat32)
moving = sitk.ReadImage(fdata("POPI/meta/70-P.mhd"), sitk.sitkFloat32)

# Carga también las máscaras si quieres segmentar
mask = sitk.ReadImage(fdata("POPI/masks/00-air-body-lungs.mhd"))
