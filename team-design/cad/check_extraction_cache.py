import bpy, json, os
s=bpy.context.scene
rows=[]
for f in [175,176,180,195,360]:
 s.frame_set(f);deps=bpy.context.evaluated_depsgraph_get()
 points=[tuple(o.evaluated_get(deps).matrix_world.translation) for o in s.objects if o.name.startswith('Sand proxy')]
 rows.append({'frame':f,'inside_B':sum(.124<x<.276 and .184<y<.416 and .006<z<.06 for x,y,z in points),'x_range':[min(p[0] for p in points),max(p[0] for p in points)]})
print('REOPEN_CHECK',json.dumps({'baked':s.rigidbody_world.point_cache.is_baked,'frames':rows}))
