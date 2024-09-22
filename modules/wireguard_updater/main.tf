resource "aws_lambda_event_source_mapping" "dynamodb_lambda_trigger" {
  event_source_arn  = module.wireguard_updater_table.dynamodb_table_stream_arn
  function_name     = module.handle_stream_updates_lambda.lambda_function_arn
  starting_position = "LATEST"
}
