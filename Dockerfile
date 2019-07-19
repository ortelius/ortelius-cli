FROM python:3

RUN mkdir -p /opt/deployhub/scripts/deployhub
ADD https://raw.githubusercontent.com/DeployHubProject/DeployHub-Pro/master/deployhub/dhapi.py /opt/deployhub/scripts/deployhub/
ADD https://raw.githubusercontent.com/DeployHubProject/DeployHub-Pro/master/deployhub/__init__.py /opt/deployhub/scripts/deployhub/

WORKDIR /opt/deployhub/scripts
COPY *.py .

RUN pip install click qtoml requests PyYAML

CMD [ "python", "./compupdate.py" ]
