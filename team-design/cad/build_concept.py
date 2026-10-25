"""Concept only. Run with Blender --background --python cad/build_concept.py.
Dimensions in mm. Shop blanks and mechanism interfaces require measurement.
"""
import bpy, math, os
from mathutils import Vector

OUT = os.path.dirname(os.path.abspath(__file__))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    return m
wood = material('Shop wood - section provisional', (.49,.28,.12))
ply = material('Shop 5mm plywood', (.73,.53,.29))
liner = material('129 K-line - sliding surface to test', (.16,.36,.56))
pcb = material('Electronics envelopes - exact models unknown', (.08,.30,.28))
actuator = material('Motor and servo envelopes - unverified', (.85,.53,.12))
green = material('A fixed source', (.12,.42,.29))
grey = material('B fixed destination', (.48,.55,.59))
sand = material('Loose sand', (.86,.69,.39))
metal = material('Shop wire and pulley - schematic', (.24,.27,.30))
white = material('Labels', (.07,.11,.16))
orange = material('Motion guide - NOT a part', (.95,.36,.07))

def box(name, loc, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object; o.name=name
    o.dimensions=size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    return o

def rod(name, a, b, radius, mat):
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=d.length, location=(Vector(a)+Vector(b))/2)
    o=bpy.context.object; o.name=name
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler(); o.data.materials.append(mat)
    return o

def label(text, loc, size=22):
    bpy.ops.object.text_add(location=loc)
    o=bpy.context.object; o.name='Label '+text
    o.data.body=text; o.data.size=size; o.data.extrude=.2
    o.data.materials.append(white)

def tray(name, x,y,z, length,width,height,thick,mat):
    box(name+' floor',(x,y,z+thick/2),(length,width,thick),mat)
    for yy in [-1,1]:
        box(name+' side',(x,y+yy*(width-thick)/2,z+height/2),(length,thick,height),mat)
    for xx in [-1,1]:
        box(name+' end',(x+xx*(length-thick)/2,y,z+height/2),(thick,width,height),mat)

# Arena and containers are reference geometry, not shop purchases.
box('Arena reference 1200 x 600',(600,300,-9),(1200,600,18),ply)
for y in [0,600]: box('Arena rim',(600,y,15),(1200,10,30),wood)
for x in [0,1200]: box('Arena rim',(x,300,15),(10,600,30),wood)
# B right edge = 280; A left edge = 780: exactly 500mm gap.
tray('B reference 160 x 240 x 60',200,300,0,160,240,60,4,grey)
tray('A reference 190 x 190 x 95',875,300,0,190,190,95,4,green)
box('Sand level illustrative only',(875,300,45),(178,178,4),sand)

# Proposed chute: 550mm horizontal reach, 200mm fall (~20 degrees).
start=Vector((250,300,80)); end=Vector((800,300,280))
theta=math.atan2(200,550); length=(end-start).length
o=box('129 K-line chute, thickness 5',(start+end)/2,(length,130,5),liner)
o.rotation_euler[1]=-theta
for y in [232,368]:
    o=box('129 K-line chute side',(525,y,195),(length,5,35),liner); o.rotation_euler[1]=-theta
for y in [216,384]:
    o=box('120 rectangular lath chute support - blank length unknown',(525,y,170),(length+30,20,20),wood)
    o.rotation_euler[1]=-theta

# Independent feet; each cut from one 300 x 300 x 5 plywood sheet.
for x in [290,790]:
    h=65 if x==290 else 247
    for y in [180,420]:
        box('125 plywood foot strip',(x,y,2.5),(240,40,5),ply)
        box('121 square lath support',(x,y,5+h/2),(30,30,h),wood)
    box('120 transverse support',(x,300,h),(30,270,20),wood)

# Lift tower outside A. Motors are removable envelopes, not verified interfaces.
for y in [185,415]:
    box('125 tower foot strip',(975,y,2.5),(240,35,5),ply)
    box('121 tower upright - 400mm assumed blank',(975,y,200),(30,30,400),wood)
box('120 tower crossbar',(975,300,385),(30,260,30),wood)
for y in [185,415]:
    rod('150 schematic wire brace',(790,y,15),(975,y,365),2,metal)
    rod('151 lift cord - routing provisional',(975,y,370),(975,y,300),2,metal)
    rod('141 pulley wheel placeholder',(975,y-5,365),(975,y+5,365),14,metal)
    box('141 pulley bracket envelope',(975,y,384),(30,16,12),metal)
    box('Guide shoe - plywood fabrication pending',(975,y,300),(42,42,35),ply)
    box('120 carriage side arm',(890,y,300),(170,20,20),wood)
    box('125 removable motor cradle',(1010,y,380),(55,35,5),ply)
rod('Lift drum shaft - actual shaft not yet selected',(975,175,365),(975,425,365),4,metal)
rod('M1 lift drum - fabrication and reduction pending',(975,270,365),(975,330,365),18,wood)
box('160 M1 DC lift motor and gearbox SPACE RESERVATION',(1015,185,405),(60,30,35),actuator)
box('160 M2 DC scoop translation drive SPACE RESERVATION',(940,415,325),(60,30,35),actuator)
rod('M2 translation cord schematic',(930,415,300),(810,415,300),2,metal)
for y in [220,380]:
    box('120 short horizontal carriage guide',(880,y,293),(200,15,15),wood)
box('125 scoop carriage cross member',(800,300,295),(20,200,10),ply)

# Front-hinged plywood scoop shown tipped towards chute; one static pose only.
bpy.ops.object.empty_add(location=(800,300,305))
scoop=bpy.context.object; scoop.name='Scoop tipping pivot - adjust Y rotation'
scoop_parts=[]
scoop_parts.append(box('125 plywood scoop floor',(860,300,307.5),(120,120,5),ply))
for y in [242,358]: scoop_parts.append(box('125 plywood scoop side',(860,y,327),(120,4,44),ply))
scoop_parts.append(box('125 plywood scoop back',(918,300,327),(4,120,44),ply))
for obj in scoop_parts:
    obj.parent=scoop; obj.matrix_parent_inverse=scoop.matrix_world.inverted()
scoop.rotation_euler[1]=math.radians(-35)
rod('147 hinge pin envelope',(800,235,305),(800,365,305),3,metal)
for y in [250,350]:box('147 real hinge leaf envelope',(805,y,300),(25,20,2),metal)
box('160 servo SPACE RESERVATION torque unknown',(800,208,315),(40,20,36),actuator)
box('125 removable servo cradle',(800,208,293),(50,30,5),ply)
rod('Servo horn linkage schematic',(800,218,315),(800,235,305),2,metal)

# Electronics on separate plywood tray away from the sand; no glue/screws into electronics.
box('125 electronics tray',(1090,300,7.5),(160,160,5),ply)
box('160 Arduino envelope - board unconfirmed',(1070,280,20),(70,55,15),pcb)
box('160 DC driver envelope - driver unconfirmed',(1135,300,25),(40,45,25),pcb)
box('POWER reserved volume - supply NOT selected',(1080,350,35),(95,35,45),grey)
for y in [258,304]:box('185 removable board retaining strap',(1070,y,29),(80,3,3),metal)
rod('Cable route schematic',(1135,300,40),(1030,415,320),2,metal)
rod('Lift motion GUIDE not material',(875,300,110),(875,300,260),2,orange)
rod('Flow GUIDE not material',(700,300,260),(370,300,140),3,orange)
label('B | DESTINO', (100,105,3),24)
label('A | ORIGEM', (800,95,3),24)
label('A  ->  B', (450,75,3),32)
label('ELETRICO | M1 eleva | M2 recolhe | servo bascula', (120,530,3),19)

scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=.001
scene.world.color=(.8,.8,.8)
bpy.ops.object.light_add(type='AREA', location=(450,-100,1300))
bpy.context.object.data.energy=18000000; bpy.context.object.data.shape='DISK'; bpy.context.object.data.size=1000
bpy.ops.object.camera_add(location=(1450,-1550,1400))
cam=bpy.context.object; cam.rotation_euler=(Vector((600,300,100))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'; cam.data.ortho_scale=1500; cam.data.clip_end=10000
scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.cycles.use_denoising=False
scene.render.resolution_x=1600; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.path.join(OUT,'sand-transfer-electric-preview.png')
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.update()
# Open directly in a useful camera view with material colours.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.clip_end=10000
            area.spaces.active.shading.color_type='MATERIAL'
            area.spaces.active.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'sand-transfer-electric.blend'))
# Export with physical metre coordinates for glTF viewers.
for o in list(scene.objects):
    if o.type=='FONT':
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
        bpy.ops.object.convert(target='MESH')
# Portable OBJ export without optional Blender Python dependencies; units metres.
with open(os.path.join(OUT,'sand-transfer-electric.obj'),'w') as f:
    f.write('# Sand transfer concept. Units: metres.\n')
    offset=1
    for o in scene.objects:
        if o.type!='MESH': continue
        f.write('o '+o.name.replace(' ','_')+'\n')
        for v in o.data.vertices:
            p=(o.matrix_world @ v.co)*.001
            f.write('v %f %f %f\n'%tuple(p))
        for face in o.data.polygons:
            f.write('f '+' '.join(str(i+offset) for i in face.vertices)+'\n')
        offset+=len(o.data.vertices)
bpy.ops.render.render(write_still=True)
