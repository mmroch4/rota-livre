"""Bridge options from the bucket wheel (in A) to B: tilting tray vs belt conveyor.
Run: blender --background --python cad/build_bridge_options.py -- tilt
     blender --background --python cad/build_bridge_options.py -- belt
Metres. The wheel is visual only and the feed onto the bridge is prescribed (same
schedule in both options). The bridge motion (tray tilt or belt) is prescribed;
every grain after release moves by Bullet rigid-body contact.
"""
import bpy, math, os, sys, json, random
from mathutils import Vector

OPTION=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'tilt'
assert OPTION in ('tilt','belt'),OPTION
OUT=os.path.dirname(os.path.abspath(__file__))
random.seed(26)
FRAMES=600
# Bullet multiplies the two frictions of a contact: 0.7*0.7 = 0.49, a slide angle of
# about 26 degrees. Real sand on K-line/tarp is NOT measured; this is the key unknown.
FRICTION=.7
BY=.38;BW=.07  # bridge centre line and width (y), beside the wheel on its spout side
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.render.fps=24
s.frame_start=1;s.frame_end=FRAMES;s.gravity=(0,0,-9.81)

def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);return m
wood=mat('Wood',(.57,.35,.15));ply=mat('125 plywood',(.8,.60,.33));blue=mat('129 K-line bridge',(.13,.38,.60))
green=mat('A source',(.12,.40,.25));grey=mat('B destination',(.45,.52,.59));sand=mat('Grain proxies',(.91,.72,.35))
steel=mat('Shafts and rollers',(.22,.25,.29));motor=mat('Unverified actuator envelopes',(.9,.52,.10))
belt=mat('193 tarp belt',(.12,.12,.14));ink=mat('Labels',(.04,.07,.10))

def rigid(o,active=False,shape='BOX'):
 bpy.context.view_layer.objects.active=o;bpy.ops.rigidbody.object_add();r=o.rigid_body
 r.type='ACTIVE' if active else 'PASSIVE';r.collision_shape=shape
 r.friction=FRICTION;r.restitution=.02;r.use_margin=True;r.collision_margin=.0003
 if active:r.mass=.0003;r.angular_damping=.9
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
def rot(p,a):return Vector((p[0]*math.cos(a)+p[2]*math.sin(a),p[1],-p[0]*math.sin(a)+p[2]*math.cos(a)))
def key(o,f):
 o.keyframe_insert(data_path='location',frame=f);o.keyframe_insert(data_path='rotation_euler',frame=f)

box('Arena reference',(.6,.3,-.009),(1.2,.6,.018),wood,True)
tray('A',.875,.30,.19,.19,.095,green);tray('B',.20,.30,.16,.24,.06,grey)

# Bucket wheel (visual only): same envelope as bucket-wheel-test, 6 rpm. Each cup has
# a low lip on +y so it empties sideways onto the bridge after passing the top.
C=Vector((.875,.30,.110))
for y in [.185,.415]:
 box('125 frame foot',(.875,y,.003),(.22,.06,.006),ply)
 box('121 bearing support',(.875,y,.057),(.03,.025,.102),wood)
rod('Wheel shaft',(.875,.16,.11),(.875,.45,.11),.004,steel)
box('160 M1 wheel drive envelope',(.875,.465,.11),(.06,.035,.035),motor)
bpy.ops.object.empty_add(location=C);hub=bpy.context.object;hub.name='Wheel hub'
panels=[('outer',(.080,0,0),(.005,.075,.026)),('inner',(.052,0,0),(.005,.075,.026)),
 ('back',(.066,0,-.014),(.033,.075,.004)),('side',(.066,-.039,0),(.033,.004,.032)),
 ('spout lip',(.066,.039,-.009),(.033,.004,.014))]
for i in range(6):
 phase=i*math.tau/6
 parts=[box('Cup %d %s'%(i+1,n),C+rot(p,phase),d,ply) for n,p,d in panels]
 parts+=[box('125 wheel spoke %d'%i,C+rot((.035,y,0),phase),(.07,.005,.01),ply) for y in [-.043,.043]]
 for o in parts:
  o.rotation_euler[1]=phase;o.parent=hub;o.matrix_parent_inverse=hub.matrix_world.inverted()
hub.rotation_euler[1]=0;hub.keyframe_insert(data_path='rotation_euler',index=1,frame=1)
hub.rotation_euler[1]=-math.tau*(FRAMES-1)/240;hub.keyframe_insert(data_path='rotation_euler',index=1,frame=FRAMES)

# Discharge hood over B, shared by both options; supported outside B's footprint.
box('129 hood impact baffle',(.14,BY,.15),(.005,.09,.16),blue,True)
for y in [BY-.042,BY+.042]:box('129 hood side',(.205,y,.15),(.13,.004,.16),blue,True)
box('120 hood bracket',(.24,.44,.232),(.12,.02,.012),wood);box('121 hood post',(.30,.44,.115),(.02,.02,.23),wood)

if OPTION=='tilt':
 # Tray hinged outside B (x=.30); a 50 mm lip overhangs B. Rests at ~4 deg while the
 # wheel fills it, then a string over a pulley lifts the A end to 35 deg in 2 s.
 PIV=Vector((.30,BY,.11));L=.62
 phi0=math.asin((.155-PIV.z)/L);phimax=math.radians(35)
 plan=[(1,0),(150,0),(198,1),(246,1),(282,0),(420,0),(468,1),(516,1),(552,0),(FRAMES,0)]
 def lift(f):
  for a,b in zip(plan,plan[1:]):
   if a[0]<=f<=b[0]:
    t=(f-a[0])/(b[0]-a[0]);t=t*t*(3-2*t);return a[1]+(b[1]-a[1])*t
  return 0
 def phi(f):return phi0+(phimax-phi0)*lift(f)
 # Spawning over the bridge while it moves would place grains inside it: those cups
 # pour onto the wheel side instead and fall back into A (counted as recirculated).
 def bridge_clear(f):return phi(f)<phi0+math.radians(1) or phi(f)>phimax-math.radians(1)
 # Both side walls run full length: the cups pour over the inner one (an open side
 # spilled grains off the tilted tray in the first run).
 parts=[('129 tray floor',(.285,0,-.004),(.67,BW,.008)),('129 tray outer wall',(.285,.037,.015),(.67,.004,.03)),
  ('129 tray inner wall',(.285,-.037,.015),(.67,.004,.03)),('129 tray back wall',(.618,0,.015),(.004,BW,.03))]
 moving=[]
 for n,p,d in parts:
  o=box(n,PIV+Vector(p),d,blue,True);o.rigid_body.kinematic=True;moving.append((o,Vector(p)))
 rod('147 hinge axle',(PIV.x,.325,PIV.z),(PIV.x,.425,PIV.z),.004,steel)
 for y in [.325,.425]:box('121 hinge post',(PIV.x,y,PIV.z/2),(.02,.02,PIV.z),wood)
 box('121 rest stop',(.74,BY,.068),(.02,.02,.136),wood)
 P=Vector((.72,BY,.56))
 box('121 tower post',(.72,.45,.29),(.025,.025,.58),wood);box('125 tower foot',(.72,.45,.003),(.16,.10,.006),ply)
 box('120 tower arm',(.72,.4125,.575),(.02,.075,.015),wood)
 rod('141 pulley',(P.x,BY-.01,P.z),(P.x,BY+.01,P.z),.015,steel)
 box('160 M2 winch envelope',(.72,.50,.03),(.06,.035,.035),motor)
 rod('151 cord to winch',(P.x,BY+.01,P.z),(.72,.50,.05),.0012,ink)
 bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.0012,depth=1);cord=bpy.context.object;cord.name='151 lifting cord';cord.data.materials.append(ink)
 for f in range(1,FRAMES+1):
  a=-phi(f)
  for o,p in moving:o.location=PIV+rot(p,a);o.rotation_euler[1]=a;key(o,f)
  E=PIV+rot((.50,0,0),a);d=P-E
  cord.location=(P+E)/2;cord.rotation_euler=d.to_track_quat('Z','Y').to_euler();cord.scale=(1,1,d.length)
  key(cord,f);cord.keyframe_insert(data_path='scale',frame=f)
 surface_x=.917
else:
 # Belt: tarp loop over two rollers, top run moving towards B at 0.1 m/s, 4.5 deg down.
 # Modelled as a chain of rigid slats travelling around the loop; they carry grains by friction.
 T=Vector((.90,.145));H=Vector((.26,.095));R=.015;rho=R+.002;V=.10
 u=(H-T).normalized();n=Vector((u.y,-u.x));Lr=(H-T).length;LOOP=2*Lr+2*math.pi*rho
 def loop(q):
  q%=LOOP
  if q<Lr:return T+n*rho+u*q,u
  q-=Lr
  if q<math.pi*rho:t=q/rho;return H+rho*(n*math.cos(t)+u*math.sin(t)),-n*math.sin(t)+u*math.cos(t)
  q-=math.pi*rho
  if q<Lr:return H-n*rho-u*q,-u
  t=(q-Lr)/rho;return T+rho*(-n*math.cos(t)-u*math.sin(t)),n*math.sin(t)-u*math.cos(t)
 for c,name in [(T,'tail'),(H,'head')]:rod('122 %s roller'%name,(c.x,BY-.042,c.y),(c.x,BY+.042,c.y),R,steel)
 N=int(LOOP/.02);pitch=LOOP/N;slats=[]
 for i in range(N):
  o=box('193 belt slat %02d'%i,(0,BY,0),(pitch-.002,BW,.004),belt,True);o.rigid_body.kinematic=True;slats.append(o)
 prev=[None]*N
 for f in range(1,FRAMES+1):
  for i,o in enumerate(slats):
   p,t=loop(i*pitch+V*(f-1)/24);a=-math.atan2(t.y,t.x)
   if prev[i] is not None:a+=math.tau*round((prev[i]-a)/math.tau)
   prev[i]=a;o.location=(p.x,BY,p.y);o.rotation_euler[1]=a;key(o,f)
 ang=-math.atan2(u.y,u.x)
 def skirt(name,y,x0,x1):
  q0=(T.x-x0)/(T.x-H.x)*Lr;q1=(T.x-x1)/(T.x-H.x)*Lr
  c=T+n*(rho+.002+.015)+u*((q0+q1)/2)
  o=box(name,(c.x,y,c.y),(q1-q0,.004,.03),blue,True);o.rotation_euler[1]=ang
 skirt('129 outer skirt',BY+.037,T.x,H.x);skirt('129 inner skirt',BY-.037,T.x,H.x)
 # Back plate 13 mm behind the slats: a tighter gap pinched grains against the tail roller.
 box('129 tail back plate',(.932,BY,.17),(.004,BW,.05),blue,True)
 for y in [BY-.045,BY+.045]:
  o=box('120 belt side rail',((T.x+H.x)/2,y,(T.y+H.y)/2),(Lr+.03,.012,.018),wood);o.rotation_euler[1]=ang
  for x,z in [(.30,.098),(.74,.132)]:box('121 belt post',(x,y,z/2),(.02,.02,z),wood)
 box('160 M2 belt drive envelope',(.26,.45,.095),(.06,.035,.035),motor)
 def bridge_clear(f):return True
 surface_x=.90

# Grains: 120 faceted 7 mm proxies, 8 per cup passing the top (every 40 frames).
# Before release they wait, kinematic, 0.6 m straight above their spout slot (Blender
# interpolates animated bodies between frames, so a jump from under the arena swept
# through the bridge and threw grains off it; above the slot there is only air, also
# for the raised tray, whose end stops at x=.81). Then they are dropped from
# the cup spout above the bridge inlet with zero velocity. A waiting grain is solid,
# so consecutive grains use spout slots at least 25 mm apart (random spots overlapped
# the grain released just before and the solver threw them out of the arena).
grains=[];fed=[];SLOTS=[0,4,1,5,2,6,3,7]
for k in range(15):
 for j in range(8):
  r=20+40*k+2*j
  on_bridge=bridge_clear(r)
  spawn=Vector((.82+.0085*SLOTS[j],random.uniform(BY-.022,BY-.008) if on_bridge else random.uniform(.295,.305),.20))
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.0035,location=spawn+Vector((0,0,.6)))
  o=bpy.context.object;o.name='Grain proxy %03d'%len(grains);o.data.materials.append(sand)
  rigid(o,True,'CONVEX_HULL');o.rigid_body.kinematic=True
  o.keyframe_insert(data_path='location',frame=1)
  o.location=spawn;o.keyframe_insert(data_path='location',frame=r-2)
  for v,f in [(True,1),(False,r-2)]:
   o.hide_render=o.hide_viewport=v
   o.keyframe_insert(data_path='hide_render',frame=f);o.keyframe_insert(data_path='hide_viewport',frame=f)
  o.rigid_body.keyframe_insert(data_path='kinematic',frame=r-1)
  o.rigid_body.kinematic=False;o.rigid_body.keyframe_insert(data_path='kinematic',frame=r)
  grains.append((o,r));fed.append(on_bridge)
for o,r in grains:
 for fc in o.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='CONSTANT'
for o in s.objects:
 if o.name.startswith(('129 tray','151 lifting','193 belt','Wheel hub')) and o.animation_data:
  for fc in o.animation_data.action.fcurves:
   for k in fc.keyframe_points:k.interpolation='LINEAR'

title={'tilt':'TILTING BRIDGE | fill ~4 deg, tip to 35 deg','belt':'BELT BRIDGE | 0.1 m/s, 4.5 deg'}[OPTION]
text('B | DESTINATION',(.11,.07,.002));text('A | SOURCE',(.80,.07,.002));text(title,(.11,.56,.002),.019)
if OPTION=='tilt':
 for name,f in [('Fill',1),('Tip',150),('Hold - slide',198),('Return',246),('Fill',282),('Tip',420),('Hold - slide',468),('Return',516)]:s.timeline_markers.new(name,frame=f)
s.world.color=(.7,.7,.7)
bpy.ops.object.light_add(type='AREA',location=(.5,-.3,1.5));bpy.context.object.data.energy=35;bpy.context.object.data.size=1.4
bpy.ops.object.camera_add(location=(1.5,-1.5,1.35));cam=bpy.context.object
cam.rotation_euler=(Vector((.6,.3,.18))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.5;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=False
s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard'
world=s.rigidbody_world;world.substeps_per_frame=64;world.solver_iterations=30
world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
s.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT')
path=os.path.join(OUT,'bridge-%s.blend'%OPTION);bpy.ops.wm.save_as_mainfile(filepath=path)
with bpy.context.temp_override(scene=s,point_cache=world.point_cache):bpy.ops.ptcache.bake(bake=True)

# Grains far outside the arena were thrown by solver penetration, not by the mechanism.
def where(x,y,z):
 if not (-.05<x<1.25 and -.05<y<.65 and z>-.02):return 'ejected_numerical'
 if .124<x<.276 and .184<y<.416 and z<.065:return 'in_B'
 if .784<x<.966 and .209<y<.391 and z<.095:return 'in_A'
 if z<.03:return 'spilled_on_arena'
 return 'on_bridge_or_airborne'
samples=[]
for f in range(24,FRAMES+1,24):
 s.frame_set(f);deps=bpy.context.evaluated_depsgraph_get();row={'frame':f,'released':0,'in_B':0,'in_A':0,'spilled_on_arena':0,'ejected_numerical':0,'on_bridge_or_airborne':0}
 for o,r in grains:
  if r>f:continue
  row['released']+=1;row[where(*o.evaluated_get(deps).matrix_world.translation)]+=1
 samples.append(row)
report={'option':OPTION,'frames':FRAMES,'seconds':FRAMES/24,'grains':len(grains),'fed_onto_bridge':sum(fed),
 'fed_back_into_A_while_bridge_moving':len(fed)-sum(fed),'final':samples[-1],'samples':samples,
 'grain':'7 mm faceted convex hull, 0.3 g, angular damping 0.9','pair_friction':round(FRICTION*FRICTION,3),
 'feed':'prescribed: 8 grains per cup passage every 40 frames; wheel pickup NOT simulated here',
 'drive':'prescribed motion, infinite torque','cache_baked':world.point_cache.is_baked}
open(os.path.join(OUT,'bridge-%s-report.json'%OPTION),'w').write(json.dumps(report,indent=2))
for f in [140,200,300,600]:
 s.frame_set(f);s.render.filepath=os.path.join(OUT,'bridge-%s-frame-%03d.png'%(OPTION,f));bpy.ops.render.render(write_still=True)
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=path)
print('BRIDGE_REPORT',json.dumps({k:v for k,v in report.items() if k!='samples'}))
