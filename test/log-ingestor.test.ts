import { Match, Template } from 'aws-cdk-lib/assertions';
import * as cdk from 'aws-cdk-lib/core';
import * as aws_sqs from 'aws-cdk-lib/aws-sqs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { LogIngestor } from '../lib/lambdas/log-ingestor';
import { BillingTag, TagKey, TagName } from '../lib/constants';
import { createTestApp } from './test-utils';

describe('LogIngestor', () => {
  let template: Template;

  beforeEach(() => {
    const app = createTestApp();
    const queueStack = new cdk.Stack(app, 'TestQueues');
    const mainQueue = new aws_sqs.Queue(queueStack, 'MainQueue', {
      queueName: 'test-main-queue',
    });
    const priorityQueue = new aws_sqs.Queue(queueStack, 'PriorityQueue', {
      queueName: 'test-priority-queue.fifo',
      fifo: true,
    });

    const stack = new cdk.Stack(app, 'TestLogIngestor');
    new LogIngestor(stack, 'TestLogIngestor', {
      mainQueueUrl: mainQueue.queueUrl,
      mainQueueArn: mainQueue.queueArn,
      priorityQueueUrl: priorityQueue.queueUrl,
      priorityQueueArn: priorityQueue.queueArn,
      functionCode: lambda.Code.fromInline('# test stub'),
    });
    template = Template.fromStack(stack);
  });

  test('creates Python 3.12 Lambda with queue env vars and tracing', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'anomaly-detector-log-ingestor',
      Runtime: 'python3.12',
      Handler: 'log_ingestor.handler.handler',
      Timeout: 30,
      MemorySize: 256,
      TracingConfig: { Mode: 'Active' },
      Environment: {
        Variables: Match.objectLike({
          MAIN_QUEUE_URL: Match.anyValue(),
          PRIORITY_QUEUE_URL: Match.anyValue(),
          POWERTOOLS_SERVICE_NAME: 'log-ingestor',
        }),
      },
    });
  });

  test('grants SQS send permissions on both queues only', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: Match.arrayWith(['sqs:SendMessage', 'sqs:SendMessageBatch']),
            Effect: 'Allow',
          }),
        ]),
      },
    });
  });

  test('creates HTTP API with POST /logs route', () => {
    template.hasResourceProperties('AWS::ApiGatewayV2::Route', {
      RouteKey: 'POST /logs',
    });
  });

  test('exports API URL', () => {
    template.findOutputs('*', {
      Export: { Name: 'AnomalyDetectorLogIngestorApiUrl' },
    });
  });

  test('applies cost allocation tags', () => {
    const expectedTags = Match.arrayWith([
      { Key: TagKey, Value: BillingTag },
      { Key: TagName, Value: 'anomaly-detector-log-ingestor' },
    ]);

    template.hasResourceProperties('AWS::Lambda::Function', {
      Tags: expectedTags,
    });
  });
});
