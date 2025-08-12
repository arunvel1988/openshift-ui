output "container_ids" {
  value = {
    for name, container in docker_container.nginx :
    name => container.id
  }
}

output "container_ips" {
  value = {
    for name, container in docker_container.nginx :
    name => container.network_data[0].ip_address
  }
}
