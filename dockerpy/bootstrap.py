#!/usr/bin/env python
import os
import boto.ec2
from configobj import ConfigObj
import time

# debug
debug = False

# get aws creds
aws_access_key_id = os.environ.get(
    'AWS_ACCESS_KEY')
aws_secret_access_key = os.environ.get(
    'AWS_SECRET_ACCESS_KEY_ID')

# connection
ec2_conn = boto.connect_vpc(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key)

# search
all_reservations = ec2_conn.get_all_instances()
all_instances = [i for r in all_reservations for i in r.instances]

# instance vars
path = os.path.dirname(os.path.realpath(__file__))
instance_cfg = ConfigObj(path + '/instance.cfg')
ami = instance_cfg['ami']
key_name = instance_cfg['key_name']
security_group_ids = [sg.strip() for sg in instance_cfg['security_group_ids'].split(',')]
subnet_id = instance_cfg['subnet_id']
placement = instance_cfg['placement']
instance_type = instance_cfg['instance_type']
instance_name = instance_cfg['instance_name']
instance_count = int(instance_cfg['instance_count']) if instance_cfg['instance_count'].isdigit() else 1
raw_tags = instance_cfg['tags'].split(',')
tags = {}
for tag in raw_tags:
    array = tag.strip().split('=')
    tags[array[0]] = array[1]

print instance_cfg

def tag_instances(instances, tags, count):
    for instance in instances:
        id_num = "{:0>2d}".format(count)
        count = count - 1
        # Check up on its status every so often
        status = instance.update()
        while status == 'pending':
            print 'waiting for ' + instance.id
            time.sleep(10)
            status = instance.update()
        if status == 'running':
            instance.add_tags(tags)
            instance.add_tag('Name', instance_name + id_num)
            print instance.tags
        else:
            print 'Instance status: ' + status


def find_instance_by_name(instances, name):
    # support short or full hostname usage
    result = []
    for i in instances:
        if "Name" in i.tags and name in i.tags['Name']:
            result.append(i)
    return result


def main():
    # create instance
    reservation = ec2_conn.run_instances(
        ami,
        key_name=key_name,
        placement=placement,
        instance_type=instance_type,
        min_count=1,
        max_count=instance_count,
        security_group_ids=security_group_ids,
        subnet_id=subnet_id,
        dry_run=debug)

    print reservation

    instances = reservation.instances
    instance_ids = [i.id for i in instances]

    count = len(find_instance_by_name(all_instances, instance_name)) + instance_count
    print 'There were ' + str(count) + ' ' + instance_name + ' already existing'
    tag_instances(instances, tags, count)


if __name__ == '__main__':
    main()
