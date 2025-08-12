output "container_id" {
  description = "ID of the Docker container"
  value       = docker_container.nginx.id
}

output "container_name" {
  description = "Name of the Docker container"
  value       = docker_container.nginx.name
}

output "container_ip" {
  description = "The IP address of the nginx container"
  value       = docker_container.nginx.network_data[0].ip_address
}
