import * as cdk from 'aws-cdk-lib/core';

export function createTestApp(): cdk.App {
  return new cdk.App({
    context: {
      '@aws-cdk/core:explicitStackTags': false,
    },
  });
}
