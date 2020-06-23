# safecast_deploy

Tooling to deploy Safecast to AWS Elastic Beanstalk and work with AWS.

## Installation

It's best if this is run in its own virtualenv. It seems that `wheel` must be installed prior to other requirements.

```
pip install wheel
pip -r requirements.txt
```

## Usage

`./deploy.py --help` will display an overview and list available commands.

Help on specific commands can be found by using `--help` with that command: `./deploy.py ssh --help`
