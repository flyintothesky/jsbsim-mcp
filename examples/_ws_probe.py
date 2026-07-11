"""WS smoke-test probe: create session -> connect WS -> read 5 frames."""
import asyncio, websockets, json, uuid
from urllib.request import Request, urlopen

URL = 'http://127.0.0.1:7860'

def rpc(method, params, sid=None):
    req = Request(URL + '/mcp', method='POST',
                  data=json.dumps({'jsonrpc':'2.0','id':uuid.uuid4().hex,
                                   'method':method,'params':params}).encode())
    req.add_header('Content-Type','application/json')
    req.add_header('Accept','application/json, text/event-stream')
    if sid: req.add_header('Mcp-Session-Id', sid)
    with urlopen(req, timeout=30) as r:
        sid = r.headers.get('Mcp-Session-Id')
        body = r.read().decode()
    for line in body.splitlines():
        if line.startswith('data:'):
            return json.loads(line[len('data:'):].strip()), sid
    return json.loads(body), sid

async def t():
    init, mcp_sid = rpc('initialize',
        {'protocolVersion':'2025-06-18','capabilities':{},
         'clientInfo':{'name':'x','version':'0'}})
    rpc('notifications/initialized', {}, mcp_sid)
    res, _ = rpc('tools/call',
        {'name':'create_session','arguments':{'aircraft':'c172x'}},
        mcp_sid)
    sim_sid = json.loads(res['result']['content'][0]['text'])['session_id']
    print(f'created sim_sid={sim_sid}')
    rpc('tools/call',
        {'name':'step','arguments':{'session_id':sim_sid,'seconds':2.0}},
        mcp_sid)
    print(f'attempting WS connect to /ws/{sim_sid}')
    try:
        async with websockets.connect(f'ws://127.0.0.1:7860/ws/{sim_sid}') as ws:
            for i in range(5):
                msg = await asyncio.wait_for(ws.recv(), 1.5)
                d = json.loads(msg)
                print(f'  frame[{i}]: t={d["frame"]["t"]:.2f}s alt={d["frame"]["alt_ft"]:.1f}ft')
            print('WS OK')
    except Exception as e:
        print(f'WS err: {type(e).__name__}: {e}')

asyncio.run(t())
