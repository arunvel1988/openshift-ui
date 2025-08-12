# docker network create frontend_net


# Read an existing Docker network
data "docker_network" "frontend" {
  name = "frontend_net"
}

# Pull image
resource "docker_image" "nginx" {
  name = "nginx:alpine"
  keep_locally = false
}

# Create container in existing network
resource "docker_container" "web" {
  name  = "frontend-nginx"
  image = docker_image.nginx.image_id

  networks_advanced {
    name = data.docker_network.frontend.name
  }

  ports {
    internal = 80
    external = 8080
  }
}
