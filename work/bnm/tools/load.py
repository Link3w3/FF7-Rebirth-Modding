import sys, json
sys.path.insert(0,'/work/cs'); sys.path.insert(0,'/work/bnm/tools')
from legacy import Legacy
from tagged import Reader, read_props
ROOT='/work/bnm/Content/Character/Player/'
def load(rel):
    L=Legacy(open(ROOT+rel+'.uasset','rb').read(), open(ROOT+rel+'.uexp','rb').read())
    objs=[]
    for ei in range(len(L.exports)):
        d=L.export_data(ei); r=Reader(d, L.names); objs.append(read_props(r))
    return L, objs
