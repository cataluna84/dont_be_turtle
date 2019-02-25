#!/usr/bin/env bash

export YOUR_TPU_NAME=jwkangmacpro2-tpu
export YOUR_SERVICE_NAME=283083143712-compute@developer.gserviceaccount.com

export DATA_BUCKET=gs://pose_dataset_tfrecord

export MODEL_BUCKET=gs://dontbeturtle_ckpt4/
#export TENSORBOARD_BUCKET=gs://dontbeturtle_tflogs/

export MODEL_BUCKET_MUTIGPU=gs://dontbeturtle_multigpu
export MODEL_BUCKET2=gs://bucket_aisolab
export MODEL_BUCKET3=gs://dontbeturtle_ckpt3
export MODEL_BUCKET4=gs://bucket_yglee

#export TENSORBOARD_BUCKET3=gs://dontbeturtle_tflogs3/

echo GET AUTHORIZATION OF GCP BUCKET

# check tpus list
gcloud alpha compute tpus describe ${YOUR_TPU_NAME}

# GIVE READ / WRITE AUTH

gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${DATA_BUCKET}
gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${DATA_BUCKET}


gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${MODEL_BUCKET}
gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${MODEL_BUCKET}

#gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${TENSORBOARD_BUCKET}
#gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${TENSORBOARD_BUCKET}

gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${MODEL_BUCKET2}
gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${MODEL_BUCKET2}


gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${MODEL_BUCKET3}
gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${MODEL_BUCKET3}

gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${MODEL_BUCKET4}
gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${MODEL_BUCKET4}


gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${MODEL_BUCKET_MUTIGPU}
gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${MODEL_BUCKET_MUTIGPU}

#gsutil acl ch -u ${YOUR_SERVICE_NAME}:READER ${TENSORBOARD_BUCKET3}
#gsutil acl ch -u ${YOUR_SERVICE_NAME}:WRITER ${TENSORBOARD_BUCKET3}
#

