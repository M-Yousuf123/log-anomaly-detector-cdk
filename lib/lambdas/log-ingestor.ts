import { execSync } from 'child_process';
import * as path from 'path';

import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigwv2Integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { BillingTag, TagKey, TagName } from '../constants';

const LOG_INGESTOR_SOURCE = path.join(
  __dirname,
  '../../src/lambdas/log_ingestor',
);
const LOG_INGESTOR_MODULE = 'log_ingestor';

function requireDocker(): void {
  try {
    execSync('docker info', { stdio: 'ignore' });
  } catch {
    throw new Error(
      'Docker is required to bundle the log-ingestor Lambda. ' +
        'Install Docker Engine (https://docs.docker.com/get-docker/) and ensure it is running, ' +
        'then run cdk deploy again.',
    );
  }
}

function logIngestorFunctionCode(): lambda.Code {
  requireDocker();
  return lambda.Code.fromAsset(LOG_INGESTOR_SOURCE, {
    bundling: {
      image: lambda.Runtime.PYTHON_3_12.bundlingImage,
      command: [
        'bash',
        '-c',
        [
          'pip install -r requirements.txt -t /asset-output',
          `mkdir -p /asset-output/${LOG_INGESTOR_MODULE}`,
          `cp -au . /asset-output/${LOG_INGESTOR_MODULE}/`,
        ].join(' && '),
      ],
    },
  });
}

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
      architecture: lambda.Architecture.ARM_64,
      handler: 'log_ingestor.handler.handler',
      code: props.functionCode ?? logIngestorFunctionCode(),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        MAIN_QUEUE_URL: mainQueueUrl,
        PRIORITY_QUEUE_URL: priorityQueueUrl,
        SERVICE_NAME: 'log-ingestor',
      },
    });

    ingestorFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['sqs:SendMessage', 'sqs:SendMessageBatch'],
        resources: [mainQueueArn, priorityQueueArn],
      }),
    );

    ingestorFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['cloudwatch:PutMetricData'],
        resources: ['*'],
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
