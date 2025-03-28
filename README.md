# Data Ingestion and ETL/ELT Pipeline with Data Analysis and 2D Simulation of NASA Near Earth Object(NEO) Database

This repository counts as a final project for [Data Engineering Zoomcamp 2025](https://github.com/marketplace/actions/kestra-deploy-action). Here, you will explore various tools such as Terraform for IaC, dlt and python to ingest the data from the API, Kestra to orchestrate the flow and to load it to a data warehouse, BigQuery to run SQL queries and to write tables to the Bucket, Apache Spark to batch process and to feature engineer the data, and finally Google Looker Studio to analyze it. The project is created in a Google Cloud VM environment, so it is highly recommended that the environment is set up first before running the files. I have logged the steps through my journey of creating this project, and will leave links of resources to set up the environment in the Prerequisites section.

## Problem Definition

To get meaningful insights from data, somebody or some system needs to administrate, orchestrate, and monitor the data pipeline from ingesting the data to securely and meaningfully storing it. This pipeline aims to solve that problem specifically for this data source(https://cneos.jpl.nasa.gov/ca/) by using the cloud and various tools to complement it. In summary, pipeline hits NASA's official API, stores it, transforms and feature engineers it, analyzes it and as an extra, creates a 2D simulation to observe the NEOs. 

## Prerequisites 

1. The project works on a Google Cloud VM environment so follow the [video](https://www.youtube.com/watch?v=ae-CV2KfoN0&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb&index=14) until minute 26:50 to setup the environment.
1. Install terraform from their official [website](https://developer.hashicorp.com/terraform/install). 
1. Create a Service Account in your Google Cloud Project with the necessary roles (BigQuery Admin, Compute Admin, Storage Admin). Create and download a service account json key, name it as my-creds.json and replace it with the one in this repository.
1. Pull docker-compose.yml from Kestra ```curl -o docker-compose.yml https://raw.githubusercontent.com/kestra-io/kestra/develop/docker-compose.yml```
1. In this project, I wanted to set up the system without any local databases; Kestra runs on Cloud SQL instead of a local PostgresDB on the VM. You will need to follow Kestra's very explanatory official documentation [website](https://kestra.io/docs/installation/gcp-vm) to configure your docker-compose.yml to initiate the Kestra Service. You have already created and configured your Google Cloud VM by this point, so start following the instructions from minute 4:30 on the video documentation.


## Steps to Run the Pipeline
1. Assuming you went through the Prerequisites section, open Visual Studio Code or any IDE to remotely connect to your Google Cloud VM.
2. Configure the files in the main directory with your credentials and file locations depending on your VM directory structure.
3. In VSCode ports section, forward 8080 for Kestra.
4. In the repository main folder run ```terraform init``` ```terraform plan``` ```terraform apply``` to create your Google Cloud Bucket, BigQuery Warehouse, and initialize the Kestra Service.
5. Wait for Kestra to initialize(shouldn't take much) and insert ```localhost:8080``` to your search bar in any web browser. Hit enter to access the Kestra UI.
6. Click on the namespaces tab and hit zoomcamp. You should see "KV Store" on the menu bar. You will need to create Key-Values of your credentials in here.
   * Create BIGQUERY_PROJECT_ID as your Google Cloud Project name.
   * Create BIGQUERY_PRIVATE_KEY (without \n like structures for Kestra to be able to process it)
   * Create BIGQUERY_CLIENT_EMAIL using the same email as your Google Cloud Account.
7. Now that you have your credentials in the KV Store, click on the "Flows" in the left side menu and hit "Create" on top right.
8. Copy and paste the content in the ingestion.yaml to the blank file and hit Save and Execute. This gets the data from API using dlt and Kestra and ingests it to the BigQuery
9. Now that you have the data in the BigQuery Warehouse, you will need to store it in the Bucket also. To do that go to console.cloud.google.com and open BigQuery.
10. In BigQuery, create a new query and run
   
```
EXPORT DATA OPTIONS(
  uri='gs://project-kerem2025-demobucket/nasa_cad_export/cad_data_*.csv',
  format='CSV',
  overwrite=true,
  header=true
)
AS
SELECT * FROM `de-zoomcamp2025-project.nasa_cad_data.nasa_cad`;
```

11. Search "Bucket" on the searchbar and check to see if your data is successfully transferred to the Bucket created on the 4th step(running terraform infrastructure).
12. If you have the data on the Bucket, the next step is to create an external table and a materialized, partitioned, and clustered table in BigQuery. Run the query below to create the external table and don't forget to change the project name, Bucket location, and database name according to your setup.

```
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp2025-project.nasa_cad_data.df_final_ext` (
  col1  STRING,       -- des
  col2  STRING,       -- orbit_id
  col3  STRING,       -- jd
  col4  STRING,       -- dist
  col5  STRING,       -- dist_min
  col6  STRING,       -- dist_max
  col7  STRING,       -- v_rel
  col8  STRING,       -- v_inf
  col9  STRING,       -- t_sigma_f
  col10 STRING,       -- h
  col11 STRING,       -- fullname
  col12 STRING,       -- _dlt_load_id
  col13 STRING,       -- _dlt_id
  col14 STRING,       -- diameter
  col15 STRING,       -- diameter_sigma (will be dropped later)
  col16 TIMESTAMP,    -- cd_ts: the timestamp column (e.g. "1999-06-12T05:23:00.000Z")
  col17 STRING,       -- h_v_rel_ratio
  col18 STRING        -- h_diameter_ratio
)
OPTIONS (
  format = 'CSV',
  uris = ['gs://project-kerem2025-demobucket/df_final/*.csv'],
  skip_leading_rows = 1
);
```
13. Run the query below to create the partitioned and clustered table and don't forget to change the project name, bucket location, and database name according to your setup.

```
CREATE OR REPLACE TABLE `de-zoomcamp2025-project.nasa_cad_data.df_final_partitioned_clustered`
PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(1900, 2100, 1))
CLUSTER BY des
AS
SELECT
  col1 AS des,
  col2 AS orbit_id,
  SAFE_CAST(col3 AS FLOAT64) AS jd,
  SAFE_CAST(col4 AS FLOAT64) AS dist,
  SAFE_CAST(col5 AS FLOAT64) AS dist_min,
  SAFE_CAST(col6 AS FLOAT64) AS dist_max,
  SAFE_CAST(col7 AS FLOAT64) AS v_rel,
  SAFE_CAST(REGEXP_REPLACE(col8, r'_.*', '') AS FLOAT64) AS v_inf_numeric,
  col9 AS t_sigma_f,
  SAFE_CAST(col10 AS FLOAT64) AS h_numeric,
  col11 AS fullname,
  col12 AS _dlt_load_id,
  col13 AS _dlt_id,
  SAFE_CAST(col14 AS FLOAT64) AS diameter,
  -- Drop col15 (diameter_sigma)
  col16 AS cd_ts,
  SAFE_CAST(col17 AS FLOAT64) AS h_v_rel_ratio,
  SAFE_CAST(col18 AS FLOAT64) AS h_diameter_ratio,
  EXTRACT(YEAR FROM col16) AS year
FROM `de-zoomcamp2025-project.nasa_cad_data.df_final_ext`;
```
14. With these steps, our final table, df_final_partitioned_clustered is created and stored in our BigQuery Warehouse. The next step is to apply feature engineering to create new columns for our table using Apache Spark.
15. You will need to install Java and Apache Spark to your Google Cloud VM using the shell. Open a terminal, and proceed to the home directory. In the terminal, run the code below.

```
wget https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz
```
```
tar xzfv openjdk-11.0.2_linux-x64_bin.tar.gz
```
```
nano .bashrc
```
When the .bashrc file is opened scroll down to the end of the file and copy paste
```
export JAVA_HOME="$HOME/jdk-11.0.2"
export PATH="$JAVA_HOME/bin:$PATH"
```
Check to see if java works by running ```java --version``` on the terminal.
Remove the archive.
```
rm openjdk-11.0.2_linux-x64_bin.tar.gz
```
Download OpenJDK11.
```
wget https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz
```
Unpack it.
```
tar xzfv openjdk-11.0.2_linux-x64_bin.tar.gz
```
Run ```nano .bashrc``` on the terminal and copy and paste the code below at the end of the file.
```
export SPARK_HOME="$HOME/spark-3.3.2-bin-hadoop3"
export PATH="$SPARK_HOME/bin:$PATH
```
16. For the Python code to run, GOOGLE_APPLICATION_CREDENTIALS needs to be in the .bashrc file. Go to home folder and run ```nano .bashrc```
Scroll down to the end of the file and copy and paste ```export GOOGLE_APPLICATION_CREDENTIALS="/path/to/file/my-creds.json"``` Change the path as where your credentials file is.
18.  Final step is to run the Python Spark code on the terminal. Run ```spark-shell``` on the terminal and wait for spark shell to initialize. After it starts copy and paste the code to make the transformations on the dataset.
```
import pyspark
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from pyspark.sql.functions import to_timestamp, col
from pyspark.sql import functions as F

credentials_location = '/path/to/file/my-creds.json' #Change it to where your file is stored

conf = SparkConf() \
    .setMaster('local[*]') \
    .setAppName('test') \
    .set("spark.jars", "./lib/gcs-connector-hadoop3-2.2.5.jar") \
    .set("spark.hadoop.google.cloud.auth.service.account.enable", "true") \
    .set("spark.hadoop.google.cloud.auth.service.account.json.keyfile", credentials_location)

sc = SparkContext(conf=conf)

hadoop_conf = sc._jsc.hadoopConfiguration()

hadoop_conf.set("fs.AbstractFileSystem.gs.impl",  "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS")
hadoop_conf.set("fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
hadoop_conf.set("fs.gs.auth.service.account.json.keyfile", credentials_location)
hadoop_conf.set("fs.gs.auth.service.account.enable", "true")

spark = SparkSession.builder \
    .config(conf=sc.getConf()) \
    .getOrCreate()

df = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load("gs://path/to/cad_data_000000000000.csv") #Change it to the path to your Bucket data.

# 1) Parse "cd" into a timestamp column "cd_ts"
df_parsed = df.withColumn(
    "cd_ts",
    to_timestamp(col("cd"), "yyyy-MMM-dd HH:mm")
)

# 2) Drop the original "cd" column
df_parsed = df_parsed.drop("cd")

# Now "cd" is removed, and "cd_ts" remains
df_parsed.printSchema()

# Create 2 new columns
df_final = df_parsed.withColumn(
    "h_v_rel_ratio",
    F.col("h") / F.col("v_rel")
).withColumn(
    "h_diameter_ratio",
    F.col("h") / F.col("diameter")
)

df_final.printSchema()
df_final.show(5)
```
The code above connects the Spark to the Bucket and does feature engineering on the dataset. Now we will need to upload the transformed data back to our Bucket. Edit the path and run the code below on the spark shell to do that.
```
df_final.write.mode("overwrite").option("header", "true").csv("gs://path-to-directory/df_final")
```

## Dashboard

For this part I have used Google's Looker Studio(https://lookerstudio.google.com). Click on the [link](https://lookerstudio.google.com/reporting/3c9a9cbc-ca81-44ce-b454-b309627c3852) to access the visualizations.

<img src="https://github.com/keremycdg/NEO_Data-Pipeline_2D-Simulation/blob/main/images/charts.PNG" alt="chart1" width="800" height="600">

## 2D Simulation

![NEO](https://github.com/keremycdg/NEO_Data-Pipeline_2D-Simulation/blob/main/images/NEO.gif)

Refer to the extra(2D_Simulation) folder for the instructions to run the simulation with python
