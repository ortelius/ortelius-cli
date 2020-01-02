FROM python:3

RUN mkdir -p /opt/deployhub/scripts/deployhub
ADD https://raw.githubusercontent.com/DeployHubProject/compupdate/master/deployhub/dhapi.py /opt/deployhub/scripts/deployhub/
ADD https://raw.githubusercontent.com/DeployHubProject/compupdate/master/deployhub/__init__.py /opt/deployhub/scripts/deployhub/
ADD https://raw.githubusercontent.com/DeployHubProject/compupdate/master/compupdate.py /opt/deployhub/scripts

WORKDIR /opt/deployhub/scripts

RUN pip install click qtoml requests PyYAML

ENTRYPOINT [ "python3", "/opt/deployhub/scripts/compupdate.py" ]
