module "vpn_dev" {
  source                = "./modules/wireguard_vpn_server"
  environment           = "dev"
  account_id            = data.aws_caller_identity.account.id
  subnet_id             = module.vpc_dev.public_subnets[0] # Change if using your own IaC / existing network
  vpc_id                = module.vpc_dev.vpc_id            # Change if using your own IaC / existing network
  wireguard_port        = "64731"                          # Should be a new, random port per WireGuard server
  wireguard_ip_address  = "192.168.2.2/32"                 # Should be an unused IP in the range 192.168.2.0/16
  wireguard_public_key  = "GENERATE_ME_WITH_SCRIPT"        # Generate this and the below using the script provided in this repository
  wireguard_private_key = "GENERATE_ME_WITH_SCRIPT"
  region                = var.region
}

module "vpn_stage" {
  source                = "./modules/wireguard_vpn_server"
  environment           = "stage"
  account_id            = data.aws_caller_identity.account.id
  subnet_id             = module.vpc_stage.public_subnets[0] # Change if using your own IaC / existing network
  vpc_id                = module.vpc_stage.vpc_id            # Change if using your own IaC / existing network
  wireguard_port        = "64729"                            # Should be a new, random port per WireGuard server
  wireguard_ip_address  = "192.168.2.3/32"                   # Should be an unused IP in the range 192.168.2.0/16
  wireguard_public_key  = "GENERATE_ME_WITH_SCRIPT"          # Generate this and the below using the script provided in this repository
  wireguard_private_key = "GENERATE_ME_WITH_SCRIPT"
  region                = var.region
}