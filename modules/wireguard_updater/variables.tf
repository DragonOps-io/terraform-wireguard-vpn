variable "account_id" {
  type = string
}

variable "vpn_environments" {
  # A dynamic map of environments and instance IDs
  type = list(object({
    environment        = string
    instance_id        = string
    public_key         = string
    wireguard_endpoint = string
    vpc_cidr           = string
  }))
  default = []
}

