variable "nginx_image" {
  description = "The Docker image to use for NGINX"
  type        = string
  default     = "nginx:latest"
}

variable "nginx_containers" {
  description = "A map of container names to their port configurations"
  type = map(object({
    external_port = number
    internal_port = number
  }))
  default = {
    nginx-A = {
      external_port = 8011
      internal_port = 80
    }
    nginx-B = {
      external_port = 8012
      internal_port = 80
    }
    nginx-C = {
      external_port = 8013
      internal_port = 80
    }
  }
}
