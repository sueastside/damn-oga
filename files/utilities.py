from urlparse import urlparse
from celery.result import AsyncResult

def is_oga_url(url):
    parsed_uri = urlparse(url)
    return parsed_uri.netloc == 'opengameart.org'
 

def get_asset(job, file_hash, subname, mimetype):
    descriptions = []
    assets = []
    for result in job.result:
        descriptions.extend(result.get().values())
    for description in descriptions:
        for asset in description.assets:
            if description.file.hash == file_hash and asset.asset.subname == subname and asset.asset.mimetype == mimetype:
                return True, description, asset.asset
            assets.append(asset.asset)
    return False, None, assets


def schedule(task_id, func , request):
    job = AsyncResult(task_id)
    if request.GET.get('force', False) and job.state != 'QUEUED':
        job.forget()
        
    if job.state == 'PENDING':
        print 'SCHEDULE', job.state, 'executing task'
        job = func()
    elif job.state == 'QUEUED':
        from celery.task.control import inspect
        i = inspect()
        task_ids = []
        for workers in [i.active(), i.reserved()]:
            for worker, tasks in workers.items():
                task_ids.extend([task['id'] for task in tasks])
        if task_id not in task_ids:
            print 'SCHEDULE', job.state, 'executing task'
            job = func()
    else:
        print 'SCHEDULE', job.state, 'already there'
    return job
