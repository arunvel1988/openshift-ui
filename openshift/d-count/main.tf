
resource "docker_image" "nginx" {
  name = var.nginx_image
}

resource "docker_container" "nginx" {
  count = 3  # Change to 2 or 3 replicas as needed

  name  = "${var.container_name}-${count.index}"
  image = docker_image.nginx.image_id

  ports {
    internal = var.internal_port
    external = var.external_port + count.index
  }
}
