terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.6.0"
    }
    # add the null provider
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0.0"
    }
  }
}

provider "google" {
  credentials = file(var.credentials)
  project     = var.project
  region      = var.region
}

resource "google_storage_bucket" "data_lake_bucket" {
  name          = var.gcs_bucket_name
  location      = var.location
  storage_class = var.gcs_storage_class
  force_destroy = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_bigquery_dataset" "data_lake_dataset" {
  dataset_id = var.bq_dataset_name
  location   = var.location
}

resource "null_resource" "run_docker_compose" {
  depends_on = [
    google_storage_bucket.data_lake_bucket,
    google_bigquery_dataset.data_lake_dataset
  ]

  provisioner "local-exec" {
    command = "docker-compose -f ${var.compose_file} up -d"
  }
}
