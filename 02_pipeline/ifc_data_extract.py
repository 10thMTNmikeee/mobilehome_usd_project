import os
import re
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
from pxr import Usd, UsdGeom, UsdShade, Gf, Sdf
from pathlib import Path

# get ifc file path
FILE_IFC = Path(__file__).resolve().parent.parent / '01_source' / 'structure_mobilehome.ifc'
# get usd file path
FILE_USD = Path(__file__).resolve().parent.parent / '01_source' / 'structure_mobilehome_test.usda'

def clean_material_name(mat_name):
    pattern = r"[\s,\-()]"
    cleaned_name = re.sub(pattern, "_", mat_name)
    return cleaned_name

def create_usd_material(stage, mat_name, rgb_color):
    path = f"/root/Materials/{mat_name}"
    material = UsdShade.Material.Define(stage, path)
    pbr_shader = UsdShade.Shader.Define(stage, f"{path}/PBRShader")

    pbr_shader.CreateIdAttr("UsdPreviewSurface")
    pbr_shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb_color))
    pbr_shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    pbr_shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

    material.CreateSurfaceOutput().ConnectToSource(pbr_shader.ConnectableAPI(), "surface")
    return material

def convert_ifc_to_usd(file_ifc, file_usd):

    stage = Usd.Stage.CreateNew(str(FILE_USD))
    UsdGeom.SetStageMetersPerUnit(stage, 0.0254)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    root_xform = UsdGeom.Xform.Define(stage, "/root")
    stage.SetDefaultPrim(root_xform.GetPrim())

    ifc_file = ifcopenshell.open(str(FILE_IFC))
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    settings.set(settings.WELD_VERTICES, False)
    
    
    

    material_cache = {}

    iterator = ifcopenshell.geom.iterator(settings, ifc_file)

    if iterator.initialize():
        while True:
            shape = iterator.get()
            element = ifc_file.by_id(shape.id)


            verts = shape.geometry.verts
            faces = shape.geometry.faces
            normals = shape.geometry.normals

            element_type = element.is_a()

            is_opening = element.is_a("IfcOpeningElement")
            if is_opening:
                if not iterator.next():
                    break
                continue


            if verts and faces:
                usd_points = [Gf.Vec3f(verts[i], verts[i+1], verts[i+2]) for i in range(0, len(verts), 3)]
                usd_face_indices = list(faces)
                usd_face_counts = [3] * (len(faces) // 3)

                usd_normals = [Gf.Vec3f(normals[i], normals[i+1], normals[i+2]) for i in range(0, len(normals), 3)]

                category_path = f"/root/{element_type}"
                mesh_path = f"{category_path}/{element_type}_{element.id()}"

                usd_mesh = UsdGeom.Mesh.Define(stage, mesh_path)
                usd_mesh.CreatePointsAttr(usd_points)
                usd_mesh.CreateFaceVertexIndicesAttr(usd_face_indices)
                usd_mesh.CreateFaceVertexCountsAttr(usd_face_counts)
                usd_mesh.CreateNormalsAttr(usd_normals)
                usd_mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
                

                mat_name = "UsdPreviewSurface"
                rgb_color = (0.5, 0.5, 0.5)

                # try to get rgb values
                try:
                    rgb_array = ifcopenshell.util.shape.get_material_colors(shape.geometry)
                    first_color = rgb_array[0]
                    rgb_color = (float(first_color[0]), float(first_color[1]), float(first_color[2]))
                except Exception as e:
                    print('error getting material color, using default color')
                
                # try to get the material name
                try:
                    # handle direct material assignmnet
                    ifc_material = ifcopenshell.util.element.get_material(element)
                    if ifc_material:
                        mat_name = ifc_material.Name
                        mat_name = clean_material_name(mat_name)

                
                    elif ifc_material.is_a("IfcMaterialLayerSetUsage"):

                        layer_set = ifc_material.ForLayerSet
                        if layer_set:
                            first_layer = layer_set.MaterialLayers[0]
                            if first_layer:
                                mat_name = first_layer.Material.Name
                                mat_name = clean_material_name(mat_name)
                
                except Exception as e:
                    pass
                            
                
                if mat_name not in material_cache:
                    material_cache[mat_name] = create_usd_material(stage, mat_name, rgb_color)
                

                UsdShade.MaterialBindingAPI(usd_mesh).Bind(material_cache[mat_name])

            if not iterator.next():
                break


    stage.Save()
    del stage

convert_ifc_to_usd(FILE_IFC, FILE_USD)
