FROM python:3

RUN mkdir -p /opt/deployhub/scripts/deployhub
ADD https://raw.githubusercontent.com/DeployHubProject/compupdate/master/deployhub/dhapi.py /opt/deployhub/scripts/deployhub/
ADD https://raw.githubusercontent.com/DeployHubProject/compupdate/master/deployhub/__init__.py /opt/deployhub/scripts/deployhub/
ADD https://raw.githubusercontent.com/DeployHubProject/compupdate/master/dh /opt/deployhub/scripts

WORKDIR /opt/deployhub/scripts

RUN pip install --upgrade pip;pip install click qtoml requests PyYAML;chmod -R 755 /opt/deployhub/scripts;

ENTRYPOINT [ "/opt/deployhub/scripts/dh" ]