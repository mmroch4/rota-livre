"""Inclined screw conveyor from A, fixed chute to B.
Run: blender --background --python cad/build_archimedes_screw.py
Metres. Fixed tube, helix turning inside with 2.5 mm radial clearance, motor on the axis
at the top. The lowest 100 mm of tube is an open-top half-pipe buried in A's sand: loose
sand only enters from above (a square-cut inclined mouth faces down), and the fixed wall
stops the sand turning with the flights, which is what makes a screw convey. Trials
with the tube turning with the helix, and with exposed flights, drew no grains in.
The top 40 mm has its lower half cut away: sand drops out onto the chute.
Only the rotation is prescribed: pickup from the grain bed in A, lift, discharge and
the chute flow all come from Bullet rigid-body contact.
Short trials (no renders, output to $SCREW_OUT): SCREW_FRAMES=96 SCREW_OUT=/tmp/x;
SCREW_PROBE=1 puts a few grains in the bore instead of the bed (direction check).
"""
import bpy, bmesh, math, os, json, random
from mathutils import Vector, Quaternion

OUT=os.path.dirname(os.path.abspath(__file__))
FRAMES=int(os.environ.get('SCREW_FRAMES',300));TEST='SCREW_OUT' in os.environ
DEST=os.environ.get('SCREW_OUT',OUT)
random.seed(26)
FRICTION=.7  # pair friction 0.49 (~26 deg), as in build_bridge_options.py; uncalibrated
RPM=120;START=24  # grains settle for 1 s before the screw turns
# Screw: 50 mm bore, 45 mm flights, 10 mm shaft, 60 mm pitch, 550 mm long, 35 deg.
RI=.025;RO=.029;RF=.0225;RS=.005;PITCH=.06;L=.55;INTAKE=.10;WINDOW=.04;ANGLE=math.radians(35)
P0=Vector((.935,.30,.032));U=Vector((-math.cos(ANGLE),0,math.sin(ANGLE)));P1=P0+U*L
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.render.fps=24
s.frame_start=1;s.frame_end=FRAMES;s.gravity=(0,0,-9.81)

def mat(n,c,alpha=1):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,alpha)
 if alpha<1:
  m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*c,1)
  b.inputs['Alpha'].default_value=alpha;m.blend_method='BLEND'
 return m
wood=mat('Wood',(.57,.35,.15));ply=mat('125 plywood',(.8,.60,.33));blue=mat('129 K-line chute',(.13,.38,.60))
green=mat('A source',(.12,.40,.25));grey=mat('B destination',(.45,.52,.59));sand=mat('Grain proxies',(.91,.72,.35))
steel=mat('Shafts and rollers',(.22,.25,.29));motor=mat('Unverified actuator envelopes',(.9,.52,.10))
tube_mat=mat('130 cardboard tube (shown see-through)',(.75,.62,.45),.22);helix_mat=mat('130 cardboard helix',(.85,.45,.15))
ink=mat('Labels',(.04,.07,.10))

def rigid(o,active=False,shape='BOX',margin=.0003):
 bpy.context.view_layer.objects.active=o;bpy.ops.rigidbody.object_add();r=o.rigid_body
 r.type='ACTIVE' if active else 'PASSIVE';r.collision_shape=shape
 r.friction=FRICTION;r.restitution=.02;r.use_margin=True;r.collision_margin=margin
 if active:r.mass=.0006;r.angular_damping=.9
 return o
def box(n,p,d,m,collision=False):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=n;o.dimensions=d
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 if collision:rigid(o)
 return o
def rod(n,a,b,r,m):
 d=Vector(b)-Vector(a);bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
 o=bpy.context.object;o.name=n;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(m);return o
def text(t,p,size=.02):
 bpy.ops.object.text_add(location=p);o=bpy.context.object;o.data.body=t;o.data.size=size;o.data.materials.append(ink)
def tray(n,x,y,l,w,h,m):
 box(n+' floor',(x,y,.003),(l,w,.006),m,True)
 for a in [-1,1]:
  box(n+' end',(x+a*(l-.004)/2,y,h/2),(.004,w,h),m,True)
  box(n+' side',(x,y+a*(w-.004)/2,h/2),(l,.004,h),m,True)
def plate(n,a,b,width,y,thick,m):
 """Plate whose centre line runs from a to b (x,z) at y; collides."""
 d=Vector((b[0]-a[0],0,b[1]-a[1]))
 o=box(n,((a[0]+b[0])/2,y,(a[1]+b[1])/2),(d.length,width,thick),m,True);o.rotation_euler[1]=-math.atan2(d.z,d.x);return o

box('Arena reference',(.6,.3,-.009),(1.2,.6,.018),wood,True)
tray('A',.875,.30,.19,.19,.095,green);tray('B',.20,.30,.16,.24,.06,grey)

# Meshes in screw coordinates (local Z = axis, origin at the intake end, local +Y up).
base=U.to_track_quat('Z','Y');N=base@Vector((0,1,0))  # perpendicular to the axis, upwards
def part(name,m,build,kinematic):
 bm=bmesh.new();build(bm);me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);s.collection.objects.link(o);o.data.materials.append(m)
 o.location=P0;o.rotation_mode='QUATERNION';o.rotation_quaternion=base
 rigid(o,False,'MESH',.0008);o.rigid_body.kinematic=kinematic;o.rigid_body.mesh_source='BASE';return o
def cylinder(bm,r,n,rings,z0,z1,a0=0,a1=math.tau):
 m=n if a1-a0>=math.tau-1e-9 else n+1
 vs=[[bm.verts.new((r*math.cos(a0+(a1-a0)*i/n),r*math.sin(a0+(a1-a0)*i/n),z0+(z1-z0)*k/rings)) for i in range(m)] for k in range(rings+1)]
 for k in range(rings):
  for i in range(n):bm.faces.new((vs[k][i],vs[k][(i+1)%m],vs[k+1][(i+1)%m],vs[k+1][i]))
def tube_shape(bm):
 cylinder(bm,RI,24,9,INTAKE,L-WINDOW)
 cylinder(bm,RI,14,2,0,INTAKE,math.pi-.35,math.tau+.35)  # open-top intake half-pipe
 cylinder(bm,RI,12,1,L-WINDOW,L,0,math.pi)  # discharge window: lower half cut away
 bm.faces.new([bm.verts.new((RI*math.cos(math.tau*i/24),RI*math.sin(math.tau*i/24),L)) for i in range(24)])  # end cap
def helix(bm):
 steps=int(L/PITCH*16);prev=None
 for k in range(steps+1):
  a=2*math.pi*k/16;z=PITCH*k/16
  if z>L:break
  pair=(bm.verts.new((RS*math.cos(a),RS*math.sin(a),z)),bm.verts.new((RF*math.cos(a),RF*math.sin(a),z)))
  if prev:bm.faces.new((prev[0],prev[1],pair[1],pair[0]))
  prev=pair
 cylinder(bm,RS,12,1,0,L)
tube=part('130 fixed cardboard tube, open-top intake',tube_mat,tube_shape,False)
screw=part('130 cardboard helix on 122 round lath',helix_mat,helix,True)
for f in range(1,FRAMES+1):
 # Negative spin about +axis lifts material with this right-handed helix.
 theta=-2*math.pi*RPM/60*max(0,f-START)/24
 screw.rotation_quaternion=base@Quaternion((0,0,1),theta);screw.keyframe_insert(data_path='rotation_quaternion',frame=f)

# Two cradles outside A hold the fixed tube; the kit motor drives the shaft at the top
# through the closed end cap (no coupling modelled: the 184 wheel hub is one option).
for tt,name in [(.24,'lower'),(.47,'upper')]:
 c=P0+U*tt;zb=c.z-RO/math.cos(ANGLE)
 for y in [.262,.338]:box('121 %s cradle post'%name,(c.x,y,zb/2),(.02,.02,zb),wood)
 box('125 %s cradle saddle'%name,(c.x,.30,zb-.004),(.03,.096,.008),ply)
 box('125 %s cradle foot'%name,(c.x,.30,.003),(.06,.16,.006),ply)
rod('122 shaft extension',P1,P1+U*.02,RS,steel)
rod('160 M1 TT motor envelope (coaxial)',P1+U*.02,P1+U*.085,.014,motor)

# Fixed chute from under the upper tube end to B, side walls and a back wall; hood over B.
CH0=(.53,.25);CH1=(.26,.09)
plate('129 chute floor',CH0,CH1,.08,.30,.005,blue)
for y in [.258,.342]:
 plate('129 chute wall',(CH0[0],CH0[1]+.03),(CH1[0],CH1[1]+.03),.004,y,.06,blue)
# Back wall stops below the tube (at x=.535 its underside is at z=.277): a taller wall
# cut through the bore and blocked every grain short of the discharge window.
box('129 chute back wall',(.535,.30,.2585),(.004,.08,.027),blue,True)
box('129 hood impact baffle',(.14,.30,.15),(.005,.10,.16),blue,True)
for y in [.248,.352]:box('129 hood side',(.20,y,.15),(.12,.004,.16),blue,True)
for x,z in [(.51,.24),(.30,.11)]:
 for y in [.245,.355]:box('121 chute post',(x,y,z/2),(.02,.02,z),wood)
box('120 hood bracket',(.24,.44,.232),(.12,.02,.012),wood);box('121 hood post',(.30,.44,.115),(.02,.02,.23),wood)

# Grain bed, ~70 mm deep, burying the open intake. 9 mm faceted proxies on a grid;
# grains between the flights are kept, none overlap the helix, shaft or tube wall.
def overlaps_rotor(q,r=.0045,gap=.001):
 l=base.inverted()@(q-P0);rho=math.hypot(l.x,l.y);z=l.z
 if not -r-gap<z<L+r+gap:return False
 if rho<RS+r+gap:return True
 if RI-r-gap<rho<RO+r+gap and (z>INTAKE-r-gap or l.y<.35*RI):return True  # tube wall
 if rho<RF+r+gap:
  turn=(math.atan2(l.y,l.x)%math.tau)/math.tau
  dz=min(abs(z-PITCH*(turn+k)) for k in range(-1,int(L/PITCH)+2))
  return dz*math.cos(math.atan(PITCH/(math.tau*max(rho,RS))))<r+gap
 return False
grains=[]
if os.environ.get('SCREW_PROBE'):  # direction probe: grains at the bottom of the bore only
 bed=[P0+U*(.12+.03*i)-N*(RI-.0065) for i in range(8)]
else:
 bed=[Vector((.840+ix*.0098,.2706+iy*.0098,.0105+iz*.0095)) for ix in range(13) for iy in range(7) for iz in range(7)]
for q in bed:
   if overlaps_rotor(q):continue
   bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.0045,location=q)
   o=bpy.context.object;o.name='Grain proxy %03d'%len(grains);o.data.materials.append(sand)
   rigid(o,True,'CONVEX_HULL');grains.append(o)
for o in (screw,):
 for fc in o.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'

text('B | DESTINATION',(.11,.07,.002));text('A | SOURCE',(.80,.07,.002))
text('SCREW CONVEYOR | fixed tube, %d rpm, %d deg, 50 mm bore'%(RPM,round(math.degrees(ANGLE))),(.11,.56,.002),.019)
s.timeline_markers.new('Settle',frame=1);s.timeline_markers.new('Screw starts',frame=START)
s.world.color=(.7,.7,.7)
bpy.ops.object.light_add(type='AREA',location=(.5,-.3,1.5));bpy.context.object.data.energy=35;bpy.context.object.data.size=1.4
bpy.ops.object.camera_add(location=(1.25,-1.15,.95));cam=bpy.context.object
cam.rotation_euler=(Vector((.6,.3,.17))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.15;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=False
s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard'
world=s.rigidbody_world;world.substeps_per_frame=24;world.solver_iterations=15
world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
s.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT')
path=os.path.join(DEST,'archimedes-screw.blend');bpy.ops.wm.save_as_mainfile(filepath=path)
with bpy.context.temp_override(scene=s,point_cache=world.point_cache):bpy.ops.ptcache.bake(bake=True)

def where(x,y,z):
 if not (-.05<x<1.25 and -.05<y<.65 and z>-.02):return 'ejected_numerical'
 if .124<x<.276 and .184<y<.416 and z<.065:return 'in_B'
 if .784<x<.966 and .209<y<.391 and z<.095:return 'in_A'
 if z<.03:return 'spilled_on_arena'
 return 'in_screw_or_chute'
samples=[];lifted=set();first_in_B=None
for f in range(1,FRAMES+1):
 s.frame_set(f);deps=bpy.context.evaluated_depsgraph_get()
 pos=[o.evaluated_get(deps).matrix_world.translation for o in grains]
 for i,p in enumerate(pos):
  if p.z>.12:lifted.add(i)
 if f%24==0 or (os.environ.get('SCREW_PROBE') and f%6==0):
  row={'frame':f,'in_B':0,'in_A':0,'in_screw_or_chute':0,'spilled_on_arena':0,'ejected_numerical':0,'inside_bore':0,'max_axial_mm':0}
  for p in pos:
   row[where(*p)]+=1;a=(p-P0).dot(U)
   if 0<a<L and ((p-P0)-U*a).length<RI:row['inside_bore']+=1;row['max_axial_mm']=max(row['max_axial_mm'],round(a*1000))
  if os.environ.get('SCREW_PROBE'):row['axial_mm']=[round((p-P0).dot(U)*1000) for p in pos]
  if row['in_B'] and first_in_B is None:first_in_B=f
  samples.append(row)
last=[r for r in samples if r['frame']>=FRAMES-5*24]
rate=(last[-1]['in_B']-last[0]['in_B'])/((last[-1]['frame']-last[0]['frame'])/24) if len(last)>1 else 0
report={'frames':FRAMES,'seconds':FRAMES/24,'grains':len(grains),'rpm':RPM,'angle_deg':round(math.degrees(ANGLE)),
 'bore_mm':RI*2000,'flight_diameter_mm':RF*2000,'open_intake_mm':INTAKE*1000,'pitch_mm':PITCH*1000,'length_mm':L*1000,'screw_starts_s':START/24,
 'unique_grains_lifted_above_120mm':len(lifted),'first_grain_in_B_s':first_in_B and first_in_B/24,
 'grains_per_s_into_B_last_5s':round(rate,2),'final':samples[-1],'samples':samples,
 'grain':'9 mm faceted convex hull, 0.6 g, angular damping 0.9','pair_friction':round(FRICTION*FRICTION,3),
 'pickup':'rigid-body contact from a grain bed; no grain keyframes','drive':'prescribed rotation, infinite torque',
 'cache_baked':world.point_cache.is_baked}
open(os.path.join(DEST,'archimedes-screw-report.json'),'w').write(json.dumps(report,indent=2))
if not TEST:
 for f in [48,144,240,FRAMES]:
  s.frame_set(f);s.render.filepath=os.path.join(OUT,'archimedes-screw-frame-%03d.png'%f);bpy.ops.render.render(write_still=True)
 s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=path)
print('SCREW_REPORT',json.dumps({k:v for k,v in report.items() if k!='samples'}))
