import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as aws_dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { BillingTag, TagKey, TagName } from './constants';

export class DdbTable extends Construct {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    new aws_dynamodb.Table(this, 'AnomalyDetectorDdbTable', {
      tableName: 'anomaly-detector-ddb-table',
      partitionKey: {
        name: 'id',
        type: aws_dynamodb.AttributeType.STRING,
      },
      billingMode: aws_dynamodb.BillingMode.PAY_PER_REQUEST,
      tableClass: aws_dynamodb.TableClass.STANDARD
    });

    cdk.Tags.of(this).add(TagKey, BillingTag);
    cdk.Tags.of(this).add(TagName, 'anomaly-detector-ddb-table');
  }
}