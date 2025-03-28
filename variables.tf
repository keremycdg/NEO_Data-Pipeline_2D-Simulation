variable "credentials" {
  description = "Path to your service account credentials JSON file."
  default     = "my-creds.json"
}

variable "project" {
  description = "Google Cloud project ID"
  default     = ""                        #Insert project name on the Google Cloud
}

variable "region" {
  description = "Google Cloud region"
  default     = "us-south1"               #Change it with the region of your Google Cloud Project
}

variable "location" {
  description = "Google Cloud location (for resources like storage buckets and BigQuery datasets)"
  default     = "US"
}

variable "bq_dataset_name" {
  description = "BigQuery dataset name"
  default     = ""                       #Insert the name of the BigQuery dataset name you want to create
}

variable "gcs_bucket_name" {
  description = "Google Cloud Storage bucket name (must be globally unique)"
  default     = ""                       #Insert a globally unique Bucket name which will be created
}

variable "gcs_storage_class" {
  description = "Storage class for the GCS bucket"
  default     = "STANDARD"
}

# New variable for referencing your Docker Compose file
variable "compose_file" {
  description = "Path to the Docker Compose file that will be executed by Terraform"
  default     = "docker-compose.yml"
}
