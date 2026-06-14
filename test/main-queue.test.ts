import { Match, Template } from 'aws-cdk-lib/assertions';
import * as cdk from 'aws-cdk-lib/core';
import { MainQueue } from '../lib/queues/main';
import { BillingTag, DEAD_LETTER_MAX_RECEIVE_COUNT, TagKey, TagName } from '../lib/constants';
import { createTestApp } from './test-utils';

describe('MainQueue', () => {
  let template: Template;

  beforeEach(() => {
    const app = createTestApp();
    const stack = new cdk.Stack(app, 'TestMainQueue');
    new MainQueue(stack, 'TestMainQueue');
    template = Template.fromStack(stack);
  });

  test('creates main queue and dead-letter queue', () => {
    template.resourceCountIs('AWS::SQS::Queue', 2);
  });

  test('configures dead-letter queue', () => {
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-main-dlq',
    });
  });

  test('configures main queue with visibility timeout and redrive policy', () => {
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-main-queue',
      VisibilityTimeout: 300,
      RedrivePolicy: Match.objectLike({
        maxReceiveCount: DEAD_LETTER_MAX_RECEIVE_COUNT,
      }),
    });
  });

  test('applies cost allocation tags to both queues', () => {
    const expectedTags = Match.arrayWith([
      { Key: TagKey, Value: BillingTag },
      { Key: TagName, Value: 'anomaly-detector-main-queue' },
    ]);

    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-main-queue',
      Tags: expectedTags,
    });

    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-main-dlq',
      Tags: expectedTags,
    });
  });
});
