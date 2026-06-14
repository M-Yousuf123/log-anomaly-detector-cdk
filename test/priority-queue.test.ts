import { Match, Template } from 'aws-cdk-lib/assertions';
import * as cdk from 'aws-cdk-lib/core';
import { PriorityQueue } from '../lib/queues/priority';
import { BillingTag, DEAD_LETTER_MAX_RECEIVE_COUNT, TagKey, TagName } from '../lib/constants';
import { createTestApp } from './test-utils';

describe('PriorityQueue', () => {
  let template: Template;

  beforeEach(() => {
    const app = createTestApp();
    const stack = new cdk.Stack(app, 'TestPriorityQueue');
    new PriorityQueue(stack, 'TestPriorityQueue');
    template = Template.fromStack(stack);
  });

  test('creates priority queue and dead-letter queue', () => {
    template.resourceCountIs('AWS::SQS::Queue', 2);
  });

  test('configures fifo dead-letter queue', () => {
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-priority-dlq.fifo',
      FifoQueue: true,
    });
  });

  test('configures fifo priority queue with visibility timeout and redrive policy', () => {
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-priority-queue.fifo',
      FifoQueue: true,
      VisibilityTimeout: 300,
      RedrivePolicy: Match.objectLike({
        maxReceiveCount: DEAD_LETTER_MAX_RECEIVE_COUNT,
      }),
    });
  });

  test('applies cost allocation tags to both queues', () => {
    const expectedTags = Match.arrayWith([
      { Key: TagKey, Value: BillingTag },
      { Key: TagName, Value: 'anomaly-detector-priority-queue' },
    ]);

    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-priority-queue.fifo',
      Tags: expectedTags,
    });

    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'anomaly-detector-priority-dlq.fifo',
      Tags: expectedTags,
    });
  });
});
