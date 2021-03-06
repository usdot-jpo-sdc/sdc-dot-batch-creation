import json
import os
import time

import boto3

from common.logger_utility import LoggerUtility


class CreateBatches:

    def get_latest_batch(self, latest_batch_id):
        try:
            ssm = boto3.client('ssm', region_name='us-east-1')
            response = ssm.get_parameter(Name=latest_batch_id, WithDecryption=False)
            LoggerUtility.log_info("Response from parameter store - {}".format(response))
            current_batch_id = response["Parameter"]["Value"]
        except Exception as ex:
            LoggerUtility.log_error("Unable to get latest batch with reason - {}".format(ex))
            raise ex
        return current_batch_id

    def create_new_batch_id(self, latest_batch_id):
        new_batch_id = str(int(time.time()))
        try:
            ssm = boto3.client('ssm', region_name='us-east-1')
            ssm.put_parameter(
                Name=latest_batch_id,
                Description='Parameter to hold the latest value of a batch used for processing waze transactions',
                Value=new_batch_id,
                Type='String',
                Overwrite=True,
                AllowedPattern='\\d+')
            LoggerUtility.log_info("Successfully created a new batch with id - {}".format(new_batch_id))
        except Exception as ex:
            LoggerUtility.log_error("Failed to create new batch with reason - {}".format(ex))
            raise ex
        return new_batch_id

    def push_batch_id_to_queue(self, current_batch_id):
        try:
            sqs = boto3.resource('sqs', region_name='us-east-1')
            queue_name = os.environ["SQS_CURATED_BATCHES_QUEUE_ARN"].rsplit(':', 1)[1]
            curated_batches_queue = sqs.get_queue_by_name(QueueName=queue_name)
            curated_batches_queue.send_message(
                MessageBody=json.dumps({'BatchId': current_batch_id}),
                MessageGroupId="WazeCuratedBatchesMessageGroup"
            )
            LoggerUtility.log_info("Successfully pushed the message to queue for batchid - {}".format(current_batch_id))
        except Exception as ex:
            LoggerUtility.log_error("Failed to push the batch to queue - {}".format(ex))
            raise ex

    def create_batch(self):
        LoggerUtility.set_level()
        LoggerUtility.log_info("Initiating batch creation process")
        latest_batch_id = os.environ["LATEST_BATCH_ID"]
        current_batch_id = self.get_latest_batch(latest_batch_id)
        if "" == current_batch_id:
            new_batch_id = self.create_new_batch_id(latest_batch_id)
        else:
            current_batch_id = self.get_latest_batch(latest_batch_id)
            self.push_batch_id_to_queue(current_batch_id)
            new_batch_id = self.create_new_batch_id(latest_batch_id)

        LoggerUtility.log_info("Completed batch creation process with batch id - {}".format(new_batch_id))
