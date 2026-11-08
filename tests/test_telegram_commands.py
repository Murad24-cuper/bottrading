from src.db import Database
from src.notify import TelegramCommandPoller


class Response:
    status_code = 200
    def __init__(self, payload): self.payload = payload
    def json(self): return self.payload


def test_telegram_commands_are_allowlisted_confirmed_and_deduplicated(tmp_path):
    db=Database(tmp_path/'bot.db'); sent=[]
    updates=[
        {'update_id':1,'message':{'chat':{'id':'owner'},'text':'/pause'}},
        {'update_id':2,'message':{'chat':{'id':'stranger'},'text':'/stop'}},
        {'update_id':3,'message':{'chat':{'id':'owner'},'text':'/closeall'}},
        {'update_id':4,'message':{'chat':{'id':'owner'},'text':'/closeall YES'}},
    ]
    def get(*args,**kwargs): return Response({'ok':True,'result':updates})
    def post(url,**kwargs): sent.append(kwargs['json']['text']); return Response({'ok':True})
    poller=TelegramCommandPoller(db,token='fake',chat_id='owner',get=get,post=post)
    assert poller.poll_once()==2
    assert [row['command'] for row in db.get_pending_commands()] == ['pause','close_all']
    assert len(sent)==3
    assert poller.poll_once()==0
    assert len(db.get_pending_commands())==2
