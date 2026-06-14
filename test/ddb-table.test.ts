import { Match, Template } from 'aws-cdk-lib/assertions';
import * as cdk from 'aws-cdk-lib/core';
import { DdbTable } from '../lib/ddb-table';
import { BillingTag, TagKey, TagName } from '../lib/constants';
import { createTestApp } from './test-utils';

describe('DdbTable', () => {
  let template: Template;

  beforeEach(() => {
    const app = createTestApp();
    const stack = new cdk.Stack(app, 'TestDdbTable');
    new DdbTable(stack, 'TestDdbTable');
    template = Template.fromStack(stack);
  });

  test('creates a single DynamoDB table', () => {
    template.resourceCountIs('AWS::DynamoDB::Table', 1);
  });

  test('configures table with pay-per-request billing and standard class', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'anomaly-detector-ddb-table',
      BillingMode: 'PAY_PER_REQUEST',
      TableClass: 'STANDARD',
      KeySchema: [
        {
          AttributeName: 'id',
          KeyType: 'HASH',
        },
      ],
      AttributeDefinitions: [
        {
          AttributeName: 'id',
          AttributeType: 'S',
        },
      ],
    });
  });

  test('applies cost allocation tags', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      Tags: Match.arrayWith([
        { Key: TagKey, Value: BillingTag },
        { Key: TagName, Value: 'anomaly-detector-ddb-table' },
      ]),
    });
  });
});
