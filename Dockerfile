# WIP
FROM python:3.7
COPY requirements.txt .
RUN pip install -r requirements.txt
ADD . /dogkop
CMD ["kopf", "run", "dogkop.py"]