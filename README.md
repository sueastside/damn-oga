damn-oga
==========

A web serivce to provide analyzing and transcoding of OpenGameArt content by URL.


![preview](https://raw.githubusercontent.com/sueastside/damn-oga/master/preview.png)

Running
=======
Run the celery worker:
 ```
    celery worker --app=damn_celery -l info --autoreload
 ```
 
Start the service
 ```
    python manage.py runserver
 ```
