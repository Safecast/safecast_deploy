# safecast_deploy

Tooling to deploy Safecast to AWS Elastic Beanstalk and work with AWS. Deployments performed using this tool will create a history entry in the [deployment-history Git repository](https://github.com/Safecast/deployment-history/).

## Installation

It's best if this is run in its own virtualenv. It seems that `wheel` must be installed prior to other requirements.

```
pip install wheel
pip install --requirement requirements.txt
```

## Required credentials and permissions

* All operations require AWS credentials for our organization to be available. The easiest way to accomplish this is to configure a profile in your `~/.aws/credentials` file and point to it using an export, e.g. `export AWS_PROFILE=safecast`.
* In order to deploy a new application version, you must be able to commit to the [deployment-history Git repository](https://github.com/Safecast/deployment-history/).
* In order to ssh to an instance, you must have the Safecast SSH key.
* In order to update Grafana dashboards, you must generate and use a Grafana API key. Set `GRAFANA_API_KEY` or provide it interactively when running the `update_grafana` command.

## Usage

`./deploy.py --help` will display an overview and list available commands.

Help on specific commands can be found by using `--help` with that command: `./deploy.py ssh --help`

## Known issues

The scripts currently assume that a previous environment already exists, in all cases.

When `new_env` is called, safecast_deploy creates a new environment from the existing application configuration templates stored in Elastic Beanstalk and named `dev`, `dev-wrk`, `prd`, `prd-wrk`, etc. The `new_env` command will set a new ARN for the environment; however, that new ARN is not saved back to the application template. This is not generally a problem, especially if we continue to use this tool for all new deployments. However, it does mean that the saved template does not accurately reflect what is being run any longer. We could create a task in the future to synchronize the saved templates to what is actually running.

## Development

Unit tests can be run with `python -m unittest`.

Please run `pycodestyle` before committing.
