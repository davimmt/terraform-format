# terraform-format

Provides a basic format for all .tf files.

Example of file and it's formatted rewrite:

`main.tf (before)`
```



provider "aws" {region = "us-east-1"}
data "aws_something" "something"{ region = "us-east-1"}
locals{ok = "lol" }

resource "aws_instance" "ec2" {
  for_each = {for i, instance in var.instances: i => instance if i in ["match"]}
   subnet_id = local.output[each.value.subnet]
 ami                    = var.ami
instance_type    = var.type
  key_name               = var.key_name
  user_data      = var.user_data == "" ? "" : file("${var.user_data}")

root_block_device {
	encrypted    = var.root_block_device.encrypted
	volume_size = var.root_block_device.volume_size
	volume_type = var.root_block_device.volume_type
}




  dynamic "ebs_block_device" {
  for_each        = var.block_devices
  content {
  device_name = block_device_mappings.value.device_name
  encrypted   = block_device_mappings.value.encrypted
  volume_size = block_device_mappings.value.volume_size
  volume_type = block_device_mappings.value.volume_type
}
}
  instance_initiated_shutdown_behavior = var.shutdown_behavior
}




```

`main.tf (after)`
```
resource "aws_instance" "ec2" {
  count         = var.instance_number
  subnet_id     = local.output[count.index]
  ami           = var.ami
  instance_type = var.type
  key_name      = var.key_name
  user_data     = var.user_data == "" ? "" : file("${var.user_data}")

  root_block_device {
    encrypted   = var.root_block_device.encrypted
    volume_size = var.root_block_device.volume_size
    volume_type = var.root_block_device.volume_type
  }

  dynamic "ebs_block_device" {
    for_each = var.block_devices

    content {
      device_name = block_device_mappings.value.device_name
      encrypted   = block_device_mappings.value.encrypted
      volume_size = block_device_mappings.value.volume_size
      volume_type = block_device_mappings.value.volume_type
    }
  }

  instance_initiated_shutdown_behavior = var.shutdown_behavior
}
```
