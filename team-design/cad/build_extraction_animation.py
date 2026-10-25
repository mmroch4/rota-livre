"""Blender 4: articulated scoop animation plus coarse rigid-body discharge test.
Run: blender --background --python cad/build_extraction_animation.py
Metres. Pickup is prescribed; released particles use rigid-body physics.
"""
import bpy, math, os, random, json
from mathutils import Vector

OUT=os.path.dirname(os.path.abspath(__file__))
random.seed(26)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.render.fps=24; scene.frame_start=1; scene.frame_end=360
scene.gravity=(0,0,-9.81)

def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);return m
wood=mat('Wood',(.57,.35,.15));ply=mat('Plywood scoop',(.8,.60,.33))
blue=mat('Supported K-line chute',(.13,.38,.60));green=mat('A source',(.12,.40,.25))
grey=mat('B destination',(.45,.52,.59));sand=mat('Coarse sand proxies',(.91,.72,.35))
steel=mat('Pivot and transmission placeholders',(.22,.25,.29));motor=mat('Unverified actuator envelopes',(.9,.52,.10))
ink=mat('Labels',(.04,.07,.10))

def rigid(o,active=False,shape='BOX',friction=.35):
 bpy.context.view_layer.objects.active=o
 bpy.ops.rigidbody.object_add()
 r=o.rigid_body;r.type='ACTIVE' if active else 'PASSIVE';r.collision_shape=shape
 r.friction=friction;r.restitution=.02;r.use_margin=True;r.collision_margin=.0003
 if active:r.mass=.0002
 return o
def box(n,p,s,m,collision=False):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=n;o.dimensions=s
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 if collision:rigid(o)
 return o
def rod(n,a,b,r,m):
 d=Vector(b)-Vector(a);bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
 o=bpy.context.object;o.name=n;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(m);return o
def text(t,p,size=.022):
 bpy.ops.object.text_add(location=p);o=bpy.context.object;o.data.body=t;o.data.size=size;o.data.materials.append(ink)
def tray(n,x,y,l,w,h,m):
 box(n+' floor',(x,y,.003),(l,w,.006),m,True)
 for sign in [-1,1]:
  box(n+' end',(x+sign*(l-.004)/2,y,h/2),(.004,w,h),m,True)
  box(n+' side',(x,y+sign*(w-.004)/2,h/2),(l,.004,h),m,True)

box('Arena reference',(0.6,.3,-.009),(1.2,.6,.018),wood,True)
tray('A',.875,.3,.19,.19,.095,green);tray('B',.2,.3,.16,.24,.06,grey)
# Static sand bed is a visual reference only, not a continuum solver.
box('Reference sand bed - no contact solver',(.875,.3,.024),(.178,.178,.035),sand)

# Chute ends BEFORE A, removing the earlier interference with its opening.
low=Vector((.24,.3,.082));high=Vector((.70,.3,.235));d=high-low
angle=math.atan2(d.z,d.x)
o=box('129 supported chute',(low+high)/2,(d.length,.14,.005),blue,True);o.rotation_euler[1]=-angle
for y in [.228,.372]:
 o=box('129 chute wall',(.47,y,.174),(d.length,.004,.035),blue,True);o.rotation_euler[1]=-angle
# Capture hood attached to chute sides, suspended above B (no support on B).
box('129 discharge impact baffle',(.145,.3,.125),(.005,.148,.15),blue,True)
for y in [.228,.372]:box('129 discharge hood side',(.195,y,.125),(.105,.004,.15),blue,True)
for x,z in [(.32,.09),(.66,.20)]:
 for y in [.20,.40]:
  box('121 chute post',(x,y,z/2),(.03,.03,z),wood)
  box('125 independent foot',(x,y,.003),(.16,.065,.006),ply)
 box('120 cross support',(x,.3,z),(.025,.23,.02),wood)
for y in [.22,.38]:
 o=box('120 chute rail - stock length to verify',(.47,y,.146),(d.length,.018,.018),wood);o.rotation_euler[1]=-angle

# Two-link planar arm, 200 mm links, paired side plates, three rotary joints.
S=Vector((1.035,.3,.36)); L1=L2=.20
for y in [.19,.41]:
 box('121 shoulder tower',(S.x,y,.18),(.03,.03,.36),wood)
 box('125 tower foot',(1.035,y,.003),(.28,.08,.006),ply)
 rod('120 diagonal brace',(.91,y,.01),(S.x,y,.32),.008,wood)
rod('Shoulder shaft supported at both ends',(S.x,.175,S.z),(S.x,.425,S.z),.005,steel)
box('160 M1 shoulder drive envelope',(1.08,.18,.36),(.06,.035,.035),motor)
box('125 removable M1 cradle',(1.08,.18,.337),(.08,.05,.01),ply)
box('160 Arduino envelope',(1.095,.30,.018),(.07,.055,.025),green)
box('160 driver envelope',(1.105,.36,.02),(.05,.04,.03),steel)
box('Unselected power supply space',(1.10,.48,.03),(.09,.04,.055),grey)

upper=[];fore=[]
for y in [.235,.365]:
 upper.append(box('120 upper arm',(.9,y,.3),(L1,.012,.018),wood))
 fore.append(box('120 forearm',(.8,y,.2),(L2,.012,.018),wood))
elbow=rod('Elbow shaft',(.9,.22,.3),(.9,.38,.3),.004,steel)
elbow_motor=box('160 M2 elbow drive envelope',(.9,.395,.3),(.045,.025,.03),motor)
servo=box('160 bucket servo envelope',(.9,.225,.1),(.04,.02,.032),motor)
wrist=rod('147 scoop hinge envelope',(.9,.24,.1),(.9,.36,.1),.003,steel)

# Bucket local coordinates: rear pivot x=0; open digging lip x=-80 mm.
bucket=[]
def bucket_part(n,p,s):
 o=box(n,p,s,ply,True);o.rigid_body.kinematic=True;bucket.append((o,Vector(p)));return o
bucket_part('125 scoop floor',(-.04,0,-.0025),(.08,.11,.005))
bucket_part('125 scoop rear',(.0025,0,.020),(.005,.11,.045))
for y in [-.053,.053]:bucket_part('125 scoop side',(-.04,y,.020),(.08,.004,.045))

# Wrist path: approach, lower within A, drag 40mm, curl, rise, cross rim, tip, return.
poses=[(1,.94,.19,0),(35,.94,.052,0),(65,.90,.052,0),(85,.90,.062,25),
 (120,.90,.24,25),(150,.72,.35,25),(175,.72,.35,-60),
 (210,.72,.35,-60),(235,.90,.24,25),(265,.94,.19,0),(360,.94,.19,0)]
def pose(frame):
 for a,b in zip(poses,poses[1:]):
  if a[0]<=frame<=b[0]:
   t=(frame-a[0])/(b[0]-a[0]);t=t*t*(3-2*t)
   return Vector((a[1]+(b[1]-a[1])*t,.3,a[2]+(b[2]-a[2])*t)),math.radians(a[3]+(b[3]-a[3])*t)
 return Vector((poses[-1][1],.3,poses[-1][2])),0
def rotate(p,a):return Vector((p.x*math.cos(a)+p.z*math.sin(a),p.y,-p.x*math.sin(a)+p.z*math.cos(a)))
def key(o,f):
 o.keyframe_insert(data_path='location',frame=f);o.keyframe_insert(data_path='rotation_euler',frame=f)
def beam(o,a,b,f):
 o.location=(a+b)/2;o.rotation_euler[1]=-math.atan2(b.z-a.z,b.x-a.x);key(o,f)

for f in range(1,361):
 P,a=pose(f);dx=P.x-S.x;dz=P.z-S.z;dist=math.hypot(dx,dz)
 assert abs(L1-L2)<dist<L1+L2,('unreachable',f)
 t=math.atan2(dz,dx)-math.acos((L1*L1+dist*dist-L2*L2)/(2*L1*dist))
 E=S+Vector((L1*math.cos(t),0,L1*math.sin(t)))
 for o in upper:
  y=o.location.y;beam(o,Vector((S.x,y,S.z)),Vector((E.x,y,E.z)),f)
 for o in fore:
  y=o.location.y;beam(o,Vector((E.x,y,E.z)),Vector((P.x,y,P.z)),f)
 elbow.location=E;key(elbow,f)
 elbow_motor.location=E+Vector((0,.095,0));key(elbow_motor,f)
 wrist.location=P;key(wrist,f)
 servo.location=P+Vector((0,-.08,.015));servo.rotation_euler[1]=a;key(servo,f)
 for o,local in bucket:
  o.location=P+rotate(local,a);o.rotation_euler[1]=a;key(o,f)

# Coarse particles: pickup/carry is prescribed; discharge uses Bullet dynamics.
# 96 spheres are 5mm diameter visual proxies, not real sand grains or measured mass.
grains=[];release=176
for i in range(96):
 local=Vector((-.070+(i%8)*.008,-.040+((i//8)%6)*.016,.006+(i//48)*.006))
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.0025)
 o=bpy.context.object;o.name='Sand proxy %03d'%i;o.data.materials.append(sand)
 rigid(o,True,'SPHERE');o.rigid_body.kinematic=True
 initial=Vector((random.uniform(.835,.93),random.uniform(.255,.345),random.uniform(.043,.049)))
 for f in range(1,release):
  P,a=pose(f);target=P+rotate(local,a)
  t=max(0,min(1,(f-45)/35))
  o.location=initial.lerp(target,t);o.keyframe_insert(data_path='location',frame=f)
 o.rigid_body.keyframe_insert(data_path='kinematic',frame=release-1)
 o.rigid_body.kinematic=False;o.rigid_body.keyframe_insert(data_path='kinematic',frame=release)
 grains.append(o)

for name,f in [('Approach',1),('Lower',35),('Dig - prescribed pickup',65),('Curl',85),('Lift',120),('Over chute',150),('Physical release',176),('Return',235),('Settling',300)]:
 scene.timeline_markers.new(name,frame=f)
for o in scene.objects:
 if o.animation_data and o.animation_data.action:
  for fc in o.animation_data.action.fcurves:
   for k in fc.keyframe_points:k.interpolation='CONSTANT' if 'kinematic' in fc.data_path else 'LINEAR'

text('B | DESTINO',(.11,.09,.002));text('A | ORIGEM',(.80,.09,.002))
text('RECOLHA ANIMADA | descarga fisica aproximada',(.11,.53,.002),.019)
scene.world.color=(.7,.7,.7)
bpy.ops.object.light_add(type='AREA',location=(.5,-.3,1.5));bpy.context.object.data.energy=35;bpy.context.object.data.size=1.4
bpy.ops.object.camera_add(location=(1.5,-1.5,1.3));cam=bpy.context.object
cam.rotation_euler=(Vector((.61,.3,.13))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.5;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
world=scene.rigidbody_world;world.substeps_per_frame=64;world.solver_iterations=40
world.point_cache.frame_start=1;world.point_cache.frame_end=360
scene.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT')
path=os.path.join(OUT,'sand-extraction-animated.blend')
bpy.ops.wm.save_as_mainfile(filepath=path)
with bpy.context.temp_override(scene=scene,point_cache=world.point_cache):bpy.ops.ptcache.bake(bake=True)
scene.frame_set(360);deps=bpy.context.evaluated_depsgraph_get()
positions=[tuple(o.evaluated_get(deps).matrix_world.translation) for o in grains]
inside=sum(.124<x<.276 and .184<y<.416 and .006<z<.06 for x,y,z in positions)
report={'proxy_particles':len(grains),'proxy_diameter_mm':5,'release_frame':release,'final_frame':360,'particles_inside_B_final':inside,'pickup':'prescribed keyframes, NOT physical excavation','discharge':'rigid spheres, uncalibrated friction 0.35','cache_baked':world.point_cache.is_baked}
open(os.path.join(OUT,'extraction-simulation-report.json'),'w').write(json.dumps(report,indent=2))
for f in [65,150,195,360]:
 scene.frame_set(f);scene.render.filepath=os.path.join(OUT,'extraction-frame-%03d.png'%f);bpy.ops.render.render(write_still=True)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=path)
print('EXTRACTION_REPORT',json.dumps(report))
