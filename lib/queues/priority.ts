import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as aws_sqs from 'aws-cdk-lib/aws-sqs';
import { BillingTag, DEAD_LETTER_MAX_RECEIVE_COUNT, TagKey, TagName } from '../constants';

export const PRIORITY_QUEUE_URL_EXPORT = 'AnomalyDetectorPriorityQueueUrl';
export const PRIORITY_QUEUE_ARN_EXPORT = 'AnomalyDetectorPriorityQueueArn';

export class PriorityQueue extends Construct {
  public readonly queue: aws_sqs.Queue;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const deadLetterQueue = new aws_sqs.Queue(this, 'AnomalyDetectorPriorityDeadLetterQueue', {
      queueName: 'anomaly-detector-priority-dlq.fifo',
      fifo: true,
    });

    this.queue = new aws_sqs.Queue(this, 'AnomalyDetectorPriorityQueue', {
      queueName: 'anomaly-detector-priority-queue.fifo',
      fifo: true,
      visibilityTimeout: cdk.Duration.seconds(300), // TODO: check if lambda timeout is less than this
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: DEAD_LETTER_MAX_RECEIVE_COUNT,
      },
    });

    new cdk.CfnOutput(this, 'PriorityQueueUrl', {
      value: this.queue.queueUrl,
      exportName: PRIORITY_QUEUE_URL_EXPORT,
    });

    new cdk.CfnOutput(this, 'PriorityQueueArn', {
      value: this.queue.queueArn,
      exportName: PRIORITY_QUEUE_ARN_EXPORT,
    });

    cdk.Tags.of(this).add(TagKey, BillingTag);
    cdk.Tags.of(this).add(TagName, 'anomaly-detector-priority-queue');
  }
}
