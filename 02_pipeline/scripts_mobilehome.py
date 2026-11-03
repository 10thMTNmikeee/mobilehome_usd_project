import os
from pxr import Usd, UsdGeom, UsdPhysics
from pathlib import Path

# get the path to the main mobilehome project directory, two folders up from this script
SOURCE_DIR = str(Path(__file__).resolve().parent.parent)
print(f"Your Source directory is: {SOURCE_DIR}")
# get the path to the structure usda file
STRUCTURE_USDA_PATH = str(Path(SOURCE_DIR) / '01_source' / 'structure_mobilehome.usda')
print(f"Your Structure USD file path is: {STRUCTURE_USDA_PATH}")
# get the path to the federated usda file
FEDERATED_STAGE_USDA_PATH = str(Path(SOURCE_DIR) / '02_pipeline' / 'federated_mobilehome.usda')
print(f"Your Federated stage USD file path is: {FEDERATED_STAGE_USDA_PATH}")

if os.path.exists(FEDERATED_STAGE_USDA_PATH):
    try:
        os.remove(FEDERATED_STAGE_USDA_PATH)
    except PermissionError:
        print(f"Permission denied: Unable to delete")
        
# open the federated stage and set the upaxis to Z for unreal, convert units, add frame range
stage = Usd.Stage.CreateNew(FEDERATED_STAGE_USDA_PATH)
stage.SetMetadata("upAxis", "Z")
stage.SetMetadata("metersPerUnit", 0.0254)
stage.SetStartTimeCode(1.0)
stage.SetEndTimeCode(1000.0)
stage.SetFramesPerSecond(24.0)
stage.SetTimeCodesPerSecond(24.0)

# reference the base usda file to the federated stage
mobilehome_root = stage.DefinePrim("/root")
mobilehome_root.GetReferences().AddReference(STRUCTURE_USDA_PATH)

# create a single transform for the left half/patio so it translates as a single object
left_half_xform = UsdGeom.Xform.Define(stage, "/root/LeftHalfGroup")
left_patio_xform = UsdGeom.Xform.Define(stage, "/root/LeftPatioGroup")
editor = Usd.NamespaceEditor(stage)

# create the transform ops for the left half and patio transforms
patio_XformOp = left_patio_xform.AddTranslateYOp()
half_XformOp = left_half_xform.AddTranslateXOp()

# string variables for the userProperties:Mark attribute values
TARGET_HALF = "Left_Half"
TARGET_PATIO = "Left_Patio"

# get lists ready for found meshes with the Mark attr
patio_meshes = []
half_meshes = []

# apply collision and load the lists
for prim in stage.Traverse():

    # first apply percise collision to all meshes in the scene
    if prim.IsA(UsdGeom.Mesh):
        
        prim.SetCustomDataByKey("URP:CollisionTraceFlag", 3)
        
        if not prim.HasAPI(UsdPhysics.CollisionAPI):
            UsdPhysics.CollisionAPI.Apply(prim)
        if not prim.HasAPI(UsdPhysics.MeshCollisionAPI):
            mesh_collision =UsdPhysics.MeshCollisionAPI.Apply(prim)
            mesh_collision.CreateApproximationAttr("mesh")

    
    if prim.HasAttribute("userProperties:Mark"):
        if prim.GetAttribute("userProperties:Mark").Get() == TARGET_HALF:
            half_meshes.append(prim)
        else:
            if prim.GetAttribute("userProperties:Mark").Get() == TARGET_PATIO:
                patio_meshes.append(prim)


# load patio meshes into group and animate it
if patio_meshes:      
    
    start_move = 96.0
    end_move = 168.0
    
    print("Patio meshes found, grouping and applying animation to the left patio transform.")
    for prim in patio_meshes:
        editor.ReparentPrim(prim, left_patio_xform.GetPrim())
        editor.ApplyEdits()

    patio_XformOp.Set(time=1, value=0)
    patio_XformOp.Set(time=start_move, value=0)
    patio_XformOp.Set(time=end_move, value=12)
   

# load the left half meshes into the left half transform and animate it
if half_meshes:

    start_move = 216
    end_move = 312
    
    print("Half meshes found, grouping and applying animation to the left half transform.")
    for prim in half_meshes:
        editor.ReparentPrim(prim, left_half_xform.GetPrim())
        editor.ApplyEdits()
    
    half_XformOp.Set(time=1, value=0)
    half_XformOp.Set(time=start_move, value=0)
    half_XformOp.Set(time=end_move, value=-6)
        


stage.Save()

del stage