import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigwv2Integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { BillingTag, TagKey, TagName } from '../constants';

export interface LogIngestorProps {
  readonly mainQueueUrl: string;
  readonly mainQueueArn: string;
  readonly priorityQueueUrl: string;
  readonly priorityQueueArn: string;
  /** Override Lambda code in unit tests to avoid Docker bundling. */
  readonly functionCode?: lambda.Code;
}

export class LogIngestor extends Construct {
  constructor(scope: Construct, id: string, props: LogIngestorProps) {
    super(scope, id);

    const mainQueueUrl = props.mainQueueUrl;
    const mainQueueArn = props.mainQueueArn;
    const priorityQueueUrl = props.priorityQueueUrl;
    const priorityQueueArn = props.priorityQueueArn;

    const ingestorFunction = new lambda.Function(this, 'LogIngestorFunction', {
      functionName: 'anomaly-detector-log-ingestor',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.handler',
      code:
        props.functionCode ??
        lambda.Code.fromAsset('src/lambdas/log_ingestor', {
          bundling: {
            image: lambda.Runtime.PYTHON_3_12.bundlingImage,
            command: [
              'bash',
              '-c',
              'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output',
            ],
          },
        }),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      tracing: lambda.Tracing.ACTIVE,
      environment: {
        MAIN_QUEUE_URL: mainQueueUrl,
        PRIORITY_QUEUE_URL: priorityQueueUrl,
        POWERTOOLS_SERVICE_NAME: 'log-ingestor',
      },
    });

    ingestorFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['sqs:SendMessage', 'sqs:SendMessageBatch'],
        resources: [mainQueueArn, priorityQueueArn],
      }),
    );

    const httpApi = new apigwv2.HttpApi(this, 'LogIngestorHttpApi', {
      apiName: 'anomaly-detector-log-ingestor-api',
    });

    httpApi.addRoutes({
      path: '/logs',
      methods: [apigwv2.HttpMethod.POST],
      integration: new apigwv2Integrations.HttpLambdaIntegration(
        'LogIngestorIntegration',
        ingestorFunction,
      ),
    });

    // HTTP API v2 has no native API keys/usage plans (REST API feature). For a portfolio
    // demo the endpoint is open; add a Lambda REQUEST authorizer on x-api-key for prod.

    new cdk.CfnOutput(this, 'LogIngestorApiUrl', {
      value: httpApi.apiEndpoint,
      exportName: 'AnomalyDetectorLogIngestorApiUrl',
    });

    cdk.Tags.of(this).add(TagKey, BillingTag);
    cdk.Tags.of(this).add(TagName, 'anomaly-detector-log-ingestor');
  }
}
