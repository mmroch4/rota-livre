"""Scoop on a string: a winch on the ground pulls a string up a tower, over two pulleys and down
to a hanging scoop in A. A servo turns the cup through the sand (like a hand), the winch lifts
it, the servo turns it left and the sand falls into the mouth of the chute to B.
Run: blender --background --python cad/build_scoop_tower.py
Metres. A and B as in README.md (A 190x190x95 at right, B 160x240x60 at left, 500 mm gap).
The tower stands behind A and the chute passes in front of it, so the mouth of the chute ends
right next to the scoop's line (3 mm clear of the cup's 43 mm turning radius). The hanger is
not guided: a short lath with the servo and ballast at the bottom keeps it upright.
Cup 70 x 60 x 50, held by the centre of its side wall on the servo horn.
Servo 180 = rest (opening right), 100 = full (opening up), 0 = dump (opening left, 10 deg down).
Solid: digging in A. See-through: raised and dumping into the mouth.
"""
import bpy, math, os
from mathutils import Vector

OUT=os.path.dirname(os.path.abspath(__file__))
SLOPE=math.radians(25)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC'

def mat(n,c,alpha=1):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,alpha);return m
wood=mat('Lath',(.57,.35,.15));blue=mat('K-line',(.13,.38,.60));cup_m=mat('Cup K-line',(.93,.93,.90))
green=mat('A source',(.12,.40,.25));grey=mat('B destination',(.45,.52,.59));sand=mat('Sand',(.91,.72,.35))
steel=mat('Steel',(.22,.25,.29));motor=mat('Servo and motor',(.9,.52,.10));ghost=mat('Raised position',(.9,.3,.2),.35)
arena=mat('Arena',(.85,.85,.82));red=mat('String',(.85,.1,.1));ink=mat('Labels',(.04,.07,.10))

def box(n,p,d,m,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p,rotation=rot);o=bpy.context.object;o.name=n;o.dimensions=d
 o.data.materials.append(m);return o
def rod(n,a,b,r,m):
 d=Vector(b)-Vector(a);bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
 o=bpy.context.object;o.name=n;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(m);return o
def text(t,p,size=.02):
 bpy.ops.object.text_add(location=p,rotation=(math.radians(70),0,0));o=bpy.context.object;o.data.body=t;o.data.size=size
 o.data.materials.append(ink)
def tray(n,x,y,l,w,h,m,t=.006):
 box(n+' floor',(x,y,t/2),(l,w,t),m)
 for a in[-1,1]:box(n+' wall x',(x+a*(l-t)/2,y,h/2),(t,w,h),m);box(n+' wall y',(x,y+a*(w-t)/2,h/2),(l,t,h),m)
def pulley(n,p,axis_x=True):
 rot=(0,math.pi/2,0) if axis_x else (math.pi/2,0,0)
 bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.015,depth=.008,location=p,rotation=rot);o=bpy.context.object;o.name=n
 o.data.materials.append(steel)

box('Arena floor',(.6,.3,-.005),(1.2,.6,.01),arena)
tray('A',.875,.30,.19,.19,.095,green);tray('B',.20,.30,.16,.24,.06,grey)
box('Sand in A',(.875,.30,.04),(.178,.178,.068),sand)

# Chute: 120 wide, from over B (x .24, floor 90 mm) up to the mouth, which ends 3 mm short of the cup.
AX=.850;X0,Z0,X1=.24,.09,.803;W=.12;L=(X1-X0)/math.cos(SLOPE);Z1=Z0+(X1-X0)*math.tan(SLOPE)
mid=Vector(((X0+X1)/2,.30,(Z0+Z1)/2));rot=(0,-SLOPE,0)
box('Chute floor',mid,(L,W,.005),blue,rot)
for a in[-1,1]:box('Chute side',mid+Vector((0,a*W/2,.015)),(L,.005,.03),blue,rot)
for a in[-1,1]:box('Mouth side',(X1-.05,.30+a*W/2,Z1+.02),(.10,.005,.07),blue)
box('Mouth end wall',(X1,.30,Z1+.0),(.005,W,.03),blue)
zc=lambda x:Z0+(x-X0)*math.tan(SLOPE)
for x in[.40,.72]:
 rod('Chute leg',(x,.30,0),(x,.30,zc(x)-.005),.01,wood)
 for a in[-1,1]:box('Leg foot',(x,.30,.006),(.012,.14,.012),wood,(0,0,a*math.radians(45)))

# Tower behind A, arm forward over the scoop line, two pulleys, winch on the ground.
TY,TH=.45,.60
box('Tower',(AX,TY,TH/2),(.025,.025,TH),wood)
for a in[-1,1]:box('Tower foot',(AX,TY,.006),(.25,.025,.012),wood,(0,0,a*math.radians(45)))
box('Arm',(AX,(TY+.285)/2,TH+.0125),(.025,TY-.285+.025,.025),wood)
pulley('Tower pulley',(AX,TY+.02,TH+.03),False);pulley('Arm-tip pulley',(AX,.30,TH-.02),False)
box('Winch motor (kit DC)',(AX+.05,TY+.06,.025),(.065,.022,.04),motor)
rod('Winch drum (dowel)',(AX-.015,TY+.06,.025),(AX+.02,TY+.06,.025),.010,steel)
rod('String drum to tower pulley',(AX,TY+.06,.035),(AX,TY+.035,TH+.03),.0015,red)
rod('String along arm',(AX,TY+.02,TH+.045),(AX,.30,TH-.005),.0015,red)
text('tower 600',(AX+.03,TY,.62));text('winch on the ground',(AX+.09,TY+.06,.06),.015)

def hanger(zc_,angle,ghosted,name):
 # zc_ = servo shaft height = cup centre. Short lath above the servo, string tied to its top.
 lm=ghost if ghosted else wood;cm=ghost if ghosted else cup_m;sm=ghost if ghosted else motor
 box(name+' servo (kit)',(AX,.30-.045,zc_),(.023,.013,.032),sm)
 box(name+' hanger lath 120',(AX,.30-.045,zc_+.016+.06),(.012,.012,.12),lm)
 box(name+' ballast (nuts)',(AX,.30-.045,zc_-.026),(.02,.014,.016),ghost if ghosted else steel)
 rod(name+' string',(AX,.30,TH-.035),(AX,.30-.045,zc_+.136),.0015,ghost if ghosted else red)
 bpy.ops.object.empty_add(location=(AX,.30,zc_));e=bpy.context.object;e.name=name+' cup axis'
 t=.004
 for n,c,d in[('bottom',(0,0,-.025+t/2),(.07,.06,t)),('wall',(-.035+t/2,0,0),(t,.06,.05)),('wall',(.035-t/2,0,0),(t,.06,.05)),
  ('side on horn',(0,-.03+t/2,0),(.07,t,.05)),('side',(0,.03-t/2,0),(.07,t,.05))]:
  o=box(name+' cup '+n,(AX+c[0],.30+c[1],zc_+c[2]),d,cm);o.parent=e;o.matrix_parent_inverse=e.matrix_world.inverted()
 e.rotation_euler=(0,angle,0)
ZTOP,ZDIG=.42,.05
hanger(ZDIG,math.radians(40),False,'Digging')
hanger(ZTOP,math.radians(-100),True,'Dumping')
for i in range(5):box('Falling sand',(.79-.004*i,.30,ZTOP-.02-.012*i),(.01,.03,.008),sand)
text('A',(.86,.18,.11));text('B',(.19,.15,.08));text('chute 25 deg',(.40,.20,.25))
text('travel %d mm'%round((ZTOP-ZDIG)*1000),(.90,.22,.30),.016)

cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam
tgt=bpy.data.objects.new('Target',None);s.collection.objects.link(tgt)
c=cam.constraints.new('TRACK_TO');c.target=tgt;c.track_axis='TRACK_NEGATIVE_Z';c.up_axis='UP_Y'
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True
s.render.resolution_x,s.render.resolution_y=1400,850
views=[('scoop-tower.png',(.20,-.80,.80),(.62,.30,.22),30),('scoop-tower-mouth.png',(.70,-.25,.55),(.83,.30,.36),45)]
for f,loc,t,lens in views:
 cam.location=loc;tgt.location=t;cam.data.lens=lens;s.render.filepath=os.path.join(OUT,f);bpy.ops.render.render(write_still=True)
cam.location,tgt.location,cam.data.lens=views[0][1],views[0][2],views[0][3]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'scoop-tower.blend'))
print('Mouth floor %.0f mm, cup centre raised %.0f mm'%(Z1*1000,ZTOP*1000))
