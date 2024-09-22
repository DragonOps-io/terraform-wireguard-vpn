import os
import helpers
import time
import json


def handle_stream_updates(event, context):
    print(event)
    for record in event['Records']:
        try:

            environment_map = json.loads(os.getenv('ENVIRONMENT_MAP'))
            environment_names_only = list(environment_map)
            config_files_map = helpers.get_config_files(environment_names_only)
            old_image = record['dynamodb'].get('OldImage', {})
            new_image = record['dynamodb'].get('NewImage', {})

            removed_envs, added_envs = helpers.compare_environments(old_image, new_image)
            for r in removed_envs:
                if r in config_files_map:
                    config_files_map[r] = helpers.remove_peer_section(config_files_map[r], old_image)
                else:
                    print(f'Environment {r} not found in config_files_map')
            for a in added_envs:
                if a in config_files_map:
                    config_files_map[a] = helpers.add_peer_section(config_files_map[a], new_image)
                else:
                    print(f'Environment {a} not found in config_files_map')

            if len(removed_envs) == 0 and len(added_envs) == 0:
                # This only happens when the environments haven't changed but the key has. This means it can't be a
                # new client.
                config_files_map = helpers.update_public_key(old_image, new_image, config_files_map)

            helpers.update_config_file_parameters(config_files_map)
            environment_map = helpers.send_commands(config_files_map, environment_map)
            # Need to sleep here because there is a small delay in when a command can be found after execution
            time.sleep(2)
            environment_map = helpers.check_status_of_commands(environment_map)

            failed_updates = [environment_map[k] for k, v in environment_map.items() if v["status"] != "Success"]
            successful_updates = [environment_map[k] for k, v in environment_map.items() if v["status"] == "Success"]

            print(f'\n\nThe following instance updates failed:\n{failed_updates}')
            print(f'\n\nThe following instance updates succeeded:\n{successful_updates}')

        except Exception as e:
            raise e


def add_new_client(event, context):
    # Verify public key doesn't already exist.
    public_key_exists = helpers.does_public_key_exist_already(event['public_key'])
    if public_key_exists:
        return "Public Key already exists. Please update your Client instead of adding a new one."
    taken_client_ips = helpers.get_all_taken_client_ips()
    client_ip = helpers.get_available_ip(taken_client_ips)
    helpers.add_item_to_dynamodb(client_ip, event['public_key'], event['environments'])
    return get_client_config_file({'client_ip': client_ip}, {})


def get_client_config_file(event, context):
    client_ip = event['client_ip']
    config_file = f'''\
[Interface]
PrivateKey = ReplaceWithYourPrivateKey
Address = {client_ip}
    '''

    environment_map = json.loads(os.getenv('ENVIRONMENT_MAP'))

    client_item = helpers.get_client_from_dynamodb(client_ip)
    for env in client_item.get('Environments'):
        config_file += f'''\
    
[Peer]
PublicKey = {environment_map[env]['public_key']}
AllowedIPs = {environment_map[env]['vpc_cidr']}
Endpoint = {environment_map[env]['wireguard_endpoint']}
PersistentKeepalive = 90
        '''
    print(config_file)
    return config_file


if __name__ == '__main__':
    handle_stream_updates({}, {})
