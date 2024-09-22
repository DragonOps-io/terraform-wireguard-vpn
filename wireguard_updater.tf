module "wireguard_updater" {
  # Only deployed a single time, NOT per network/environment
  source     = "./modules/wireguard_updater"
  account_id = data.aws_caller_identity.account.account_id

  # Update the below map with your environments.
  # If you have different terraform workspaces or environments, you can utilize stack outputs instead of modules outputs.
  vpn_environments = [
    {
      environment        = "dev"
      instance_id        = module.vpn_dev.wireguard_instance_id
      public_key         = module.vpn_dev.wireguard_public_key
      wireguard_endpoint = module.vpn_dev.wireguard_public_endpoint
      vpc_cidr           = module.vpc_dev.vpc_cidr_block
    },
    {
      environment        = "stage"
      instance_id        = module.vpn_stage.wireguard_instance_id
      public_key         = module.vpn_stage.wireguard_public_key
      wireguard_endpoint = module.vpn_stage.wireguard_public_endpoint
      vpc_cidr           = module.vpc_stage.vpc_cidr_block
    }
  ]
}