from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper

from files.utilities import is_oga_url, get_asset, schedule

from django.conf import settings

import os
import json

from damn_celery import tasks
from celery.result import AsyncResult


def index(request):
    return render(request, 'index.html')


def capabilities(request):
    from damn_at import Analyzer
    analyzer = Analyzer()
    data = {}
    data['mimetypes'] = analyzer.get_supported_mimetypes()
    data['capabilities'] = analyzer.get_supported_metadata()
            
    return HttpResponse(json.dumps(data, indent=4), content_type="application/json")        


def analyzed(request):
    from damn_celery import tasks
    keys = tasks.app.backend.client.keys('*')
    return HttpResponse(json.dumps(keys, indent=4), content_type="application/json")


def analyze(request):
    url = request.GET.get('url', False)
    if not url or not is_oga_url(url):
        return HttpResponse('Not a valid url', status=400)

    job = schedule(url, lambda: tasks.oga(url, task_id=url), request)
    stats, ready = tasks.collect_stats(job.id)
    
    if ready:
        job = AsyncResult(job.id)        
        return HttpResponse(json.dumps(stats, indent=4), content_type="application/json")
    else:
        return HttpResponse(json.dumps(stats, indent=4), content_type="application/json")


def transcode(request):
    url = request.GET.get('url', False)
    if not url or not is_oga_url(url):
        return HttpResponse('Not a valid url', status=400)
        
    file_hash = request.GET.get('hash', False)
    mimetype = request.GET.get('mimetype', False)
    subname = request.GET.get('subname', False)
    
    job = AsyncResult(url)
    if job.successful() and job.result.successful():
        found, file_descr, asset = get_asset(job, file_hash, subname, mimetype)
        if found:
            task_id = url+file_hash+mimetype+subname+'preview'
            job = schedule(task_id, lambda: tasks.generate_preview((file_descr, asset), {'path': '/tmp/transcoded'}, task_id=task_id), request)
                
            if job.state == 'SUCCESS' and job.result:
                data = job.result
            elif job.state == 'FAILURE' and job.result:
                data = str(job.result)
            else:
                data = job.state
            data = {'state': job.state, 'result': data}
            return HttpResponse(json.dumps(data, indent=4), content_type="application/json")
        else:
            data = {'Error': 'Combination of hash, mimetype, subname not found!'}
            if settings.DEBUG:
                from thrift.protocol.TJSONProtocol import TSimpleJSONProtocol
                from damn_at.serialization import SerializeThriftMsg
                data['assets'] = [json.loads(SerializeThriftMsg(ass, TSimpleJSONProtocol)) for ass in asset]
            return HttpResponse(json.dumps(data, indent=4), content_type="application/json", status=400)
    else:
        return HttpResponse('wait for it!', status=400)


def download(request):
    url = request.GET.get('url', False)
    if not url or not is_oga_url(url):
        return HttpResponse('Not a valid url', status=400)
        
    file_hash = request.GET.get('hash', False)
    
    job = AsyncResult(url)
    if job.successful() and job.result.successful():
        descriptions = []
        found = False
        for result in job.result:
            descriptions.extend(result.get().values())
        for description in descriptions:
            for asset in description.assets:
                if description.file.hash == file_hash:
                    found = description
                    break
        if found:
            print 'streaming', found.file.filename
            filename = found.file.filename                          
            wrapper = FileWrapper(file(filename))
            response = HttpResponse(wrapper, content_type='application/octet-stream')
            response['Content-Length'] = os.path.getsize(filename)
            response['Content-Disposition'] = 'attachment; filename='+os.path.basename(filename)
            return response
        else:
            data = {'Error': 'Hash not found!'}
            if settings.DEBUG:
                from thrift.protocol.TJSONProtocol import TSimpleJSONProtocol
                from damn_at.serialization import SerializeThriftMsg
                data['assets'] = [json.loads(SerializeThriftMsg(ass, TSimpleJSONProtocol)) for ass in asset]
            return HttpResponse(json.dumps(data, indent=4), content_type="application/json", status=400)
    else:
        return HttpResponse('wait for it!', status=400)


def reset(request):
    #tasks.app.backend.client.flushdb()
    import shutil

    for path in ['/tmp/transcoded/*', '/tmp/oga/*']:
        if os.path.exists(path):
            shutil.rmtree(path)
    
    jobs = {}
    keys = tasks.app.backend.client.keys('*')
    for key in keys:
        if key.startswith('celery-task-meta-'):
            key = key.split('celery-task-meta-')[1]
            print 'FORGETTING', key
            job = AsyncResult(key)
            jobs[key] = job.state
            job.forget()
            
    data = {'state': 'cleared', 'jobs': jobs}
    return HttpResponse(json.dumps(data, indent=4), content_type="application/json", status=200)
    
