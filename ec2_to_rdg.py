import boto3
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from botocore.config import Config
from xml.dom import minidom

REGION = sys.argv[1]  # us-east-1, us-west-2
PROFILE = sys.argv[2]  # qa, uat, prod
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f'{PROFILE}_{REGION}_{TIMESTAMP}.rdg'
CUSTOMER = ''

FILTER_CHUNK_SIZE = 100
FOLDER_TAG_KEY = 'Customer'

ROLE_SUFFIXES = [
    '*-appserver',
    '*-processing',
    '*-gisserver',
    '*-gisserver-*',
    '*-webportal',
    '*-webportal-*',
]


def chunk_list(items, chunk_size):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def get_tag_value(instance, tag_key):
    for tag in instance.get('Tags', []):
        if tag.get('Key', '').lower() == tag_key.lower():
            return tag.get('Value')
    return None


def get_windows_instances(ec2, profile):
    """
    Retrieves Windows EC2 instances matching this profile's role patterns.
    """

    patterns = [f'{profile}-{suffix}' for suffix in ROLE_SUFFIXES]
    instances = []

    for filter_chunk in chunk_list(patterns, FILTER_CHUNK_SIZE):
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'platform', 'Values': ['windows']},
                {'Name': 'tag:Name', 'Values': filter_chunk},
                {'Name': 'instance-state-name', 'Values': ['running']},
            ]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance)

    return instances


def add_group_properties(parent, name, expanded=False):
    props = ET.SubElement(parent, 'properties')
    ET.SubElement(props, 'expanded').text = 'True' if expanded else 'False'
    ET.SubElement(props, 'name').text = name


def add_server_properties(parent, display_name, host):
    props = ET.SubElement(parent, 'properties')
    ET.SubElement(props, 'displayName').text = display_name
    ET.SubElement(props, 'name').text = host


def create_rdg_file(instances, output_file):
    """
    Creates a Remote Desktop Connection (.rdg) file, grouped by stack, with
    the provided instances.
    """

    instance_ip_dict = {}

    for instance in instances:
        if 'PublicIpAddress' not in instance:
            continue

        instance_name = get_tag_value(instance, 'Name')
        if not instance_name:
            continue

        instance_customer = get_tag_value(instance, FOLDER_TAG_KEY)

        if CUSTOMER and (instance_customer or '').lower() != CUSTOMER:
            continue

        public_ip = instance['PublicIpAddress']
        print(f'{instance_name} ({instance_customer or "NO_CUSTOMER_TAG"}) ---> {public_ip}')

        parts = instance_name.split('-')
        stack = '-'.join(parts[:2]) if len(parts) >= 2 else instance_name

        instance_ip_dict[instance_name] = {
            'ip': public_ip,
            'customer': instance_customer,
            'stack': stack,
        }

    instance_list_asc = sorted(instance_ip_dict.keys())

    stacks = {}
    for instance_name in instance_list_asc:
        stack = instance_ip_dict[instance_name]['stack']
        stacks.setdefault(stack, []).append(instance_name)

    root = ET.Element('RDCMan', {'programVersion': '2.7', 'schemaVersion': '3'})
    file_node = ET.SubElement(root, 'file')
    ET.SubElement(file_node, 'credentialsProfiles')
    add_group_properties(file_node, f'{PROFILE}_{REGION}_{TIMESTAMP}', expanded=False)

    for stack_name in sorted(stacks.keys()):
        stack_group = ET.SubElement(file_node, 'group')

        customer_values = sorted({
            instance_ip_dict[name]['customer']
            for name in stacks[stack_name]
            if instance_ip_dict[name].get('customer')
        })

        group_name = stack_name
        if customer_values:
            group_name = f'{stack_name} ({customer_values[0]})'

        add_group_properties(stack_group, group_name, expanded=False)

        for instance_name in stacks[stack_name]:
            server = ET.SubElement(stack_group, 'server')
            add_server_properties(server, instance_name, instance_ip_dict[instance_name]['ip'])

    ET.SubElement(root, 'connected')
    ET.SubElement(root, 'favorites')
    ET.SubElement(root, 'recentlyUsed')

    pretty_xml = minidom.parseString(
        ET.tostring(root, encoding='utf-8')
    ).toprettyxml(indent='  ')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)


def main():

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    boto_config = Config(retries={'max_attempts': 10, 'mode': 'standard'})

    ec2 = session.client('ec2', config=boto_config, region_name=REGION)

    # Get Windows EC2 instances matching this profile's role patterns
    instances = get_windows_instances(ec2, PROFILE)

    # Create .rdg file
    create_rdg_file(instances, OUTPUT_FILE)

    print('---SPLIT---')
    print(OUTPUT_FILE)


if __name__ == '__main__':
    main()