# S3 Bucket Setup Guide

This guide explains how to create and configure the S3 bucket for UrbIA in a new AWS account.

## Prerequisites

- AWS account created
- AWS CLI installed and configured

## Step 1: Create IAM User with S3 Access

1. Login to [AWS Console](https://console.aws.amazon.com)
2. Search for **IAM** and go to the IAM service
3. Click **Users** → **Create user**
4. Set username: `matteo` (or your preferred name)
5. Select **Access key - Programmatic access**
6. Click **Next**
7. Select **Attach policies directly**
8. Search and select **AmazonS3FullAccess** (or create a custom policy)
9. Click **Next** → **Create user**
10. **Copy the Access Key ID and Secret Access Key** (secret is shown only once!)

## Step 2: Configure AWS CLI

```bash
aws configure
```

Enter the credentials from Step 1:
- AWS Access Key ID: `AKIAXXXXXXXXXXXXX`
- AWS Secret Access Key: `your_secret_key`
- Default region name: `eu-central-1`
- Default output format: `json`

## Step 3: Create S3 Bucket

```bash
aws s3 mb s3://urbia-prod --region eu-central-1
```

## Step 4: Create Folder Structure

```bash
aws s3api put-object --bucket urbia-prod --key input/
aws s3api put-object --bucket urbia-prod --key input/datasets/
aws s3api put-object --bucket urbia-prod --key output/
aws s3api put-object --bucket urbia-prod --key tests/
```

## Step 5: Apply Bucket Policy

```bash
aws s3api put-bucket-policy --bucket urbia-prod --policy file://policy.json
```

## Step 6: Update Environment Variables

Add the following to your `.env` file:

```bash
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
S3_BUCKET=urbia-prod
AWS_REGION=eu-central-1
```

## Bucket Structure

```
urbia-prod/
├── input/
│   └── datasets/
├── output/
└── tests/
```

## Policy File

The bucket policy is stored in `policy.json` at the project root. It grants the following permissions:

| Prefix | Permissions |
|--------|-------------|
| `input/*` | Read (`GetObject`) |
| `input/datasets/*` | Write, Delete |
| `output/*` | Read, Write |
| `tests/*` | Read, Write, Delete |
| Root bucket | List (on specific prefixes) |

The policy is version-controlled in git as it only contains non-sensitive configuration.
