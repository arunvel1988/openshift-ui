# docker volume create my_shared_data


provider "docker" {}

# 1. Fetch image metadata from Docker Hub (registry)
data "docker_registry_image" "nginx" {
  name = "nginx:alpine"
}

# 2. Use existing Docker network (like "bridge")
data "docker_network" "bridge" {
  name = "bridge"
}

# 3. Use existing volume (assume created outside Terraform)
data "docker_volume" "shared_data" {
  name = "my_shared_data"
}

# 4. Run nginx container using the image metadata and attach it to existing network & volume
resource "docker_image" "nginx" {
  name = data.docker_registry_image.nginx.name
}

resource "docker_container" "web" {
  name  = "nginx_web"
  image = docker_image.nginx.image_id

  networks_advanced {
    name = data.docker_network.bridge.name
  }

  mounts {
    target = "/usr/share/nginx/html"
    source = data.docker_volume.shared_data.name
    type   = "volume"
  }

  ports {
    internal = 80
    external = 8080
  }
}

# 5. Query the running container using data source
data "docker_container" "running_nginx" {
  name = docker_container.web.name
}

# OUTPUTS
output "nginx_image_digest" {
  value = data.docker_registry_image.nginx.sha256_digest
}

output "container_ip" {
  value = data.docker_container.running_nginx.network_data[0].ip_address
}

output "volume_path" {
  value = data.docker_volume.shared_data.mountpoint
}

output "network_id" {
  value = data.docker_network.bridge.id
}
