import unittest
import helpers
from unittest.mock import patch, MagicMock


class TestGetConfigFiles(unittest.TestCase):
    @patch('helpers.ssm_client')
    def test_get_config_files_success(self, mock_ssm_client):
        # Arrange
        environments = ['dev', 'prod']
        expected_config_files = {
            'dev': 'dev_config_content',
            'prod': 'prod_config_content',
        }

        # Mock the return value of ssm_client.get_parameter for each environment
        mock_ssm_client.get_parameter.side_effect = [
            {'Parameter': {'Value': 'dev_config_content'}},
            {'Parameter': {'Value': 'prod_config_content'}}
        ]

        # Act
        result = helpers.get_config_files(environments)

        # Assert
        self.assertEqual(result, expected_config_files)
        mock_ssm_client.get_parameter.assert_any_call(Name='/dev/wireguard/config_file', WithDecryption=True)
        mock_ssm_client.get_parameter.assert_any_call(Name='/prod/wireguard/config_file', WithDecryption=True)
        self.assertEqual(mock_ssm_client.get_parameter.call_count, 2)

    @patch('helpers.ssm_client')
    def test_get_config_files_failure(self, mock_ssm_client):
        # Arrange
        environments = ['dev', 'prod']
        mock_ssm_client.get_parameter.side_effect = Exception("SSM Error")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            helpers.get_config_files(environments)

        self.assertEqual(str(context.exception), "SSM Error")
        mock_ssm_client.get_parameter.assert_called_once_with(Name='/dev/wireguard/config_file', WithDecryption=True)


class TestCompareEnvironments(unittest.TestCase):
    def test_compare_environments_no_changes(self):
        old_image = {'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        new_image = {'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}

        removed, added = helpers.compare_environments(old_image, new_image)

        self.assertEqual(removed, [])
        self.assertEqual(added, [])

    def test_compare_environments_removed_environment(self):
        old_image = {'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        new_image = {'Environments': {'L': [{'S': 'dev'}]}}

        removed, added = helpers.compare_environments(old_image, new_image)

        self.assertEqual(removed, ['prod'])
        self.assertEqual(added, [])

    def test_compare_environments_added_environment(self):
        old_image = {'Environments': {'L': [{'S': 'dev'}]}}
        new_image = {'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}

        removed, added = helpers.compare_environments(old_image, new_image)

        self.assertEqual(removed, [])
        self.assertEqual(added, ['prod'])

    def test_compare_environments_added_and_removed(self):
        old_image = {'Environments': {'L': [{'S': 'dev'}, {'S': 'staging'}]}}
        new_image = {'Environments': {'L': [{'S': 'prod'}, {'S': 'dev'}]}}

        removed, added = helpers.compare_environments(old_image, new_image)

        self.assertEqual(removed, ['staging'])
        self.assertEqual(added, ['prod'])

    def test_compare_environments_empty_old_image(self):
        old_image = {'Environments': {'L': []}}
        new_image = {'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}

        removed, added = helpers.compare_environments(old_image, new_image)

        self.assertEqual(removed, [])
        self.assertEqual(added, ['dev', 'prod'])

    def test_compare_environments_empty_new_image(self):
        old_image = {'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        new_image = {'Environments': {'L': []}}

        removed, added = helpers.compare_environments(old_image, new_image)

        self.assertEqual(removed, ['dev', 'prod'])
        self.assertEqual(added, [])


class TestUpdatePeerPublicKey(unittest.TestCase):
    def test_update_peer_public_key_no_change(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820
PostUp = wg set %i private-key /etc/wireguard/privatekey

[Peer]
PublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.1/32

[Peer]
PublicKey = 1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.2/32
"""

        expected_config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820
PostUp = wg set %i private-key /etc/wireguard/privatekey

[Peer]
PublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.1/32

[Peer]
PublicKey = 1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.2/32
"""
        old_public_key = "1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+="
        new_public_key = "1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+="  # No change
        result = helpers.update_peer_public_key(config_str, old_public_key, new_public_key)

        self.assertEqual(result.strip(), expected_config_str.strip())

    def test_update_peer_public_key_single_peer(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820
PostUp = wg set %i private-key /etc/wireguard/privatekey

[Peer]
PublicKey = 1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.1/32
"""
        old_public_key = "1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+="
        new_public_key = "9876nr5ETQ/evj5fUk5huzk+qkvoJ1+="
        expected_result = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820
PostUp = wg set %i private-key /etc/wireguard/privatekey

[Peer]
PublicKey = 9876nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.1/32
"""
        result = helpers.update_peer_public_key(config_str, old_public_key, new_public_key)

        self.assertEqual(result.strip(), expected_result.strip())

    def test_update_peer_public_key_multiple_peers(self):
        config_str = """
[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.2/32

[Peer]
PublicKey = 9876nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.3/32
"""
        old_public_key = "9876nr5ETQ/evj5fUk5huzk+qkvoJ1+="
        new_public_key = "1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+="
        expected_result = """
[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.2/32

[Peer]
PublicKey = 1234/nr5ETQ/evj5fUk5huzk+qkvoJ1+=
AllowedIPs = 10.0.0.3/32
"""
        result = helpers.update_peer_public_key(config_str, old_public_key, new_public_key)

        self.assertEqual(result.strip(), expected_result.strip())

    def test_update_peer_public_key_no_match(self):
        config_str = """
[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.1/32
"""
        old_public_key = "old_key"  # Key does not exist in the config
        new_public_key = "new_key"
        result = helpers.update_peer_public_key(config_str, old_public_key, new_public_key)

        # The config should remain unchanged because the old_public_key wasn't found
        self.assertEqual(result.strip(), config_str.strip())

    def test_update_peer_public_key_partial_match(self):
        config_str = """
[Peer]
PublicKey = old_key
AllowedIPs = 10.0.0.1/32
"""
        old_public_key = "old_key_partial"
        new_public_key = "new_key"
        result = helpers.update_peer_public_key(config_str, old_public_key, new_public_key)

        # The config should remain unchanged because the full old_public_key wasn't found
        self.assertEqual(result.strip(), config_str.strip())


class TestUpdatePublicKey(unittest.TestCase):
    def test_update_public_key_no_change(self):
        old_image = {'PublicKey': {'S': 'QzGaKVm6zB+Z0rusOiP+dEKdhyc+='}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        new_image = {'PublicKey': {'S': 'QzGaKVm6zB+Z0rusOiP+dEKdhyc+='}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        config_files_map = {
            'dev': '[Interface]\nAddress = 192.168.0.1/24\nListenPort = 51820\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = QzGaKVm6zB+Z0rusOiP+dEKdhyc+=\nAllowedIPs = 192.168.0.4/32',
            'prod': '[Interface]\nAddress = 192.168.0.2/24\nListenPort = 51821\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = QzGaKVm6zB+Z0rusOiP+dEKdhyc+=\nAllowedIPs = 192.168.0.4/32'
        }

        expected_result = {
            'dev': '[Interface]\nAddress = 192.168.0.1/24\nListenPort = 51820\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = QzGaKVm6zB+Z0rusOiP+dEKdhyc+=\nAllowedIPs = 192.168.0.4/32',
            'prod': '[Interface]\nAddress = 192.168.0.2/24\nListenPort = 51821\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = QzGaKVm6zB+Z0rusOiP+dEKdhyc+=\nAllowedIPs = 192.168.0.4/32'
        }

        result = helpers.update_public_key(old_image, new_image, config_files_map)

        self.assertEqual(result, expected_result)

    def test_update_public_key_changed_key(self):
        old_image = {'PublicKey': {'S': 'QzGaKVm6zB+Z0rusOiP+dEKdhyc+dzOEWhD7ZowV3k4='}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        new_image = {'PublicKey': {'S': 'NaGaKVm6zB+Z0rusOiP+dEKdhyc+dzOEWhD7ZowV3k4='}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        config_files_map = {
            'dev': '[Interface]\nAddress = 192.168.0.1/24\nListenPort = 51820\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = QzGaKVm6zB+Z0rusOiP+dEKdhyc+dzOEWhD7ZowV3k4=\nAllowedIPs = 192.168.0.4/32',
            'prod': '[Interface]\nAddress = 192.168.0.2/24\nListenPort = 51821\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = NaGaKVm6zB+Z0rusOiP+dEKdhyc+dzOEWhD7ZowV3k4=\nAllowedIPs = 192.168.0.4/32'
        }

        expected_result = {
            'dev': '[Interface]\nAddress = 192.168.0.1/24\nListenPort = 51820\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = NaGaKVm6zB+Z0rusOiP+dEKdhyc+dzOEWhD7ZowV3k4=\nAllowedIPs = 192.168.0.4/32',
            'prod': '[Interface]\nAddress = 192.168.0.2/24\nListenPort = 51821\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = NaGaKVm6zB+Z0rusOiP+dEKdhyc+dzOEWhD7ZowV3k4=\nAllowedIPs = 192.168.0.4/32'
        }

        result = helpers.update_public_key(old_image, new_image, config_files_map)

        self.assertEqual(result, expected_result)

    def test_update_public_key_empty_old_key(self):
        old_image = {'PublicKey': {'S': ''}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        new_image = {'PublicKey': {'S': 'new_key'}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        config_files_map = {
            'dev': '[Interface]\nAddress = 192.168.0.1/24\nListenPort = 51820\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = \nAllowedIPs = 192.168.0.4/32',
            'prod': '[Interface]\nAddress = 192.168.0.2/24\nListenPort = 51821\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = \nAllowedIPs = 192.168.0.4/32'
        }

        with self.assertRaises(Exception) as context:
            helpers.update_public_key(old_image, new_image, config_files_map)

    def test_update_public_key_empty_new_key(self):
        old_image = {'PublicKey': {'S': 'old_key'}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        new_image = {'PublicKey': {'S': ''}, 'Environments': {'L': [{'S': 'dev'}, {'S': 'prod'}]}}
        config_files_map = {
            'dev': '[Interface]\nAddress = 192.168.0.1/24\nListenPort = 51820\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = old_key\nAllowedIPs = 192.168.0.4/32',
            'prod': '[Interface]\nAddress = 192.168.0.2/24\nListenPort = 51821\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = old_key\nAllowedIPs = 192.168.0.4/32'
        }

        expected_result = {
            'dev': '[Interface]\nAddress = 192.168.0.1/24\nListenPort = 51820\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = \nAllowedIPs = 192.168.0.4/32',
            'prod': '[Interface]\nAddress = 192.168.0.2/24\nListenPort = 51821\nPostUp = wg set %i private-key /etc/wireguard/privatekey\n[Peer]\nPublicKey = nr5ETQ/evj5fUk5huzk+qkvoJ1+=\nAllowedIPs = 192.168.0.3/32\n[Peer]\nPublicKey = \nAllowedIPs = 192.168.0.4/32'
        }

        result = helpers.update_public_key(old_image, new_image, config_files_map)

        self.assertEqual(result, expected_result)


class TestAddPeerSection(unittest.TestCase):
    def test_add_peer_section_new_peer_no_existing_peers(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820
"""
        new_image = {
            'PublicKey': {'S': 'new_public_key'},
            'ClientIP': {'S': '10.0.0.3/32'}
        }
        expected_result = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = new_public_key
AllowedIPs = 10.0.0.3/32
"""
        result = helpers.add_peer_section(config_str, new_image)
        self.assertEqual(result.strip(), expected_result.strip())

    def test_add_peer_section_existing_peer(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = other_existing_key
AllowedIPs = 10.0.0.2/32
"""
        expected_result = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = other_existing_key
AllowedIPs = 10.0.0.2/32

[Peer]
PublicKey = other_public_key
AllowedIPs = 10.0.0.3/32
"""
        new_image = {
            'PublicKey': {'S': 'other_public_key'},
            'ClientIP': {'S': '10.0.0.3/32'}
        }
        result = helpers.add_peer_section(config_str, new_image)
        self.assertEqual(result.strip(), expected_result.strip())

    def test_add_peer_section_no_public_key(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820
"""
        new_image = {
            'ClientIP': {'S': '10.0.0.3/32'}
        }
        # No PublicKey in new_image, so the config should remain unchanged
        with self.assertRaises(Exception) as context:
            helpers.add_peer_section(config_str, new_image)

    def test_add_peer_section_no_client_ip(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820
"""
        new_image = {
            'PublicKey': {'S': 'new_public_key'}
        }
        expected_result = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820


[Peer]
PublicKey = new_public_key
AllowedIPs = 
"""
        with self.assertRaises(Exception) as context:
            helpers.add_peer_section(config_str, new_image)


class TestRemovePeerSection(unittest.TestCase):
    def test_remove_peer_section_existing_peer(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = to_be_removed_key
AllowedIPs = 10.0.0.1/32

[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.2/32
"""
        old_image = {
            'PublicKey': {'S': 'to_be_removed_key'}
        }
        expected_result = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.2/32
"""
        result = helpers.remove_peer_section(config_str, old_image)
        self.assertEqual(result.strip(), expected_result.strip())

    def test_remove_peer_section_non_existing_peer(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.2/32
"""
        old_image = {
            'PublicKey': {'S': 'non_existing_key'}
        }
        # Since the PublicKey doesn't exist, the config should remain unchanged
        result = helpers.remove_peer_section(config_str, old_image)
        self.assertEqual(result.strip(), config_str.strip())

    def test_remove_peer_section_empty_config(self):
        config_str = """
        [Interface]
        Address = 192.168.0.1/24
        ListenPort = 51820
        """
        old_image = {
            'PublicKey': {'S': 'any_key'}
        }
        # Config is empty, so nothing to remove
        result = helpers.remove_peer_section(config_str, old_image)
        self.assertEqual(result.strip(), config_str.strip())

    def test_remove_peer_section_no_public_key_in_old_image(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = some_key
AllowedIPs = 10.0.0.1/32
"""
        old_image = {}  # No PublicKey in old_image
        # Since no PublicKey is provided, the config should remain unchanged
        result = helpers.remove_peer_section(config_str, old_image)
        self.assertEqual(result.strip(), config_str.strip())

    def test_remove_peer_section_multiple_peers_with_similar_keys(self):
        config_str = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = to_be_removed_key_1
AllowedIPs = 10.0.0.1/32

[Peer]
PublicKey = to_be_removed_key_2
AllowedIPs = 10.0.0.2/32

[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.3/32
"""
        old_image = {
            'PublicKey': {'S': 'to_be_removed_key_2'}
        }
        expected_result = """
[Interface]
Address = 192.168.0.1/24
ListenPort = 51820

[Peer]
PublicKey = to_be_removed_key_1
AllowedIPs = 10.0.0.1/32

[Peer]
PublicKey = another_key
AllowedIPs = 10.0.0.3/32
"""
        result = helpers.remove_peer_section(config_str, old_image)
        self.assertEqual(result.strip(), expected_result.strip())


class TestUpdateConfigFileParameters(unittest.TestCase):
    @patch('helpers.ssm_client')
    def test_update_config_file_parameters_success(self, mock_ssm_client):
        # Arrange
        mock_put_parameter = MagicMock()
        mock_ssm_client.put_parameter = mock_put_parameter

        config_files_map = {
            'dev': 'config_data_for_dev',
            'prod': 'config_data_for_prod'
        }

        # Act
        helpers.update_config_file_parameters(config_files_map)

        # Assert
        calls = [
            unittest.mock.call(
                Name='/dev/wireguard/config_file',
                Description='The config file for wireguard in the dev network.',
                Value='config_data_for_dev',
                Type='SecureString',
                Overwrite=True,
                Tier='Standard',
                DataType='text'
            ),
            unittest.mock.call(
                Name='/prod/wireguard/config_file',
                Description='The config file for wireguard in the prod network.',
                Value='config_data_for_prod',
                Type='SecureString',
                Overwrite=True,
                Tier='Standard',
                DataType='text'
            )
        ]
        mock_put_parameter.assert_has_calls(calls)
        self.assertEqual(mock_put_parameter.call_count, 2)

    @patch('helpers.ssm_client')
    def test_update_config_file_parameters_failure(self, mock_ssm_client):
        # Arrange
        mock_ssm_client.put_parameter.side_effect = Exception("SSM update failed")

        config_files_map = {
            'dev': 'config_data_for_dev'
        }

        # Act & Assert
        with self.assertRaises(Exception) as context:
            helpers.update_config_file_parameters(config_files_map)
        self.assertEqual(str(context.exception), "SSM update failed")


class TestSendCommands(unittest.TestCase):
    @patch('helpers.ssm_client')
    def test_send_commands_success(self, mock_ssm_client):
        # Arrange
        mock_send_command = MagicMock()
        mock_send_command.return_value = {
            'Command': {'CommandId': 'command-id-123'}
        }
        mock_ssm_client.send_command = mock_send_command

        config_files_map = {
            'dev': 'config_data_for_dev',
            'prod': 'config_data_for_prod',
            'staging': 'config_data_for_staging'
        }
        instance_id_map = {
            'dev': {'instance_id': 'i-1234567890abcdef'},
            'prod': {'instance_id': 'i-abcdef1234567890'},
            'staging': {'instance_id': 'i-fedcba0987654321'}
        }

        # Act
        updated_instance_id_map = helpers.send_commands(config_files_map, instance_id_map)

        # Assert
        self.assertEqual(updated_instance_id_map['dev']['command_id'], 'command-id-123')
        self.assertEqual(updated_instance_id_map['prod']['command_id'], 'command-id-123')
        self.assertEqual(updated_instance_id_map['staging']['command_id'], 'command-id-123')

        # Verify that send_command was called with the expected parameters
        expected_calls = [
            unittest.mock.call(
                InstanceIds=['i-1234567890abcdef'],
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'commands': [
                        'config=$(aws ssm get-parameters --names /dev/wireguard/config_file --with-decryption --query Parameters[0].Value --output text --region us-east-1)',
                        'echo -e "$config" | sudo tee /etc/wireguard/wg0.conf > /dev/null',
                        'sudo systemctl reload wg-quick@wg0',
                        'sudo systemctl restart wg-quick@wg0'
                    ]
                }
            ),
            unittest.mock.call(
                InstanceIds=['i-abcdef1234567890'],
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'commands': [
                        'config=$(aws ssm get-parameters --names /prod/wireguard/config_file --with-decryption --query Parameters[0].Value --output text --region us-east-1)',
                        'echo -e "$config" | sudo tee /etc/wireguard/wg0.conf > /dev/null',
                        'sudo systemctl reload wg-quick@wg0',
                        'sudo systemctl restart wg-quick@wg0'
                    ]
                }
            ),
            unittest.mock.call(
                InstanceIds=['i-fedcba0987654321'],
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'commands': [
                        'config=$(aws ssm get-parameters --names /staging/wireguard/config_file --with-decryption --query Parameters[0].Value --output text --region us-east-1)',
                        'echo -e "$config" | sudo tee /etc/wireguard/wg0.conf > /dev/null',
                        'sudo systemctl reload wg-quick@wg0',
                        'sudo systemctl restart wg-quick@wg0'
                    ]
                }
            )
        ]
        mock_send_command.assert_has_calls(expected_calls)
        self.assertEqual(mock_send_command.call_count, 3)

    @patch('helpers.ssm_client')
    def test_send_commands_failure(self, mock_ssm_client):
        # Arrange
        mock_ssm_client.send_command.side_effect = Exception("SSM command failed")

        config_files_map = {
            'dev': 'config_data_for_dev'
        }
        instance_id_map = {
            'dev': {'instance_id': 'i-1234567890abcdef'}
        }

        # Act & Assert
        with self.assertRaises(Exception) as context:
            helpers.send_commands(config_files_map, instance_id_map)
        self.assertEqual(str(context.exception), "SSM command failed")


class TestCheckStatusOfCommands(unittest.TestCase):
    @patch('helpers.ssm_client')
    def test_check_status_of_commands_failed(self, mock_ssm_client):
        # Arrange
        mock_get_command_invocation = MagicMock()
        # Simulate different statuses
        mock_get_command_invocation.side_effect = [
            {'Status': 'InProgress'},
            {'Status': 'InProgress'},
            {'Status': 'InProgress'},
            {'Status': 'Success'},
            {'Status': 'Failed'},
            {'Status': 'Success'},
        ]
        mock_ssm_client.get_command_invocation = mock_get_command_invocation

        instance_id_map = {
            'env1': {'instance_id': 'i-1234567890abcdef', 'command_id': 'cmd1'},
            'env2': {'instance_id': 'i-abcdef1234567890', 'command_id': 'cmd2'},
            'env3': {'instance_id': 'i-fedcba0987654321', 'command_id': 'cmd3'}
        }

        # Act
        updated_instance_id_map = helpers.check_status_of_commands(instance_id_map)

        # Assert
        self.assertEqual(updated_instance_id_map['env1']['status'], 'Success')
        self.assertEqual(updated_instance_id_map['env2']['status'], 'Failed')
        self.assertEqual(updated_instance_id_map['env3']['status'], 'Success')

    @patch('helpers.ssm_client')
    def test_check_status_of_commands_success(self, mock_ssm_client):
        # Arrange
        mock_get_command_invocation = MagicMock()
        # Simulate different statuses
        mock_get_command_invocation.side_effect = [
            {'Status': 'InProgress'},
            {'Status': 'InProgress'},
            {'Status': 'Success'},
            {'Status': 'Success'},
            {'Status': 'Success'},
            {'Status': 'Success'},
        ]
        mock_ssm_client.get_command_invocation = mock_get_command_invocation

        instance_id_map = {
            'env1': {'instance_id': 'i-1234567890abcdef', 'command_id': 'cmd1'},
            'env2': {'instance_id': 'i-abcdef1234567890', 'command_id': 'cmd2'},
            'env3': {'instance_id': 'i-fedcba0987654321', 'command_id': 'cmd3'}
        }

        # Act
        updated_instance_id_map = helpers.check_status_of_commands(instance_id_map)

        # Assert
        self.assertEqual(updated_instance_id_map['env1']['status'], 'Success')
        self.assertEqual(updated_instance_id_map['env2']['status'], 'Success')
        self.assertEqual(updated_instance_id_map['env3']['status'], 'Success')

    @patch('helpers.ssm_client')
    def test_check_status_of_commands_failure(self, mock_ssm_client):
        # Arrange
        mock_ssm_client.get_command_invocation.side_effect = Exception("SSM command failed")

        instance_id_map = {
            'env1': {'instance_id': 'i-1234567890abcdef', 'command_id': 'cmd1'}
        }

        # Act & Assert
        with self.assertRaises(Exception) as context:
            helpers.check_status_of_commands(instance_id_map)
        self.assertEqual(str(context.exception), "SSM command failed")

    @patch('helpers.ssm_client')
    def test_check_status_of_commands_in_progress(self, mock_ssm_client):
        # Arrange
        mock_get_command_invocation = MagicMock()
        # Simulate a case where commands are stuck in 'InProgress'
        mock_get_command_invocation.side_effect = [
            {'Status': 'InProgress'},
            {'Status': 'InProgress'},
            {'Status': 'InProgress'},
            {'Status': 'InProgress'},
            {'Status': 'InProgress'}
        ]
        mock_ssm_client.get_command_invocation = mock_get_command_invocation

        instance_id_map = {
            'env1': {'instance_id': 'i-1234567890abcdef', 'command_id': 'cmd1'},
        }

        # Assert
        with self.assertRaises(Exception) as context:
            helpers.check_status_of_commands(instance_id_map)


class TestGetAvailableIP(unittest.TestCase):
    @patch('helpers.is_ip_available')
    @patch('random.randint')
    def test_get_available_ip(self, mock_randint, mock_is_ip_available):
        # Mock the random number to control the IP generation
        mock_randint.return_value = 10

        # Case where the IP is available
        mock_is_ip_available.side_effect = [True]  # First call returns True

        taken_ips = ["192.168.2.5/32", "192.168.2.6/32"]
        result = helpers.get_available_ip(taken_ips)
        self.assertEqual(result, "192.168.2.10/32")

        # Case where the first IP is not available, but the second one is
        mock_is_ip_available.side_effect = [False, True]  # First call False, second True
        result = helpers.get_available_ip(taken_ips)
        self.assertEqual(result, "192.168.2.10/32")

    @patch('helpers.is_ip_available')
    @patch('random.randint')
    def test_get_available_ip_with_multiple_attempts(self, mock_randint, mock_is_ip_available):
        # Mock the random number to control the IP generation
        mock_randint.side_effect = [5, 10, 15]  # Sequence of numbers

        # Case where the first two IPs are not available, but the third is
        mock_is_ip_available.side_effect = [False, False, True]

        taken_ips = ["192.168.2.5/32", "192.168.2.10/32"]
        result = helpers.get_available_ip(taken_ips)
        self.assertEqual(result, "192.168.2.15/32")


if __name__ == '__main__':
    unittest.main()
