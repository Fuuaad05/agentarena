import json
from unittest.mock import patch
from backend.research.tavily_research import TavilyResearch
class Response:
    def __init__(self,value):self.value=value
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return json.dumps(self.value).encode()

def test_no_key_makes_no_network_call(monkeypatch):
    monkeypatch.delenv('TAVILY_API_KEY',raising=False)
    with patch('urllib.request.urlopen') as request:
        assert TavilyResearch().search('redirect','private report')['status']=='disabled'
        request.assert_not_called()

def test_redirect_primary_sources_and_cache(monkeypatch,tmp_path):
    monkeypatch.setenv('TAVILY_API_KEY','test-only')
    monkeypatch.setattr('backend.research.tavily_research.CACHE_DIRECTORY',tmp_path)
    raw={'results':[{'title':'Python 3.11','url':'https://docs.python.org/3.11/library/urllib.parse.html','content':'An absolute URL may replace the base origin.'},{'url':'https://example.com/blog','content':'Untrusted'},{'url':'https://docs.python.org/3.15/library/urllib.parse.html','content':'Wrong version'}]}
    captured=[]
    def response(req,**kwargs):captured.append(json.loads(req.data));return Response(raw)
    with patch('urllib.request.urlopen',side_effect=response) as request:
        first=TavilyResearch().search('redirect','SECRET_REPORT')
        second=TavilyResearch().search('redirect','SECRET_REPORT')
    assert len(first['sources'])==1 and first['sources'][0]['id']=='S1'
    assert captured[0]['include_domains']==['docs.python.org'] and 'SECRET_REPORT' not in str(captured)
    assert second['cached'] and request.call_count==1

def test_research_failure_is_explicit(monkeypatch,tmp_path):
    monkeypatch.setenv('TAVILY_API_KEY','test-only')
    monkeypatch.setattr('backend.research.tavily_research.CACHE_DIRECTORY',tmp_path)
    with patch('urllib.request.urlopen',side_effect=TimeoutError('offline')):
        result=TavilyResearch().search('redirect','test')
    assert result['status']=='failed' and not result['sources']

def test_empty_search_extracts_exact_version(monkeypatch,tmp_path):
    monkeypatch.setenv('TAVILY_API_KEY','test-only')
    monkeypatch.setattr('backend.research.tavily_research.CACHE_DIRECTORY',tmp_path)
    url='https://docs.python.org/3.11/library/urllib.parse.html'
    replies=iter([Response({'results':[]}),Response({'results':[{'url':url,'raw_content':'It is not secure to use urljoin with an attacker-controlled URL.'}]})])
    calls=[]
    def reply(request,**kwargs):calls.append(request);return next(replies)
    with patch('urllib.request.urlopen',side_effect=reply):
        result=TavilyResearch().search('redirect','private')
    assert result['status']=='completed' and result['sources'][0]['url']==url
    assert calls[1].full_url=='https://api.tavily.com/extract'
    assert json.loads(calls[1].data)['urls']==[url]

def test_empty_research_is_not_cached(monkeypatch,tmp_path):
    monkeypatch.setenv('TAVILY_API_KEY','test-only')
    monkeypatch.setattr('backend.research.tavily_research.CACHE_DIRECTORY',tmp_path)
    with patch('urllib.request.urlopen',return_value=Response({'results':[]})):
        result=TavilyResearch().search('redirect','private')
    assert result['status']=='no_results' and result['error']
    assert not list(tmp_path.glob('*.json'))

def test_redirect_changelog_does_not_block_exact_page_extraction(monkeypatch,tmp_path):
    monkeypatch.setenv('TAVILY_API_KEY','test-only')
    monkeypatch.setattr('backend.research.tavily_research.CACHE_DIRECTORY',tmp_path)
    url='https://docs.python.org/3.11/library/urllib.parse.html'
    replies=iter([Response({'results':[{'url':'https://docs.python.org/3.11/whatsnew/changelog.html','content':'Generic changes'}]}),Response({'results':[{'url':url,'raw_content':'It is not secure to use urljoin with an attacker-controlled URL.'}]})])
    with patch('urllib.request.urlopen',side_effect=lambda *args,**kwargs:next(replies)) as request:
        result=TavilyResearch().search('redirect','private')
    assert request.call_count==2
    assert result['sources'][0]['url']==url

def test_callback_extracts_behavior_specific_passage(monkeypatch,tmp_path):
    monkeypatch.setenv('TAVILY_API_KEY','test-only')
    monkeypatch.setattr('backend.research.tavily_research.CACHE_DIRECTORY',tmp_path)
    url='https://docs.python.org/3.11/library/urllib.parse.html'
    raw='General module introduction. '*90+'urllib.parse.parse_qsl(qs, keep_blank_values=False) The default means blank values are to be ignored and omitted.'+' Further details.'*80
    replies=iter([Response({'results':[]}),Response({'results':[{'url':url,'raw_content':raw}]})])
    with patch('urllib.request.urlopen',side_effect=lambda *args,**kwargs:next(replies)):
        result=TavilyResearch().search('callback','private payment detail')
    assert result['status']=='completed'
    assert 'blank values are to be ignored' in result['sources'][0]['content']
    assert 'private payment detail' not in result['query']

def test_old_unscoped_cache_is_ignored(monkeypatch,tmp_path):
    import time
    monkeypatch.setattr('backend.research.tavily_research.CACHE_DIRECTORY',tmp_path)
    service=TavilyResearch()
    service._write_cache('legacy',{'fetched_at':time.time(),'sources':[{'id':'S1','content':'old parse_qs section'}]})
    assert service._read_cache('legacy') is None
