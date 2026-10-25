"""Alternative B: physical coarse-particle pickup test, not a sand DEM model.
All grain motion uses Bullet from frame 1. Only the wheel rotation is prescribed.
Run with Blender --background --python cad/build_bucket_wheel.py.
"""
import bpy, math, os, json, random
from mathutils import Vector
OUT=os.path.dirname(os.path.abspath(__file__))
random.seed(26)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.render.fps=24
s.frame_start=1;s.frame_end=360;s.gravity=(0,0,-9.81)
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);return m
wood=mat('Wood',(.55,.34,.17));ply=mat('125 plywood',(.8,.58,.30));sand=mat('10mm spherical proxies',(.9,.68,.28))
green=mat('A reference',(.1,.4,.28));blue=mat('Test receiver NOT B',(.16,.36,.58));metal=mat('Shaft dimensions unverified',(.23,.27,.30));yellow=mat('Drive reservation',(.9,.5,.08))
def rb(o,active=False):
 bpy.context.view_layer.objects.active=o;bpy.ops.rigidbody.object_add();r=o.rigid_body
 r.type='ACTIVE' if active else 'PASSIVE';r.collision_shape='SPHERE' if active else 'BOX'
 r.use_margin=True;r.collision_margin=.0003;r.friction=.4;r.restitution=.01
 if active:r.mass=.0008
def box(n,p,d,m,collide=False):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=n;o.dimensions=d
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 if collide:rb(o)
 return o
def rod(n,a,b,r,m):
 d=Vector(b)-Vector(a);bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
 o=bpy.context.object;o.name=n;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(m);return o
def label(t,p):
 bpy.ops.object.text_add(location=p);o=bpy.context.object;o.data.body=t;o.data.size=.014;o.data.materials.append(metal)
def tray(n,x,y,l,w,h,m):
 box(n+' floor',(x,y,.003),(l,w,.006),m,True)
 for a in [-1,1]:
  box(n+' end',(x+a*(l-.004)/2,y,h/2),(.004,w,h),m,True)
  box(n+' side',(x,y+a*(w-.004)/2,h/2),(l,.004,h),m,True)
box('Test bench reference',(.85,.3,-.01),(.65,.50,.02),wood,True)
tray('A',.875,.30,.19,.19,.095,green)
tray('TEST RECEIVER',.69,.30,.15,.18,.06,blue)
C=Vector((.875,.30,.110))
for y in [.185,.415]:
 box('125 frame foot',(.875,y,.003),(.22,.06,.006),ply)
 box('121 independent bearing support',(.875,y,.057),(.03,.025,.102),wood)
 rod('Bearing envelope',(.875,y-.009,.11),(.875,y+.009,.11),.012,metal)
rod('Shaft - fit and material unverified',(.875,.16,.11),(.875,.45,.11),.004,metal)
box('Motor and reduction envelope',(.875,.465,.11),(.06,.035,.035),yellow)
box('125 removable drive cradle',(.875,.465,.085),(.08,.045,.01),ply)

# Six rigid cups: open in +local Z, collect with negative Y-axis rotation.
# All dimensions contribute to the <=170mm swept diameter.
panels=[('outer',(.080,0,0),(.005,.075,.026)),
 ('inner',(.052,0,0),(.005,.075,.026)),
 ('back',(.066,0,-.014),(.033,.075,.004)),
 ('side L',(.066,-.039,0),(.033,.004,.032)),
 ('side R',(.066,.039,0),(.033,.004,.032))]
def rot(p,a):return Vector((p[0]*math.cos(a)+p[2]*math.sin(a),p[1],-p[0]*math.sin(a)+p[2]*math.cos(a)))
def theta(f):return -2*math.pi*max(0,min(240,f-48))/240
moving=[]
for i in range(6):
 phase=i*math.tau/6
 for n,p,d in panels:
  o=box('Cup %d %s'%(i+1,n),C+rot(p,phase),d,ply,True);o.rigid_body.kinematic=True
  moving.append((o,Vector(p),phase))
 for y in [-.043,.043]:
  o=box('125 wheel spoke %d'%i,C+rot((.035,y,0),phase),(.07,.005,.01),ply,True)
  o.rigid_body.kinematic=True;moving.append((o,Vector((.035,y,0)),phase))
for o,p,phase in moving:
 for f in [1,48,*range(49,289),360]:
  a=phase+theta(f);o.location=C+rot(p,a);o.rotation_euler[1]=a
  o.keyframe_insert(data_path='location',frame=f);o.keyframe_insert(data_path='rotation_euler',frame=f)
 for fc in o.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'

# Seed a non-overlapping coarse granular bed, excluding initial wheel solids.
grains=[];radius=.005
def intersects_wheel(p):
 for o,local,phase in moving:
  q=rot(p-C,-phase)-local
  if all(abs(q[k])<o.dimensions[k]/2+radius+.0005 for k in range(3)):return True
 return False
for ix in range(11):
 for iy in range(9):
  for iz in range(5):
   p=Vector((.815+ix*.012,.252+iy*.012,.013+iz*.012))
   if intersects_wheel(p):continue
   bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=radius,location=p)
   o=bpy.context.object;o.name='Grain proxy %03d'%len(grains);o.data.materials.append(sand);rb(o,True);grains.append(o)

label('A: FIXO',(.83,.205,.098));label('RECETOR DE TESTE',(.61,.17,.002))
label('RODA DE CONCHAS | 1 volta / 10 s',(.64,.51,.002))
for name,f in [('Settle grains',1),('Start 6 RPM',48),('Quarter turn',108),('Half turn',168),('Full turn',288),('Final settling',360)]:s.timeline_markers.new(name,frame=f)
s.world.color=(.65,.65,.65)
bpy.ops.object.light_add(type='AREA',location=(.7,-.2,1));bpy.context.object.data.energy=16;bpy.context.object.data.size=.8
bpy.ops.object.camera_add(location=(1.35,-.45,.65));cam=bpy.context.object
cam.rotation_euler=(Vector((.82,.3,.09))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.68;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=False
s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard'
world=s.rigidbody_world;world.substeps_per_frame=64;world.solver_iterations=40
world.point_cache.frame_start=1;world.point_cache.frame_end=360
s.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT')
path=os.path.join(OUT,'bucket-wheel-test.blend');bpy.ops.wm.save_as_mainfile(filepath=path)
with bpy.context.temp_override(scene=s,point_cache=world.point_cache):bpy.ops.ptcache.bake(bake=True)
lifted=set();escaped=set();samples=[]
for f in range(1,361):
 s.frame_set(f);deps=bpy.context.evaluated_depsgraph_get()
 pp=[tuple(o.evaluated_get(deps).matrix_world.translation) for o in grains]
 for i,(x,y,z) in enumerate(pp):
  if z>.105:lifted.add(i)
  if not (.780<x<.970 and .205<y<.395):escaped.add(i)
 if f in [48,108,168,228,288,360]:
  samples.append({'frame':f,'in_A':sum(.784<x<.966 and .209<y<.391 and .006<z<.095 for x,y,z in pp),
   'in_test_receiver':sum(.619<x<.761 and .214<y<.386 and .006<z<.06 for x,y,z in pp)})
report={'grain_count':len(grains),'grain_diameter_mm':10,'rpm':6,'revolutions':1,'unique_particles_lifted_above_105mm':len(lifted),'unique_particles_outside_A_xy':len(escaped),'samples':samples,'cache_baked':world.point_cache.is_baked,'pickup':'rigid-body contact, no grain keyframes','drive':'prescribed rotation, infinite available torque; no stall model','limitations':'coarse spheres and uncalibrated friction; receiver is not competition B'}
open(os.path.join(OUT,'bucket-wheel-report.json'),'w').write(json.dumps(report,indent=2))
for f in [48,108,168,288,360]:
 s.frame_set(f);s.render.filepath=os.path.join(OUT,'wheel-frame-%03d.png'%f);bpy.ops.render.render(write_still=True)
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=path)
print('WHEEL_REPORT',json.dumps(report))
