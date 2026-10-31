"""Read-only DWARF named-type layout comparison. No device access."""
from elftools.elf.elffile import ELFFile

def name(d):
    a=d.attributes.get('DW_AT_name')
    return a.value.decode(errors='replace') if a and isinstance(a.value,bytes) else ''
def attr(d,k):
    a=d.attributes.get(k)
    return a.value if a else None
def target(d):
    return d.get_DIE_from_attribute('DW_AT_type') if 'DW_AT_type' in d.attributes else None
def type_size(d):
    if d is None:return None
    if attr(d,'DW_AT_byte_size') is not None:return attr(d,'DW_AT_byte_size')
    return type_size(target(d))
def token(d,depth=0):
    if d is None:return 'void'
    if depth>12:return 'depth-bound'
    n=name(d);tag=d.tag.removeprefix('DW_TAG_')
    if tag in ('structure_type','union_type','enumeration_type'):
        if n:return tag+' '+n
        return {'kind':tag,'members':members(d,depth+1)}
    if tag=='array_type':return {'array':token(target(d),depth+1),'bounds':[(attr(x,'DW_AT_count') or None,attr(x,'DW_AT_upper_bound')) for x in d.iter_children() if x.tag=='DW_TAG_subrange_type']}
    if tag=='subroutine_type':return {'result':token(target(d),depth+1),'args':[token(target(x),depth+1) for x in d.iter_children() if x.tag=='DW_TAG_formal_parameter']}
    if tag=='base_type':return {'base':n,'bytes':attr(d,'DW_AT_byte_size'),'encoding':attr(d,'DW_AT_encoding')}
    return {'kind':tag,'name':n,'type':token(target(d),depth+1)}
def members(d,depth=0):
    result=[]
    for x in d.iter_children():
        if x.tag!='DW_TAG_member':continue
        offset=attr(x,'DW_AT_data_member_location');bits=attr(x,'DW_AT_bit_size');bit_offset=None
        if bits is not None:
            absolute=attr(x,'DW_AT_data_bit_offset')
            if absolute is None and offset is not None and attr(x,'DW_AT_bit_offset') is not None:
                size=attr(x,'DW_AT_byte_size') or type_size(target(x))
                absolute=offset*8+size*8-attr(x,'DW_AT_bit_offset')-bits
            if absolute is not None:offset,bit_offset=divmod(absolute,8)
        result.append({'name':name(x),'offset':offset,'bits':bits,'bit_offset':bit_offset,'type':token(target(x),depth+1)})
    return result
def inventory(path):
    with path.open('rb') as f:
        dwarf=ELFFile(f).get_dwarf_info();types={};duplicates=[]
        for cu in dwarf.iter_CUs():
            for d in cu.iter_DIEs():
                if d.tag is None:continue
                n=name(d);tag=d.tag.removeprefix('DW_TAG_')
                if not n or tag not in ('structure_type','union_type','enumeration_type') or attr(d,'DW_AT_declaration'):continue
                desc={'kind':tag,'bytes':attr(d,'DW_AT_byte_size')}
                if tag=='enumeration_type':desc['values']=[(name(x),attr(x,'DW_AT_const_value')) for x in d.iter_children() if x.tag=='DW_TAG_enumerator']
                else:desc['members']=members(d)
                if n in types and types[n]!=desc:duplicates.append(n)
                types[n]=desc
        return types,sorted(set(duplicates))
def diff(a,b):return {n:{'old':a[n],'candidate':b[n]} for n in sorted(a.keys()&b.keys()) if a[n]!=b[n]}
