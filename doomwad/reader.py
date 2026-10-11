"""Read-only indexed WAD access without retaining every lump payload in memory."""
from dataclasses import dataclass
from pathlib import Path
import struct

from .exceptions import InvalidWadError, LumpNotFoundError


@dataclass(frozen=True)
class LazyLump:
    name: str
    size: int
    offset: int
    reader: object

    @property
    def data(self):
        if self.reader.closed: raise ValueError('WAD reader is closed')
        if self.size == 0: return b''
        self.reader._stream.seek(self.offset)
        data=self.reader._stream.read(self.size)
        if len(data)!=self.size: raise InvalidWadError('WAD changed or was truncated during reading')
        return data


class WadReader:
    """Context-managed lazy reader. Do not mutate the file or share across threads."""
    def __init__(self,path,*,max_bytes=512*1024*1024,max_lumps=1_000_000):
        self._stream=Path(path).open('rb');self.closed=False
        try:
            size=self._stream.seek(0,2);self._stream.seek(0)
            if size>max_bytes: raise InvalidWadError('WAD exceeds configured byte limit')
            header=self._stream.read(12)
            if len(header)!=12: raise InvalidWadError('WAD header is truncated')
            kind,count,directory=struct.unpack('<4sii',header)
            if kind not in (b'IWAD',b'PWAD') or not 0<=count<=max_lumps or directory<12 or directory+count*16>size:
                raise InvalidWadError('Invalid WAD header or directory')
            self.wad_type=kind.decode();self.lumps=[]
            self._stream.seek(directory)
            for _ in range(count):
                raw=self._stream.read(16)
                if len(raw)!=16: raise InvalidWadError('Truncated WAD directory')
                offset,length,name=struct.unpack('<ii8s',raw)
                if length<0 or (length and (offset<0 or offset+length>size)):
                    raise InvalidWadError('WAD lump extends outside the file')
                self.lumps.append(LazyLump(name.split(b'\0',1)[0].decode('ascii',errors='replace'),length,offset,self))
        except BaseException:
            self.close();raise

    def __len__(self): return len(self.lumps)
    def __iter__(self): return iter(self.lumps)
    def find(self,name):
        for lump in self.lumps:
            if lump.name==name: return lump
        raise LumpNotFoundError(f'No lump named {name!r}')
    def close(self):
        self._stream.close();self.closed=True
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
