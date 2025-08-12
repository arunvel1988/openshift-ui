variable "nginx_image" {
  description = "Docker image name for nginx"
  type        = string
  default     = "nginx:alpine"
}

variable "container_name" {
  description = "Name of the container"
  type        = string
  default     = "nginx"
}

variable "internal_port" {
  description = "Internal port exposed by the container"
  type        = number
  default     = 80
}

variable "external_port" {
  description = "Port to map to on the host"
  type        = number
  default     = 8080
}
