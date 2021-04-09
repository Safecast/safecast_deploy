# Dockerfile for aws-cli
#
# To build:
#
#  $ docker build -f Dockerfile.aws-cli -t aws-cli:latest
#
# To run:
#
#  $ docker run --rm -it --env-file <(aws-vault exec safecast --no-session -- env | grep --color=no '^AWS_') -v $(pwd):/aws aws-cli:latest
#
# You need to run aws-vault before running.

FROM amazon/aws-cli:latest

RUN yum install git python3 python3-pip -y
RUN pip3 install cryptography==3.3.2 awsebcli --upgrade --user

RUN mkdir /src
WORKDIR /src
ADD ./requirements.txt ./deploy.py ./
ADD ./safecast_deploy ./safecast_deploy/
RUN pip3 install --requirement requirements.txt

ENTRYPOINT ["/bin/bash"]
