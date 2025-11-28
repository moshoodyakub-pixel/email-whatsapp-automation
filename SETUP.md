# Quick Setup Guide

## Prerequisites Checklist

Before you begin, make sure you have:

- [ ] Python 3.9+ installed
- [ ] Node.js 16+ installed
- [ ] Gmail account
- [ ] WhatsApp account
- [ ] Google Cloud account (free tier)
- [ ] Google AI Studio account (for Gemini API)

## Step-by-Step Setup

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install
```

### 2. Configure Google Cloud

#### A. Create Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "email-whatsapp-bot")
3. Note your Project ID

#### B. Enable APIs

1. Go to **APIs & Services > Library**
2. Enable these APIs:
   - Gmail API
   - Cloud Pub/Sub API

#### C. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Choose **Desktop app**
4. Download credentials as JSON
5. Save to `config/credentials.json`

#### D. Setup Pub/Sub

```bash
# Install Google Cloud SDK if needed
# https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Create topic
gcloud pubsub topics create gmail-notifications

# Create subscription
gcloud pubsub subscriptions create gmail-sub --topic=gmail-notifications

# Grant Gmail permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

### 3. Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)

### 4. Configure Environment

```bash
# Copy example config
cp config/.env.example config/.env

# Edit config/.env with your details
notepad config/.env  # Windows
# or
nano config/.env     # Linux/Mac
```

Fill in:

```env
PUBSUB_PROJECT_ID=your-gcp-project-id
GEMINI_API_KEY=AIza...your-key
YOUR_WHATSAPP_NUMBER=+1234567890
```

### 5. Authenticate Gmail

```bash
python src/gmail_auth.py
```

This will:

- Open a browser for OAuth consent
- Save authentication token
- Test Gmail API access

### 6. Authenticate WhatsApp

```bash
node src/whatsapp_init.js
```

This will:

- Display a QR code
- Wait for you to scan with WhatsApp
- Save session data
- Send a test message

### 7. Test Components

```bash
python src/main.py --test
```

This will verify:

- Configuration is valid
- Gemini AI is accessible
- WhatsApp service is ready

### 8. Run the Bot

#### Terminal 1: Start WhatsApp Service

```bash
node src/whatsapp_service.js
```

#### Terminal 2: Start Email Monitor

```bash
python src/main.py
```

## Docker Deployment (Optional)

### Build and Run Locally

```bash
# Build image
docker-compose build

# Run container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down
```

### Deploy to Digital Ocean

1. Push code to GitHub
2. Update `.do/app.yaml` with your repo URL
3. Deploy:

```bash
# Install doctl
# https://docs.digitalocean.com/reference/doctl/how-to/install/

# Authenticate
doctl auth init

# Create app
doctl apps create --spec .do/app.yaml

# Or update existing app
doctl apps update YOUR_APP_ID --spec .do/app.yaml
```

## Troubleshooting

### Gmail Authentication Issues

**Error: "credentials.json not found"**

- Download OAuth credentials from Google Cloud Console
- Save to `config/credentials.json`

**Error: "Access blocked"**

- Enable Gmail API in Google Cloud Console
- Make sure OAuth consent screen is configured

### WhatsApp Issues

**QR code not appearing**

- Ensure Node.js is installed: `node --version`
- Install dependencies: `npm install`
- Try running with visible browser: Edit `whatsapp_init.js`, set `headless: false`

**Session expired**

- Delete `.wwebjs_auth` folder
- Re-run `node src/whatsapp_init.js`

### Gemini API Issues

**Error: "Invalid API key"**

- Verify key at [Google AI Studio](https://makersuite.google.com/app/apikey)
- Check for extra spaces in `.env` file

**Rate limit exceeded**

- Free tier: 60 requests/minute
- The bot has built-in rate limiting
- Consider upgrading if processing many emails

### Pub/Sub Issues

**Push notifications not working**

- Verify topic exists: `gcloud pubsub topics list`
- Check subscription: `gcloud pubsub subscriptions list`
- Verify IAM permissions for Gmail service account

## Next Steps

Once everything is working:

1. **Customize Summary Length**: Edit `SUMMARY_LENGTH` in `.env`
2. **Add Email Filters**: Modify `src/email_monitor.py` to filter specific senders
3. **Schedule Quiet Hours**: Add time-based filtering in `src/main.py`
4. **Monitor Costs**: Check Google Cloud billing dashboard
5. **Setup Alerts**: Configure monitoring for errors

## Support

For issues:

1. Check logs in `logs/app.log`
2. Run with `--test` flag to diagnose
3. Review the main README.md for detailed documentation
