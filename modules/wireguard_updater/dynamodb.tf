module "wireguard_updater_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "4.1.0"
  name    = "wireguard-updater"

  hash_key = "ClientIP"

  attributes = [
    {
      name = "ClientIP"
      type = "S"
    }
  ]
  billing_mode     = "PAY_PER_REQUEST"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  tags = {
    DeployedBy = "terraform"
    Name       = "wireguard-updater"
  }
}

# resource "aws_dynamodb_resource_policy" "wireguard_updater_policy" {
#   resource_arn = module.wireguard_updater_table.dynamodb_table_stream_arn
#   policy       = <<EOF
# {
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Sid": "AccessStreamOnly",
#             "Effect": "Allow",
#             "Action": [
#                 "dynamodb:DescribeStream",
#                 "dynamodb:GetRecords",
#                 "dynamodb:GetShardIterator",
#                 "dynamodb:ListStreams"
#             ],
#             "Principal": {
#               "AWS": "arn:aws:iam::${var.account_id}:root"
#             },
#             "Resource": "${module.wireguard_updater_table.dynamodb_table_arn}/stream/*"
#         }
#     ]
# }
# EOF
# }