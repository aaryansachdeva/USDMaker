#USD_Maker 1.01

import math
import xml.etree.ElementTree as ET
import os
import hou
from mpc.tvcFtrack.apiBridge.common import Api3Helper
import toolutils
import re

node = hou.pwd()

#xml = "ADD_PATH_HERE"
xml = node.parm("xmlPath").eval()


def determine_type(file_name):

    # Keywords and their clumped types
    keywords = {
        "COL": "DIF",
        "col": "DIF",
        "DIF": "DIF",
        "dif": "DIF",
        "Albedo": "DIF",
        "albedo": "DIF",
        "AO": "AO",
        "ao": "AO",
        "OCC": "AO",
        "occ": "AO",
        "Occ": "AO",
        "RGH": "RGH",
        "rgh": "RGH",
        "Roughness": "RGH",
        "roughness": "RGH",
        "Translucency": "Translucency",
        "translucency": "Translucency",
        "Normal": "NRM",
        "normal": "NRM",
        "NRM": "NRM",
        "nrm": "NRM",
        "SSS": "SSS",
        "sss": "SSS",
        "OPC": "OPC",
        "opc": "OPC",
        "Opacity": "OPC",
        "opacity": "OPC"
    }
    
    for keyword, texture_type in keywords.items():
        if keyword in file_name:
            return texture_type
    return "Unknown"
    
def makeTextures(imageBlock, shaderNode, standardSurface):
    name = image_block.get('name', 'No name found')
    
    # Split the name by '/'
    parts = name.split('/')
    
    # Get the last part of the split
    if parts:
        name = parts[-1]
    
    filename = image_block.get('filename', 'No filename found')
    if filename.startswith('"') and filename.endswith('"'):
        filename = filename[1:-1]
    #print(name)
    tex = shaderNode.createNode("usduvtexture::2.0", name)
    tex.parm("file").set(filename)
    
    filetype = determine_type(name)
    #print(filetype)
    
    if filetype == "DIF":
        standardSurface.setInput(0, tex, 4)
        
    if filetype == "RGH":
        standardSurface.setInput(5, tex, 0)
        
    if filetype == "NRM":
        #normalNode = shaderNode.createNode("mtlxnormalmap", "NormalMap")
        #normalNode.setInput(0, tex, 0)
        standardSurface.setInput(10, tex, 4)
    
    if filetype == "OPC":
        standardSurface.setInput(8, tex, 0)
        
    #if filetype == "SSS":
        #standardSurface.setInput(18, tex, 4)
    
    

def read_ass_file(filename):
    with open(filename, 'r') as file:
        return file.read()
        
        
def parse_ass_file(content):
    blocks = {}
    block_pattern = re.compile(r'(\w+)\s*\{\s*([\s\S]*?)\s*\}', re.MULTILINE)
    
    for match in block_pattern.finditer(content):
        block_type = match.group(1)
        block_content = match.group(2)
        
        if block_type not in blocks:
            blocks[block_type] = []
        
        attributes = {}
        for line in block_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key_value = line.split(None, 1)  # Corrected here
            if len(key_value) == 2:
                key, value = key_value
                attributes[key] = value
        
        blocks[block_type].append(attributes)
    
    return blocks

def extract_version_number(name):
    # Use a regular expression to find the version pattern 'v<digit+>'
    match = re.search(r'v(\d+)', name)
    if match:
        return match.group(1)  # Return only the digit part
    else:
        return None

def getInfo(id):
    api = Api3Helper()
    shader_id = id
    
    comp = api.getEntFromId('Component', shader_id)
    if comp:
        asset_id = comp['version_id']
        ver = api.getVersionFromId(asset_id)
    else:
        asset_id = shader_id
        ver = api.getVersionFromId(shader_id)
        
    ver = api.getVersionFromId(asset_id)
    #link = ver['link']
    
    return ver

def makeGrabAss(subnetNode, name, assdata):

    link = assdata['link']
    shader_name = link[3]['name'].split()[0]

    grabass = subnetNode.createNode('sachdevaa::dev::grabass::1.0', 'grabass_' + name)
    grabass.parm("job_name").set(link[0]['name'])
    grabass.parm("scene_name").set(link[1]['name'])
    grabass.parm("shot_name").set(link[2]['name'])
    grabass.parm("asset_type_name").set('Shaders')
    grabass.parm("asset_name").set(shader_name)
    
    version = extract_version_number(link[3]['name']);
    
    grabass.parm("version_name").set(version)
    grabass.parm("component_name").set("ass")
    
    return grabass

def makeRotation(rotx, roty, rotz):

    def radians(degrees):
        return degrees * (math.pi / 180.0)
        
    rotx_rad = radians(rotx)
    roty_rad = radians(roty)
    rotz_rad = radians(rotz)
    
    #Create rotation matrices for each axis
    rotx_mat = hou.hmath.buildRotateAboutAxis(hou.Vector3(1, 0, 0), rotx_rad)
    roty_mat = hou.hmath.buildRotateAboutAxis(hou.Vector3(0, 1, 0), roty_rad)
    rotz_mat = hou.hmath.buildRotateAboutAxis(hou.Vector3(0, 0, 1), rotz_rad)
    
    #Combine rotations 
    rot_matrix = rotz_mat * roty_mat * rotx_mat
    
    # Extract the quaternion from the combined rotation matrix
    q = hou.Quaternion(rot_matrix)
    
    return q
    



geo = node.geometry()



basePath = node.parent().path()
baseNode = hou.node(basePath)

#Add a Subnet node for Assets
subnet_name = "ASSETS"
assetSubnet = baseNode.node(subnet_name)

if not assetSubnet:
    assetSubnet = baseNode.createNode("subnet", subnet_name)
    
#Ensure the subnet node is empty to avoid conflicts
#for child in assetSubnet.children():
    #child.destroy()
    
    
#Add a Lopnet node
lopnet_name = "USD"
lopnet = baseNode.node(lopnet_name)

if not lopnet:
    lopnet = baseNode.createNode("lopnet", lopnet_name)
    
#Ensure the lopnet node is empty to avoid conflicts
#for child in lopnet.children():
    #child.destroy()
    
#Create additional nodes inside Lopnet
mergeLopNode = lopnet.createNode("merge", "mergeInstances")
mergeLopNode.parm("mergestyle").set("flattened")

nullLopNode = lopnet.createNode("null", "OUT")
nullLopNode.setInput(0, mergeLopNode)

lopRenderNode = lopnet.createNode("usd_rop", "export")
lopRenderNode.parm("lopoutput").set("$HIP/geo/USD_Maker/" + lopRenderNode.name() + "/" + lopRenderNode.name() + ".usd")
lopRenderNode.setInput(0, nullLopNode)

# Parse XML

tree = ET.parse(xml)
root = tree.getroot()

#Find all asset tags
assetTags = root.findall('.//asset')

#print(asset_tags)

for asset in assetTags:
    name = asset.find('name').text if asset.find('name') is not None else "default_name"
    ftrack_id = asset.find('ftrack_id').text if asset.find('ftrack_id') is not None else None
    asset_path = asset.find('asset_path').text if asset.find('asset_path') is not None else None
    shader_id = asset.find('shader_id').text if asset.find('shader_id') is not None else None

    # Create a geo node inside the subnet named after the asset name
    alembicNode = assetSubnet.createNode("alembic", name)
    if asset_path:
        # Replace 'assemblyDef' with 'alembic' in the path
        new_path = asset_path.replace('/assemblyDef/', '/alembic/')
        
        # Change the file extension from '.ma' to '.abc'
        new_path = os.path.splitext(new_path)[0] + '.abc'
        
        alembicNode.parm("fileName").set(new_path)
            
    nullNode = assetSubnet.createNode("null", name + "_OUT")
    nullNode.setInput(0, alembicNode)
    
    #Create AttribWrangle
    geoContainer = assetSubnet.createNode('attribwrangle', 'IP_'+name)
    geoContainer.parm("snippet").set("")
    geoContainer.parm("class").set("detail")
    
    ipNullNode = assetSubnet.createNode("null", "IP_" + name + "_OUT")
    ipNullNode.setInput(0, geoContainer)
    
    assdata = getInfo(shader_id)
    grabass = makeGrabAss(assetSubnet, name, assdata)
    assfile = grabass.parm("asset_filepath").eval()
    
    # Prepare the point data from XML
    points_data = []
    
    # Prepare the vex code to create points
    vex_code = "int points[];"
    
    #Read xforms
    
    xforms = asset.findall('.//xform')
    
    for xform in xforms:
        xform_text = xform.text.strip().split()
        tx, ty, tz = map(float, xform_text[:3])
        rx, ry, rz = map(float, xform_text[3:6])
        sx, sy, sz = map(float, xform_text[6:9])
        
        points_data.append((tx, ty, tz, rx, ry, rz, sx, sy, sz))
        
    for i, point in enumerate(points_data):
        tx, ty, tz, rx, ry, rz, sx, sy, sz = point
        
        orient = makeRotation(rx, ry, rz)
        
        #Add point position
        vex_code += "\nint pt{} = addpoint(geoself(), set({}, {}, {}));".format(i, tx, ty, tz)
        vex_code += ('\nsetpointattrib(geoself(), "orient", pt%d, {%f, %f, %f, %f}, "set");' % (i, orient[0], orient[1], orient[2], orient[3]))
        vex_code += '\nsetpointattrib(geoself(), "scale", pt{}, set({}, {}, {}), "set");'.format(i, sx, sy, sz)
        
    geoContainer.parm('snippet').set(vex_code)
    
    #READING ASS FILE
    content = read_ass_file(assfile)
    blocks = parse_ass_file(content)
    
    #Create a sopimport node inside the lopnet
    
    sopImpNode = lopnet.createNode("sopimport", "import_" + name)
    sopImpNode.parm("soppath").set(nullNode.path())
    
    #lopIpNode = lopnet.createNode("sopimport", "IP_" + name)
    #lopIpNode.parm("soppath").set(geoContainer.path())
    
    instancerNode = lopnet.createNode("instancer", "instance_" + name)
    instancerNode.setInput(1, sopImpNode)
    instancerNode.parm("transformsourcemode").set("extsop")
    instancerNode.parm("pointsoppath").set(geoContainer.path())
    instancerNode.parm("protopattern").set("%kind:component")
    instancerNode.parm("primpath").set("/geo/instance_"+name)
    instancerNode.parm("primkind").set("component")
    
    mtllib = lopnet.createNode("materiallibrary", "mtllib_" + name)
    
    shaderNode = mtllib.createNode("subnet", "shader_" + name)
    shaderNode.setMaterialFlag(True)
    
    connectorNode = shaderNode.createNode("subnetconnector", "subnetconnect")
    connectorNode.parm("connectorkind").set("output")
    connectorNode.parm("parmname").set("surface")
    connectorNode.parm("parmlabel").set("surface")
    connectorNode.parm("parmtype").set("surface")
    
    standardSurface = shaderNode.createNode("usdpreviewsurface", "stdsurface")
    connectorNode.setInput(0, standardSurface, 0)
    
    
    ### NOT WORKING, SETTING SIGNATURE IS HARD, ALTHOUGH WORKS WITHOUT IT
    
    #usdvarreader = shaderNode.createNode("usdprimvarreader", "usdvarreader")
    #usdvarreader.parm("varname").set("st")
    #usdvarreader.parm("signature").set("Float2")
    
    # Extract image blocks
    image_blocks = blocks.get('image', [])

    # Access and print the filename in each image block
    for image_block in image_blocks:
        makeTextures(image_block, shaderNode, standardSurface)

    shaderNode.layoutChildren()
    
    mtllib.setInput(0, instancerNode)
    
    mtlassign = lopnet.createNode("assignmaterial", "mtlassign_" + name)
    mtlassign.parm("primpattern1").set("/geo/*")
    mtlassign.parm("matspecpath1").set("/materials/shader_" + name) ### INCOMPLETE - ADD MAT NAME HERE
    mtlassign.setInput(0, mtllib)
    
    mergeLopNode.setNextInput(mtlassign)
    
    
    assetSubnet.layoutChildren()
    lopnet.layoutChildren()
    
baseNode.layoutChildren();
geoContainer.cook()


#AS
