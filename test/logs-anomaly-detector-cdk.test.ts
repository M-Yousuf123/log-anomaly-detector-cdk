import { Template } from 'aws-cdk-lib/assertions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { LogsAnomalyDetectorCdkStack } from '../lib/logs-anomaly-detector-cdk-stack';
import { createTestApp } from './test-utils';

describe('LogsAnomalyDetectorCdkStack', () => {
  test('synthesizes all infrastructure resources', () => {
    const app = createTestApp();
    const stack = new LogsAnomalyDetectorCdkStack(app, 'TestStack', {
      functionCode: lambda.Code.fromInline('# test stub'),
    });
    const template = Template.fromStack(stack);

    template.resourceCountIs('AWS::SQS::Queue', 4);
    template.resourceCountIs('AWS::DynamoDB::Table', 1);
    template.resourceCountIs('AWS::Lambda::Function', 1);
  });
});
