output "container_ids" {
  value = [
    for c in docker_container.nginx : c.id
  ]
}


output "container_names" {
  value = [
    for c in docker_container.nginx : c.name
  ]
}

output "container_name_to_ip" {
  value = {
    for c in docker_container.nginx :
    c.name => c.network_data[0].ip_address
  }
}
