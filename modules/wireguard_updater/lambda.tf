locals {
  # Transform the list of maps into the desired map format
  vpn_environment_map = {
    for env in var.vpn_environments :
    env.environment => {
      public_key         = env.public_key
      wireguard_endpoint = env.wireguard_endpoint
      vpc_cidr           = env.vpc_cidr
      instance_id        = env.instance_id
      status             = ""
      command_id         = ""
    }
  }

  # Optional: Convert the map to JSON string if needed
  vpn_environment_map_json = jsonencode(local.vpn_environment_map)
}

module "handle_stream_updates_lambda" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = "handle_stream_updates"
  description   = "Lambda that listens for changes in the wireguard-updater DynamoDB table and makes appropriates updates to the WiregUrard VPN servers."
  handler       = "main.handle_stream_updates"
  runtime       = "python3.12"

  publish = true

  allowed_triggers = {
    DynamoDB = {
      principal  = "dynamodb.amazonaws.com"
      source_arn = module.wireguard_updater_table.dynamodb_table_stream_arn
    }
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb_stream = {
      effect = "Allow",
      actions = [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ],
      resources = [module.wireguard_updater_table.dynamodb_table_stream_arn]
    },
    ssm_access = {
      effect = "Allow",
      actions = [
        "ssm:SendCommand",
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetCommandInvocation",
        "ssm:AddTagsToResource"
      ],
      resources = ["*"]
    }
  }

  environment_variables = {
    ENVIRONMENT_MAP     = local.vpn_environment_map_json
    DYNAMODB_TABLE_NAME = split("/", module.wireguard_updater_table.dynamodb_table_arn)[1]
  }

  source_path = "./modules/wireguard_updater/python_code"

  tags = {
    DeployedBy = "terraform"
    Name       = "wireguard-updater"
  }
}

module "add_new_client_lambda" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = "add_new_client"
  description   = "Lambda that adds a new client and grants access to networks specified."
  handler       = "main.add_new_client"
  runtime       = "python3.12"

  source_path = "./modules/wireguard_updater/python_code"

  attach_policy_statements = true
  policy_statements = {
    dynamodb_item = {
      effect = "Allow",
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Scan"
      ],
      resources = [module.wireguard_updater_table.dynamodb_table_arn]
    },
    ssm_access = {
      effect = "Allow",
      actions = [
        "ssm:SendCommand",
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetCommandInvocation",
        "ssm:AddTagsToResource"
      ],
      resources = ["*"]
    }
  }


  environment_variables = {
    ENVIRONMENT_MAP     = local.vpn_environment_map_json
    DYNAMODB_TABLE_NAME = split("/", module.wireguard_updater_table.dynamodb_table_arn)[1]
  }

  tags = {
    DeployedBy = "terraform"

    Name = "wireguard-updater"
  }
}

module "get_client_config_file_lambda" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = "get_client_config_file"
  description   = "Retrieves the client config for a given client. This config is used in the user's WireGuard application on their local machine."
  handler       = "main.get_client_config_file"
  runtime       = "python3.12"

  source_path = "./modules/wireguard_updater/python_code"

  environment_variables = {
    ENVIRONMENT_MAP     = local.vpn_environment_map_json
    DYNAMODB_TABLE_NAME = split("/", module.wireguard_updater_table.dynamodb_table_arn)[1]
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb_item = {
      effect = "Allow",
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Scan"
      ],
      resources = [module.wireguard_updater_table.dynamodb_table_arn]
    },
    ssm_access = {
      effect = "Allow",
      actions = [
        "ssm:SendCommand",
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetCommandInvocation",
        "ssm:AddTagsToResource"
      ],
      resources = ["*"]
    }
  }

  tags = {
    DeployedBy = "terraform"
    Name       = "wireguard-updater"
  }

}

# TODO need remove client
# TODO need update client