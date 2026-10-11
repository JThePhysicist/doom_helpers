"""Map-scoped standard Doom editing. Node generation delegates to external tools."""
from pathlib import Path
import subprocess
import struct
import tempfile

from .maps import Thing, Linedef, Sidedef, Vertex, Sector, is_map_marker, MAP_LUMP_NAMES
from ..exceptions import DoomWadError

RECORDS={'THINGS':Thing,'LINEDEFS':Linedef,'SIDEDEFS':Sidedef,'VERTEXES':Vertex,'SECTORS':Sector}
GEOMETRY={'VERTEXES','LINEDEFS','SIDEDEFS'}
GENERATED={'SEGS','SSECTORS','NODES','BLOCKMAP','REJECT'}


class DoomMap:
    def __init__(self, wad, name):
        self.wad=wad
        matches=[i for i,lump in enumerate(wad.lumps) if lump.name==name]
        if not is_map_marker(name) or len(matches)!=1:
            raise DoomWadError('Map marker must exist exactly once')
        self.start=matches[0]
        self.end=next((i for i in range(self.start+1,len(wad.lumps)) if is_map_marker(wad.lumps[i].name)),len(wad.lumps))
        self.name=name
        self.geometry_dirty=False
        if any(lump.name in ('TEXTMAP','BEHAVIOR') for lump in wad.lumps[self.start+1:self.end]):
            raise DoomWadError('Hexen and UDMF maps require separate format support')

    def lump(self,name):
        matches=[lump for lump in self.wad.lumps[self.start+1:self.end] if lump.name==name]
        if len(matches)!=1:
            raise DoomWadError(f'Map {self.name} requires exactly one {name} lump')
        return matches[0]

    def records(self,name):
        if name not in RECORDS: raise DoomWadError(f'Unsupported map record {name}')
        try: return RECORDS[name].list_from_bytes(self.lump(name).data)
        except (ValueError, struct.error) as exc:
            raise DoomWadError(f'Invalid {name} records in {self.name}: {exc}') from exc

    def replace_records(self,name,records):
        if name not in RECORDS: raise DoomWadError(f'Unsupported map record {name}')
        data=RECORDS[name].list_to_bytes(records)
        self.lump(name).data=data
        if name in GEOMETRY or name=='SECTORS': self.geometry_dirty=True

    def validate(self):
        vertices=self.records('VERTEXES'); sides=self.records('SIDEDEFS'); sectors=self.records('SECTORS')
        for line in self.records('LINEDEFS'):
            if not 0<=line.start_vertex<len(vertices) or not 0<=line.end_vertex<len(vertices):
                raise DoomWadError('Linedef vertex reference is out of range')
            if not 0<=line.front_sidedef<len(sides) or not (line.back_sidedef==-1 or 0<=line.back_sidedef<len(sides)):
                raise DoomWadError('Linedef sidedef reference is out of range')
        if any(not 0<=side.sector<len(sectors) for side in sides):
            raise DoomWadError('Sidedef sector reference is out of range')
        self.records('THINGS')

    def save(self,path):
        self.validate()
        if self.geometry_dirty:
            raise DoomWadError('Geometry changed; rebuild nodes, BLOCKMAP, and REJECT before saving')
        self.wad.save(path)

    def rebuild_nodes(self,command):
        """Run an explicit argv command; substitute {wad} for a temporary WAD path.

        The external builder must update that WAD in place and regenerate all
        derived geometry. Output is validated before any original lumps change.
        """
        if not command or not any('{wad}' in arg for arg in command):
            raise DoomWadError('Node builder command must include a {wad} path argument')
        from ..wad import Wad
        self.validate()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'map.wad';self.wad.save(path)
            subprocess.run([arg.replace('{wad}',str(path)) for arg in command],check=True)
            rebuilt=Wad.load(path)
            replacement=DoomMap(rebuilt,self.name);replacement.validate()
            # Builders may add split vertices as well as regenerate derived data.
            regenerated={name:replacement.lump(name).data for name in MAP_LUMP_NAMES}
            for name in MAP_LUMP_NAMES: self.lump(name)  # validate target before mutation
            for name,data in regenerated.items(): self.lump(name).data=data
        self.geometry_dirty=False
