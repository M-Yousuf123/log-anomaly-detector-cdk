import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { DdbTable } from './ddb-table';
import { LogIngestor } from './lambdas/log-ingestor';
import { MainQueue } from './queues/main';
import { PriorityQueue } from './queues/priority';

export interface LogsAnomalyDetectorCdkStackProps extends cdk.StackProps {
  /** Override Lambda code in unit tests to avoid Docker bundling. */
  readonly functionCode?: lambda.Code;
}

export class LogsAnomalyDetectorCdkStack extends cdk.Stack {
  constructor(
    scope: Construct,
    id: string,
    props?: LogsAnomalyDetectorCdkStackProps,
  ) {
    super(scope, id, props);

    const mainQueue = new MainQueue(this, 'AnomalyDetectorMainQueue');
    const priorityQueue = new PriorityQueue(this, 'AnomalyDetectorPriorityQueue');
    new DdbTable(this, 'AnomalyDetectorDdbTable');
    new LogIngestor(this, 'AnomalyDetectorLogIngestor', {
      mainQueueUrl: mainQueue.queue.queueUrl,
      mainQueueArn: mainQueue.queue.queueArn,
      priorityQueueUrl: priorityQueue.queue.queueUrl,
      priorityQueueArn: priorityQueue.queue.queueArn,
      functionCode: props?.functionCode,
    });
  }
}
