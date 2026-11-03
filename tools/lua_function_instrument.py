"""Instrument owned Lua function definitions in a separate diagnostic copy.

The lexer leaves comments and literals opaque. A real Lua compiler must still
validate both input and result: this module is not a complete Lua parser.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import re

IDENTIFIER=re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
LONG_OPEN=re.compile(r'\[(=*)\[')


def lua_string(value: str) -> str:
    return '"'+''.join('\\%03d'%b if b<32 or b>126 else '\\'+chr(b) if b in (34,92) else chr(b) for b in value.encode('utf-8'))+'"'


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int


def tokens(source: str) -> list[Token]:
    result=[]
    i=0
    while i<len(source):
        if source[i].isspace():
            i+=1
            continue
        start=i
        comment=source.startswith('--',i)
        if comment:
            i+=2
        long=LONG_OPEN.match(source,i) if source[i:i+1]=='[' else None
        if long:
            closing=']'+long[1]+']'
            end=source.find(closing,i+len(long[0]))
            if end<0:
                raise ValueError('Unterminated long literal/comment')
            i=end+len(closing)
            continue
        if comment:
            end=source.find('\n',i)
            i=len(source) if end<0 else end+1
            continue
        if source[i] in "\"'":
            quote=source[i]
            i+=1
            while i<len(source) and source[i]!=quote:
                if source[i]=='\\':
                    escaped=source[i+1:i+2]
                    i+=2
                    if escaped=='z':
                        while i<len(source) and source[i].isspace():
                            i+=1
                    elif escaped=='\r' and source[i:i+1]=='\n':
                        i+=1
                elif source[i] in '\r\n':
                    raise ValueError('Unescaped newline in short string')
                else:
                    i+=1
            if i>=len(source):
                raise ValueError('Unterminated short string')
            i+=1
            continue
        name=IDENTIFIER.match(source,i)
        i+=len(name[0]) if name else 1
        result.append(Token(source[start:i],start,i))
    return result


def instrument(source: str,label: str) -> tuple[str,list[dict]]:
    if not isinstance(source,str) or not isinstance(label,str):
        raise ValueError('Source and label must be strings')
    ts=tokens(source)
    if any(t.value=='P6OwnWrap' for t in ts):
        raise ValueError('Diagnostic helper collides with source identifier')
    edits=[]
    stack=[]
    delimiters=[]
    manifest=[]
    newlines=[i for i,c in enumerate(source) if c=='\n']
    for index,t in enumerate(ts):
        word=t.value
        if word in ('(','[','{'):
            delimiters.append(word)
        elif word in (')',']','}'):
            if not delimiters or delimiters.pop()!= {')':'(',']':'[','}':'{'}[word]:
                raise ValueError('Unbalanced delimiter')
        if word=='function':
            j=index+1
            while j<len(ts) and ts[j].value!='(':
                j+=1
            if j>=len(ts):
                raise ValueError('Missing function parameter list')
            head=ts[index+1:j]
            name=''.join(x.value for x in head)
            if name and not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*(?::[A-Za-z_][A-Za-z_0-9]*)?',name):
                raise ValueError('Unsupported function name')
            is_local=bool(name) and index>0 and ts[index-1].value=='local'
            if is_local and ('.' in name or ':' in name):
                raise ValueError('Invalid local function name')
            line=bisect_right(newlines,t.start)+1
            title=f'{label}:{line}'+(':'+name if name else '')
            quoted=lua_string(title)
            if name:
                destination=name.replace(':','.')
                declaration=f'local {name}; ' if is_local else ''
                replacement=declaration+destination+'=P6OwnWrap('+quoted+',function'
                edits.append((ts[index-1].start if is_local else t.start,ts[j].start,replacement))
                if ':' in name:
                    prefix='self' if j+1<len(ts) and ts[j+1].value==')' else 'self,'
                    edits.append((ts[j].end,ts[j].end,prefix))
            else:
                edits.append((t.start,t.start,'P6OwnWrap('+quoted+','))
            manifest.append({'label':title,'line':line,'name':name or None,'kind':'local' if is_local else 'named' if name else 'anonymous'})
            stack.append({'kind':'function','waiting':False})
        elif word in ('if','for','while','repeat'):
            stack.append({'kind':word,'waiting':word in ('for','while')})
        elif word=='do':
            if stack and stack[-1]['waiting']:
                stack[-1]['waiting']=False
            else:
                stack.append({'kind':'do','waiting':False})
        elif word=='until':
            if not stack or stack[-1]['kind']!='repeat':
                raise ValueError('Unmatched until')
            stack.pop()
        elif word=='end':
            if not stack or stack[-1]['kind']=='repeat' or stack[-1]['waiting']:
                raise ValueError('Unmatched end or missing loop do')
            block=stack.pop()
            if block['kind']=='function':
                edits.append((t.end,t.end,')'))
    if stack or delimiters:
        raise ValueError('Unclosed block or delimiter')
    for start,end,replacement in sorted(edits,reverse=True):
        source=source[:start]+replacement+source[end:]
    return source,manifest
