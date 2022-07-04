from typing import Dict, NamedTuple


AreaListItem = NamedTuple('AreaListItem',
                          [('name', str), ('count', int), ('description', str)])

FileListItem = NamedTuple('FileListItem',
                          [('name', str), ('size', int), ('description', str)])

FileAreaItem = NamedTuple('FileAreaItem',
                          [('filearea', str),
                           ('fid', str),
                           ('name', str),
                           ('size', int),
                           ('address', str),
                           ('description', str)])

AreaCount = Dict[str, int]
