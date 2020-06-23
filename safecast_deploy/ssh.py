import boto3
import os
import pprint
import sys


class Ssh:
    def __init__(self, state, args):
        self.state = state
        self.role = args.role
        self.select = args.select

    def run(self):
        c = self.state.eb_client
        ec2_c = boto3.client('ec2')
        env_resources = c.describe_environment_resources(
            EnvironmentName=self.state.env_metadata[self.state.subenvs[self.role]]['name'])['EnvironmentResources']
        if self.select and len(env_resources['Instances']) > 1:
            choices = ''
            for index, instance in enumerate(env_resources['Instances']):
                choices += "{}) {}\n".format(index, instance['Id'])
            env_num = int(input("Select from below instances:\n" + choices))
        else:
            env_num = 0
        instance_id = env_resources['Instances'][env_num]['Id']
        instances = ec2_c.describe_instances(InstanceIds=[instance_id, ])
        public_dns = instances['Reservations'][0]['Instances'][0]['PublicDnsName']
        print("Connecting to " + public_dns, file=sys.stderr)
        os.execvp('ssh', ['ssh', 'ec2-user@' + public_dns, ])
