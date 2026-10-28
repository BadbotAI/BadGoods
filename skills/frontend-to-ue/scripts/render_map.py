#!/usr/bin/env python3
"""Render an already sanitized UE model and static resources as an offline spatial canvas."""
import argparse, base64, json, math, mimetypes, re
from pathlib import Path

def safe_file(root, relative):
    path=(root/relative).resolve()
    if Path(relative).is_absolute() or root not in path.parents or not path.is_file():
        raise ValueError('Resource must be a file inside the input directory')
    return path

def validate(model):
    screens=model.get('screens',[])
    if not isinstance(screens,list) or not screens:raise ValueError('Model needs at least one screen')
    ids=[x.get('id') for x in screens]
    valid_id=lambda v:isinstance(v,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,79}',v)
    if not all(valid_id(v) for v in ids) or len(set(ids))!=len(ids):raise ValueError('Screen IDs must be safe and unique')
    routes=model.get('transitions',[]);tids=[x.get('id') for x in routes]
    if not all(valid_id(v) for v in tids) or len(set(tids))!=len(tids):raise ValueError('Transition IDs must be safe and unique')
    if any(t.get('from') not in ids or t.get('to') not in ids for t in routes):raise ValueError('Transition target is missing')
    for screen in screens:
        viewport=screen.get('viewport',model.get('viewport',{'width':1440,'height':1000}))
        for key in ['width','height']:
            v=viewport.get(key)
            if not isinstance(v,(int,float)) or not math.isfinite(v) or not 1<=v<=16384:raise ValueError('Viewport dimensions must be finite and supported')
        if 'map' in screen:
            for key,fallback in [('w',viewport['width']),('h',viewport['height'])]:screen['map'].setdefault(key,fallback)
            for key in ['x','y','w','h']:
                v=screen['map'].get(key)
                if not isinstance(v,(int,float)) or not math.isfinite(v) or (key in ['w','h'] and v<=0):raise ValueError('Map coordinates must be finite with positive size')
        for key in ['layout','rules']:
            values=screen.get('annotation',{}).get(key,[])
            if not isinstance(values,list) or not all(isinstance(v,str) for v in values):raise ValueError('Annotations must contain text lists')

def layout(model):
    screens=model['screens'];transitions=model.get('transitions',[]);groups=[]
    mods=list(dict.fromkeys(s.get('module','页面') for s in screens));some_placed=any('map' in s for s in screens)
    for name in mods:
        items=[s for s in screens if s.get('module','页面')==name];placed=[s for s in items if 'map' in s]
        if some_placed:
            edge=max((s['map']['x']+s['map']['w'] for s in placed),default=max((s['map']['x']+s['map']['w'] for s in screens if 'map'in s),default=0)+450)
            top=min((s['map']['y'] for s in placed),default=0)
            pending=[s for s in items if 'map' not in s]
            base=model.get('viewport',{'width':1440,'height':1000})
            step_w=max((s.get('viewport',base)['width'] for s in pending),default=0)+400
            step_h=max((s.get('viewport',base)['height'] for s in pending),default=0)+400
            for index,s in enumerate(pending):
                v=s.get('viewport',model.get('viewport',{'width':1440,'height':1000}));w,h=v['width'],v['height']
                s['map']={'x':edge+400+(index%3)*step_w,'y':top+(index//3)*step_h,'w':w,'h':h}
        else:
            ids={s['id'] for s in items};edges=[t for t in transitions if t['from'] in ids and t['to'] in ids and t['from']!=t['to'] and not t.get('isReturn')]
            indegree={id:sum(t['to']==id for t in edges) for id in ids};ranks={id:0 for id in ids};queue=[s['id'] for s in items if indegree[s['id']]==0]
            for id in queue:
                for t in edges:
                    if t['from']==id:
                        ranks[t['to']]=max(ranks[t['to']],ranks[id]+1);indegree[t['to']]-=1
                        if indegree[t['to']]==0:queue.append(t['to'])
            rows={};v=model.get('viewport',{'width':1440,'height':1000});step_w=max(s.get('viewport',v)['width'] for s in items)+400;step_h=max(s.get('viewport',v)['height'] for s in items)+400
            for s in items:
                col=ranks[s['id']] if indegree[s['id']]==0 else 0;row=rows.get(col,0);rows[col]=row+1;sv=s.get('viewport',v)
                s['map']={'x':col*step_w,'y':row*step_h,'w':sv['width'],'h':sv['height']}
        x=min(s['map']['x'] for s in items);y=min(s['map']['y'] for s in items)
        groups.append({'name':name,'x':x,'y':y,'w':max(s['map']['x']+s['map']['w'] for s in items)-x,'h':max(s['map']['y']+s['map']['h'] for s in items)-y,'ids':[s['id'] for s in items]})
    if not some_placed:
        target=max(max(g['w'] for g in groups),math.sqrt(sum((g['w']+600)*(g['h']+700) for g in groups)*1.6));x=y=row_h=0;by_id={s['id']:s for s in screens}
        for g in groups:
            if x and x+g['w']>target:x=0;y+=row_h+850;row_h=0
            dx,dy=x-g['x'],y-g['y']
            for sid in g['ids']:by_id[sid]['map']['x']+=dx;by_id[sid]['map']['y']+=dy
            g['x']=x;g['y']=y;x+=g['w']+850;row_h=max(row_h,g['h'])
    return groups

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input_dir',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--title');args=ap.parse_args()
    root=args.input_dir.resolve();model=json.loads((root/'ue-spec.json').read_text())
    validate(model)
    ids=[s['id'] for s in model['screens']]
    groups=layout(model);views={};thumbs={}
    for s in model['screens']:
        view=safe_file(root,s['view']).read_text()
        if re.search(r'<script\b|\son[a-z]+\s*=|javascript\s*:',view,re.I):raise ValueError('Views must be sanitized static HTML without event handlers')
        views[s['id']]=view;capture=safe_file(root,s['capture']);mime=mimetypes.guess_type(capture.name)[0]
        if mime not in ['image/png','image/jpeg','image/webp']:raise ValueError('Use PNG, JPEG or WebP captures')
        thumbs[s['id']]='data:'+mime+';base64,'+base64.b64encode(capture.read_bytes()).decode()
    data={'title':args.title or model.get('displayName','UE'),'model':model,'groups':groups,'css':safe_file(root,'screens/source.css').read_text(),'views':views,'thumbs':thumbs}
    template=(Path(__file__).resolve().parent.parent/'assets/ue-map.html').read_text()
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(template.replace('__PAYLOAD__',payload))
    print(json.dumps({'screens':len(ids),'transitions':len(model.get('transitions',[])),'standalone':True}))
if __name__=='__main__':main()
