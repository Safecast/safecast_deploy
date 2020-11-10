import boto3
import os
import pprint
import sys


def ssh(aws_state, env_type, tier_type, select_instance):
    c = boto3.client('elasticbeanstalk')
    ec2_c = boto3.client('ec2')

    env_resources = c.describe_environment_resources(
        EnvironmentName=aws_state.envs[env_type][tier_type].name)['EnvironmentResources']
    instance_num = 0
    if select_instance and len(env_resources['Instances']) > 1:
        choices = ''
        for index, instance in enumerate(env_resources['Instances']):
            choices += f"{index}) {instance['Id']}\n"
        instance_num = int(input("Select from below instances:\n" + choices))

    instance_id = env_resources['Instances'][instance_num]['Id']
    instances = ec2_c.describe_instances(InstanceIds=[instance_id, ])
    public_dns = instances['Reservations'][0]['Instances'][0]['PublicDnsName']

    print(f"Connecting to {public_dns}", file=sys.stderr)
    os.execvp('ssh', ['ssh', f'ec2-user@{public_dns}', ])
