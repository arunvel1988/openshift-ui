resource "docker_image" "nginx" {
  name = var.nginx_image
}

resource "docker_container" "nginx" {
  for_each = var.nginx_containers

  name  = each.key
  image = docker_image.nginx.image_id

  ports {
    internal = each.value.internal_port
    external = each.value.external_port
  }
}
