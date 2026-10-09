import importlib, importlib.abc, importlib.util, importlib.metadata as md, sys
class CompatGapError(ImportError): pass
class _AliasLoader(importlib.abc.Loader):
    def __init__(s,n): s.n=n
    def create_module(s,spec): return importlib.import_module(s.n)
    def exec_module(s,m): pass
class Dist(md.Distribution):
    def __init__(s,name,ver): s._t={"METADATA":f"Metadata-Version: 2.1\nName: {name}\nVersion: {ver}\n"}
    def read_text(s,f): return s._t.get(f)
    def locate_file(s,p): return p
class AliasFinder(importlib.abc.MetaPathFinder):
    def __init__(s,owned,ver): s.o=owned; s.v=ver
    def find_spec(s,full,path=None,target=None):
        for up,nat in s.o.items():
            if full==up or full.startswith(up+"."):
                nn=nat+full[len(up):]
                ns=importlib.util.find_spec(nn)
                if ns is None: raise CompatGapError(f"{full}: not provided (matrix row: blocked)")
                return importlib.util.spec_from_loader(full,_AliasLoader(nn),is_package=ns.submodule_search_locations is not None)
    def find_distributions(s,context=md.DistributionFinder.Context()):
        if context.name in (None,*s.o): return iter([Dist(n,s.v) for n in s.o if context.name in (None,n)])
        return iter([])
def activate(owned,ver):
    for up in owned:
        if any(k==up or k.startswith(up+".") for k in sys.modules): raise RuntimeError(f"late activation: {up} already imported")
    sys.meta_path.insert(0,AliasFinder(owned,ver))
sys.path.insert(0,"pkg")
activate({"fakegraph":"orama_native.fakegraph"},"1.0.3+orama.1")
import fakegraph, fakegraph.graph
from fakegraph.graph import StateGraph
import orama_native.fakegraph.graph as N
print("same module object:", fakegraph.graph is N, "| class identity:", StateGraph is N.StateGraph, "| pkg:", fakegraph.VERSION)
try:
    from fakegraph.types import Send
except ImportError as e: print("gap caught by except ImportError:", type(e).__name__)
print("metadata version:", md.version("fakegraph"))
from packaging.specifiers import SpecifierSet
v="1.0.3+orama.1"; print("==1.0.3:", v in SpecifierSet("==1.0.3"), "| >=1.0:", v in SpecifierSet(">=1.0"), "| <1.0.4:", v in SpecifierSet("<1.0.4"))
try: activate({"fakegraph":"x"},"0")
except RuntimeError as e: print("refused:", e)
