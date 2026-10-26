"""Two-scoop grab on a swinging arm lifts sand out of A, drops it into a hopper at the top of
a fixed chute, and the chute carries it down into B. Static concept, no physics.
Run: blender --background --python cad/build_claw_chute.py
Metres. A and B as in README.md (A 190x190x95 at right, B 160x240x60 at left, 500 mm gap).
Chute at 25 deg (to be checked with the real sand and liner), so its top sits at ~300 mm and
the grab must clear ~380 mm. The arm pivot is on the perpendicular bisector between A's
centre and the drop point, so one servo swing (~57 deg) moves the grab between them.
Scoop, simplest build: a K-line cup (5 rectangles, hot glue, open top) glued to the servo horn.
The servo is glued to the bottom of a 500 mm square lath that slides in a sleeve at the arm tip,
so the lath takes the digging reaction. The winch string is tied low on the lath and runs up
over the arm-tip pulley. Dig: cup facing sideways, servo turns it upright through the sand.
Solid: digging in A. See-through: raised over the hopper, cup turned over to dump.
Front right, outside the arena: the scoop dig / hold / dump, at full scale.
"""
import bpy, bmesh, math, os
from mathutils import Vector

OUT=os.path.dirname(os.path.abspath(__file__))
SLOPE=math.radians(25)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC'

def mat(n,c,alpha=1):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,alpha);return m
wood=mat('Wood',(.57,.35,.15));ply=mat('Plywood',(.8,.60,.33));blue=mat('K-line chute',(.13,.38,.60))
green=mat('A source',(.12,.40,.25));grey=mat('B destination',(.45,.52,.59));sand=mat('Sand',(.91,.72,.35))
steel=mat('Steel',(.22,.25,.29));motor=mat('Servos and motor',(.9,.52,.10));ghost=mat('Raised position',(.9,.3,.2),.35)
arena=mat('Arena',(.85,.85,.82));ink=mat('Labels',(.04,.07,.10))

def box(n,p,d,m,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p,rotation=rot);o=bpy.context.object;o.name=n;o.dimensions=d
 o.data.materials.append(m);return o
def rod(n,a,b,r,m):
 d=Vector(b)-Vector(a);bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
 o=bpy.context.object;o.name=n;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(m);return o
def text(t,p,size=.022):
 bpy.ops.object.text_add(location=p,rotation=(math.radians(70),0,0));o=bpy.context.object;o.data.body=t;o.data.size=size
 o.data.materials.append(ink)
def tray(n,x,y,l,w,h,m,t=.006):
 box(n+' floor',(x,y,t/2),(l,w,t),m)
 for a in[-1,1]:
  box(n+' wall x',(x+a*(l-t)/2,y,h/2),(t,w,h),m);box(n+' wall y',(x,y+a*(w-t)/2,h/2),(l,t,h),m)

box('Arena floor',(.6,.3,-.005),(1.2,.6,.01),arena)
tray('A',.875,.30,.19,.19,.095,green);tray('B',.20,.30,.16,.24,.06,grey)
box('Sand in A',(.875,.30,.04),(.178,.178,.068),sand)

# Chute: 120 mm wide U-channel from the hopper (x .76) down to over B (x .24, floor at 90 mm).
X0,Z0,X1=.24,.09,.76;W=.12;L=(X1-X0)/math.cos(SLOPE);Z1=Z0+(X1-X0)*math.tan(SLOPE)
mid=Vector(((X0+X1)/2,.30,(Z0+Z1)/2));rot=(0,-SLOPE,0)
box('Chute floor',mid,(L,W,.005),blue,rot)
for a in[-1,1]:box('Chute side',mid+Vector((0,a*W/2,.015)),(L,.005,.03),blue,rot)
# Hopper at the top end: taller sides and a back wall, catches what the grab releases.
for a in[-1,1]:box('Hopper side',(.70,.30+a*W/2,Z1+.01),(.13,.005,.09),blue)
box('Hopper back wall',(X1,.30,Z1+.01),(.005,W,.09),blue)
box('Sand on chute',mid+Vector((0,0,.006)),(L*.8,.06,.006),sand,rot)
zc=lambda x:Z0+(x-X0)*math.tan(SLOPE)
for x in[.36,.62]:
 rod('Chute post',(x,.30,0),(x,.30,zc(x)-.005),.009,wood);box('Post foot',(x,.30,.003),(.08,.14,.006),ply)

cup_m=mat('Cup K-line',(.93,.93,.90))
# Mast and arm. Pivot behind A, on the bisector between A's centre (.875) and the drop point (.70).
PX,PY,ZA=.7875,.46,.52;R=math.hypot(.875-PX,.30-PY)
box('Mast foot',(PX,PY+.03,.003),(.15,.12,.006),ply);rod('Mast',(PX,PY,0),(PX,PY,ZA-.02),.012,wood)
box('Swing servo (shop 170) over a bearing',(PX,PY,ZA-.03),(.032,.016,.03),motor)
rod('Winch drum (dowel on DC motor)',(PX-.025,PY,ZA+.02),(PX+.025,PY,ZA+.02),.012,steel)
box('Winch DC motor',(PX+.045,PY,ZA+.02),(.04,.022,.02),motor)
LATH=.50
def arm(tx,ty,zp,angle,ghosted,name):
 m=ghost if ghosted else steel
 rod(name+' arm',(PX,PY,ZA),(tx,ty,ZA),.008,m)
 box(name+' lath sleeve',(tx,ty,ZA),(.03,.03,.04),ghost if ghosted else ply)
 rod(name+' string',(tx+.012,ty,ZA),(tx+.012,ty,zp+.05),.0012,m)
 scoop(tx,ty,zp,angle,ghosted,name)
def scoop(x,y,zp,angle,ghosted,name):
 # zp = servo shaft height. Cup 60 long x 70 wide x 50 deep, hinged at one top edge.
 lm=ghost if ghosted else wood;cm=ghost if ghosted else cup_m;sm=ghost if ghosted else motor
 box(name+' lath (2 x shop 121 joined)',(x-.02,y,zp+.012+LATH/2),(.015,.015,LATH),lm)
 box(name+' scoop servo (kit)',(x-.02,y-.045,zp+.004),(.032,.013,.023),sm)
 bpy.ops.object.empty_add(location=(x,y,zp));e=bpy.context.object;e.name=name+' scoop hinge'
 t=.004
 for n,c,d in[('bottom',(.03,0,-.05+t/2),(.06,.07,t)),('back wall',(t/2,0,-.025),(t,.07,.05)),
  ('front wall',(.06-t/2,0,-.025),(t,.07,.05)),('side',(.03,-.035+t/2,-.025),(.06,t,.05)),('side',(.03,.035-t/2,-.025),(.06,t,.05))]:
  o=box(name+' cup '+n,(x+c[0],y+c[1],zp+c[2]),d,cm);o.parent=e;o.matrix_parent_inverse=e.matrix_world.inverted()
 e.rotation_euler=(0,angle,0)
arm(.875,.30,.075,math.radians(80),False,'Digging')
arm(.70,.30,.44,math.radians(-100),True,'Dumping')
for i in range(5):box('Falling sand',(.66,.30,.38-.012*i),(.01,.03,.008),sand)
# Full-scale detail outside the arena: dig, hold, dump.
for k,(a,lab) in enumerate([(80,'dig'),(0,'hold'),(-100,'dump')]):
 scoop(1.02+.13*k,-.12,.07,math.radians(a),False,'Detail '+lab);text(lab,(.99+.13*k,-.17,.0),.014)

text('A 190x190x95',(.80,.18,.12));text('B 160x240x60',(.13,.15,.08))
text('chute 25 deg, 120 wide',(.38,.20,.24));text('mast 520',(.80,.48,.55))
text('arm %.0f mm, swing 57 deg'%(R*1000),(.60,.50,.60))

cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam
tgt=bpy.data.objects.new('Target',None);s.collection.objects.link(tgt)
c=cam.constraints.new('TRACK_TO');c.target=tgt;c.track_axis='TRACK_NEGATIVE_Z';c.up_axis='UP_Y'
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True
s.render.resolution_x,s.render.resolution_y=1400,850
for f,loc,t,lens in[('claw-chute.png',(.30,-.85,.75),(.66,.25,.17),30),('claw-detail.png',(1.15,-.62,.25),(1.15,-.12,.08),40)]:
 cam.location=loc;tgt.location=t;cam.data.lens=lens;s.render.filepath=os.path.join(OUT,f);bpy.ops.render.render(write_still=True)
cam.location,tgt.location,cam.data.lens=(.30,-.85,.75),(.66,.25,.17),30
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'claw-chute.blend'))
print('Chute top %.0f mm, arm %.0f mm'%(Z1*1000,R*1000))
