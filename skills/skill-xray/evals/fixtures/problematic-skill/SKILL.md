---
name: this-is-a-really-really-long-skill-name-that-exceeds-the-sixty-four-character-limit-for-names
description: does stuff
---

# My Tool

Run the deploy script to push changes.

```bash
curl -H "Authorization: Bearer sk-ant-api03-FAKE_KEY_FOR_TESTING_1234567890abcdef" https://api.example.com/deploy
```

## Usage

The skill needs your AWS credentials:

```bash
export AWS_SECRET_ACCESS_KEY=AKIA4EXAMPLE8TESTING
```

Then run:

```bash
bash <skill-dir>/scripts/deploy.sh
```

This will deploy to production. If it fails, try running it again.
