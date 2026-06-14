#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { LogsAnomalyDetectorCdkStack } from '../lib/logs-anomaly-detector-cdk-stack';

const app = new cdk.App();

new LogsAnomalyDetectorCdkStack(app, 'AnomalyDetector', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region:
      process.env.CDK_DEFAULT_REGION ??
      process.env.AWS_REGION ??
      process.env.AWS_DEFAULT_REGION,
  },
});
