import json
import random
from botocore.exceptions import ClientError
import boto3
import re
import time
import os
ssm_client = boto3.client('ssm', os.getenv('AWS_REGION', 'us-east-1'))
table_client = boto3.resource('dynamodb', os.getenv('AWS_REGION', 'us-east-1')).Table(os.getenv("DYNAMODB_TABLE_NAME", "test"))


def get_config_files(environments):
    print("get_config_files: Retrieving config files for each environment...")
    config_files = {}
    for env in environments:
        try:
            config_files[env] = ssm_client.get_parameter(
                Name=f'/{env}/wireguard/config_file',
                WithDecryption=True,
            )['Parameter']['Value']
        except Exception as e:
            raise e
    return config_files


def compare_environments(old_image, new_image):
    print("compare_environments: Finding removed and added environments for client...")
    old_environments = [obj['S'] for obj in old_image.get('Environments', {}).get('L', [])]
    new_environments = [obj['S'] for obj in new_image.get('Environments', {}).get('L', [])]
    removed = [env for env in old_environments if env not in new_environments]
    added = [env for env in new_environments if env not in old_environments]
    return removed, added


def update_public_key(old_image, new_image, config_files_map):
    print("update_public_key: Updating client public key...")
    old_public_key = old_image.get('PublicKey', {}).get('S', '')
    new_public_key = new_image.get('PublicKey', {}).get('S', '')

    if old_public_key == '':
        raise Exception("the public_key for this client is unexpectedly empty. please manually check the config")
    if old_public_key != new_public_key:
        for e in [obj['S'] for obj in new_image.get('Environments', {}).get('L', [])]:
            config_files_map[e] = update_peer_public_key(config_files_map[e], old_public_key, new_public_key)
    return config_files_map


def add_peer_section(config_str, new_image):
    print("add_peer_section: Adding peer section to config...")
    public_key = new_image.get('PublicKey', {}).get('S', '')
    client_ip = new_image.get('ClientIP', {}).get('S', '')

    # We don't want to add the peer section if public key or client_ip is an empty string
    if public_key == '' or client_ip == '':
        raise Exception("either no client_ip or public_key provided")
    if f'PublicKey = {public_key}' not in config_str:
        config_str += f'\n[Peer]\nPublicKey = {public_key}\nAllowedIPs = {client_ip}'
    return config_str


def update_peer_public_key(config_str, old_public_key, new_public_key):
    print("update_peer_public_key: Key needs updated. Updating peer public key...")
    pattern = re.compile(r'PublicKey\s*=\s*' + re.escape(old_public_key))
    updated_config_str = pattern.sub('PublicKey = ' + new_public_key, config_str)
    return updated_config_str.strip()


def remove_peer_section(config_str, old_image):
    print("remove_peer_section: Removing peer section from config...")
    public_key = old_image.get('PublicKey', {}).get('S', '')
    pattern = re.compile(
        r'\[Peer\](?:\n(?:[^\[]*\n)*?PublicKey\s*=\s*' + re.escape(public_key) + r'\n(?:.*\n)*?)(?=\[Peer\]|\Z)',
        re.MULTILINE
    )
    modified_config = pattern.sub('', config_str)
    return modified_config.strip()


def update_config_file_parameters(config_files_map):
    print("update_config_file_parameters: Updating confile file parameters with new clients...")
    try:
        print(config_files_map)
        for k, v in config_files_map.items():
            ssm_client.put_parameter(
                Name=f'/{k}/wireguard/config_file',
                Description=f'The config file for wireguard in the {k} network.',
                Value=v,
                Type='SecureString',
                Overwrite=True,
                Tier='Standard',
                DataType='text'
            )
    except Exception as e:
        raise e


def send_commands(config_files_map, instance_id_map):
    print("send_commands: Sending commands to instances...")
    for k, v in config_files_map.items():
        try:
            response = ssm_client.send_command(
                InstanceIds=[
                    instance_id_map[k]["instance_id"],
                ],
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'commands': [
                        f'config=$(aws ssm get-parameters --names /{k}/wireguard/config_file --with-decryption --query Parameters[0].Value --output text --region us-east-1)',
                        f'echo -e "$config" | sudo tee /etc/wireguard/wg0.conf > /dev/null',
                        "sudo systemctl reload wg-quick@wg0",
                        "sudo systemctl restart wg-quick@wg0",
                    ]
                }
            )
        except Exception as e:
            raise e
        instance_id_map[k]["command_id"] = response['Command']['CommandId']
    return instance_id_map


def check_status_of_commands(instance_id_map, max_depth=5, current_depth=0):
    print("check_status_of_commands: Checking command status...")

    if current_depth >= max_depth:
        print(f"Maximum recursion depth of {max_depth} reached.")
        raise Exception("too many calls to check the status")

    for k, v in instance_id_map.items():
        if "command_id" in v and v["command_id"] != "":
            try:
                response = ssm_client.get_command_invocation(
                    CommandId=v["command_id"],
                    InstanceId=v["instance_id"],
                )
            except Exception as e:
                raise e
            v['status'] = response['Status']

    while 'InProgress' in [v["status"] for k, v in instance_id_map.items() if "command_id" in v and v["command_id"] != ""]:
        time.sleep(5)
        check_status_of_commands(instance_id_map, max_depth, current_depth + 1)
    return instance_id_map


def get_all_taken_client_ips():
    response = table_client.scan()
    primary_keys = [item['ClientIP'] for item in response['Items']]

    while 'LastEvaluatedKey' in response:
        response = table_client.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        primary_keys.extend([item['ClientIP'] for item in response['Items']])

    return primary_keys


def get_available_ip(taken_ips):
    client_ip_prefix = "192.168.2"
    random_number = random.randint(5, 255)
    ip = client_ip_prefix + f".{random_number}/32"
    if is_ip_available(taken_ips, ip):
        return ip
    return get_available_ip(taken_ips)


def is_ip_available(taken_ips, ip):
    if ip in taken_ips:
        return False
    else:
        return True


def get_client_from_dynamodb(client_ip):
    response = table_client.get_item(
        Key={"ClientIP": client_ip}
    )
    item = response.get('Item')
    if not item:
        raise Exception(f"The item with client ip {client_ip} was not found.")
    return item


def add_item_to_dynamodb(client_ip, public_key, environments):
    try:
        table_client.put_item(
            Item={
                'ClientIP': client_ip,
                'PublicKey': public_key,
                'Environments': environments
            }
        )
    except ClientError as e:
        raise e


def does_public_key_exist_already(public_key):
    response = table_client.scan()
    public_keys = [item['PublicKey'] for item in response['Items']]

    while 'LastEvaluatedKey' in response:
        response = table_client.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        public_keys.extend([item['PublicKey'] for item in response['Items']])

    if public_key in public_keys:
        return True
    return False
