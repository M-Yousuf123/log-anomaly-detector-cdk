import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as aws_sqs from 'aws-cdk-lib/aws-sqs';
import { BillingTag, DEAD_LETTER_MAX_RECEIVE_COUNT, TagKey, TagName } from '../constants';

export const MAIN_QUEUE_URL_EXPORT = 'AnomalyDetectorMainQueueUrl';
export const MAIN_QUEUE_ARN_EXPORT = 'AnomalyDetectorMainQueueArn';

export class MainQueue extends Construct {
  public readonly queue: aws_sqs.Queue;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const deadLetterQueue = new aws_sqs.Queue(this, 'AnomalyDetectorMainDeadLetterQueue', {
      queueName: 'anomaly-detector-main-dlq',
    });

    this.queue = new aws_sqs.Queue(this, 'AnomalyDetectorMainQueue', {
      queueName: 'anomaly-detector-main-queue',
      visibilityTimeout: cdk.Duration.seconds(300), // TODO: check if lambda timeout is less than this
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: DEAD_LETTER_MAX_RECEIVE_COUNT,
      },
    });

    new cdk.CfnOutput(this, 'MainQueueUrl', {
      value: this.queue.queueUrl,
      exportName: MAIN_QUEUE_URL_EXPORT,
    });

    new cdk.CfnOutput(this, 'MainQueueArn', {
      value: this.queue.queueArn,
      exportName: MAIN_QUEUE_ARN_EXPORT,
    });

    cdk.Tags.of(this).add(TagKey, BillingTag);
    cdk.Tags.of(this).add(TagName, 'anomaly-detector-main-queue');
  }
}
