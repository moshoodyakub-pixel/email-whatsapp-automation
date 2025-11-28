# Email-to-WhatsApp Automation Platform

Automatically monitor your Gmail inbox, generate AI summaries using Google Gemini, and receive notifications on WhatsApp.

## 🚀 Features

- **Real-time Email Monitoring**: Uses Gmail API with push notifications for instant detection
- **AI-Powered Summaries**: Google Gemini generates concise, actionable email summaries
- **WhatsApp Notifications**: Receive summaries directly on WhatsApp
- **Cloud-Ready**: Designed for deployment on Digital Ocean
- **Secure**: OAuth2 authentication, encrypted credentials, environment-based configuration

## 📋 Prerequisites

Before you begin, you'll need:

1. **Google Cloud Account** (free tier available)
   - Gmail API enabled
   - OAuth 2.0 credentials
   - Pub/Sub topic for push notifications

2. **Google AI Studio Account** (for Gemini API)
   - Free API key: <https://makersuite.google.com/app/apikey>

3. **WhatsApp Account**
   - A phone number with WhatsApp installed
   - Will authenticate via QR code

4. **Digital Ocean Account** (optional for cloud deployment)
   - Droplet or App Platform access

## 🛠️ Installation

### 1. Clone and Setup

```bash
cd C:\Users\hp\.gemini\antigravity\scratch\email-whatsapp-automation
npm install
pip install -r requirements.txt
```

### 2. Configure Google Cloud

#### Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Gmail API** and **Cloud Pub/Sub API**
4. Go to **APIs & Services > Credentials**
5. Create **OAuth 2.0 Client ID** (Desktop app)
6. Download credentials as `config/credentials.json`

#### Setup Pub/Sub for Push Notifications

```bash
# Create a Pub/Sub topic
gcloud pubsub topics create gmail-notifications

# Create a subscription
gcloud pubsub subscriptions create gmail-sub --topic=gmail-notifications

# Grant Gmail permission to publish
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

### 3. Get Google Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)

### 4. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp config/.env.example config/.env
```

Edit `config/.env`:

```env
# Gmail Configuration
GMAIL_CREDENTIALS_PATH=config/credentials.json
GMAIL_TOKEN_PATH=config/token.pickle
PUBSUB_PROJECT_ID=your-gcp-project-id
PUBSUB_TOPIC_NAME=gmail-notifications
PUBSUB_SUBSCRIPTION_NAME=gmail-sub

# Google Gemini AI
GEMINI_API_KEY=AIza...your-key-here

# WhatsApp Configuration
YOUR_WHATSAPP_NUMBER=+1234567890  # Your phone number with country code

# Monitoring Settings
PROCESS_EXISTING=false  # Set to true to process existing unread emails
SUMMARY_LENGTH=standard  # brief, standard, or detailed

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

## 🚀 Usage

### Local Development

#### 1. Authenticate Gmail (First Time Only)

```bash
python src/gmail_auth.py
```

This will open a browser for OAuth consent and save the token.

#### 2. Authenticate WhatsApp (First Time Only)

```bash
node src/whatsapp_init.js
```

Scan the QR code with your WhatsApp mobile app.

#### 3. Run the Application

```bash
python src/main.py
```

The application will:

- Start monitoring your Gmail inbox
- Generate summaries for new emails using Gemini
- Send notifications to your WhatsApp

### Docker Deployment (Digital Ocean)

#### 1. Build Docker Image

```bash
docker build -t email-whatsapp-bot .
```

#### 2. Run with Docker Compose

```bash
docker-compose up -d
```

#### 3. Deploy to Digital Ocean

**Option A: Using Digital Ocean App Platform**

```bash
# Install doctl CLI
# https://docs.digitalocean.com/reference/doctl/how-to/install/

# Authenticate
doctl auth init

# Deploy
doctl apps create --spec .do/app.yaml
```

**Option B: Using Digital Ocean Droplet**

```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Clone repository
git clone <your-repo-url>
cd email-whatsapp-automation

# Setup environment
cp config/.env.example config/.env
# Edit .env with your credentials

# Run with Docker
docker-compose up -d
```

## 📱 WhatsApp Authentication on Server

Since WhatsApp Web.js requires QR code scanning, you have two options for cloud deployment:

**Option 1: Pre-authenticate Locally**

1. Run `node src/whatsapp_init.js` locally
2. This creates `.wwebjs_auth` folder with session data
3. Upload this folder to your server (keep it secure!)
4. The server will use the saved session

**Option 2: Temporary Port Forwarding**

1. Deploy to Digital Ocean
2. Temporarily expose the QR code endpoint
3. Access `http://your-server-ip:3000/qr` to scan
4. Close the endpoint after authentication

## 📊 Message Format

WhatsApp notifications will look like:

```
📧 New Email from John Doe <john@example.com>

📌 Subject: Q4 Project Update

📝 Summary:
John is requesting a status update on the Q4 marketing project. 
He needs the final report by Friday and wants to schedule a 
review meeting next week.

🕐 Received: 2:45 PM, Nov 28
```

## 🔧 Configuration Options

### Summary Length

Edit `SUMMARY_LENGTH` in `.env`:

- `brief`: One-line summary (quick notifications)
- `standard`: 2-3 sentences with key points (default)
- `detailed`: Full summary with action items

### Email Filters

By default, all new emails are processed. To filter specific emails, modify `src/email_monitor.py`:

```python
# Example: Only process emails from specific senders
ALLOWED_SENDERS = ['boss@company.com', 'client@example.com']

# Example: Only process emails with specific labels
REQUIRED_LABELS = ['IMPORTANT', 'INBOX']
```

## 🔒 Security Best Practices

1. **Never commit credentials**: `.env` and `credentials.json` are in `.gitignore`
2. **Use environment variables**: All secrets should be in `.env`
3. **Rotate API keys**: Regularly regenerate your Gemini API key
4. **Secure WhatsApp session**: The `.wwebjs_auth` folder contains sensitive data
5. **Enable 2FA**: Use two-factor authentication on your Google account
6. **Monitor logs**: Regularly check `logs/app.log` for suspicious activity

## 📈 Monitoring & Logs

Logs are written to `logs/app.log` with the following information:

- Email processing events
- API calls and responses
- WhatsApp message delivery status
- Errors and warnings

View logs in real-time:

```bash
tail -f logs/app.log
```

## 💰 Cost Estimation

Based on 100 emails/day:

| Service | Cost | Notes |
|---------|------|-------|
| Gmail API | Free | Up to 1B requests/day |
| Google Gemini API | ~$3-5/month | ~$0.001 per email |
| WhatsApp Web.js | Free | Unofficial, no API costs |
| Digital Ocean Droplet | $6/month | Basic droplet |
| **Total** | **~$9-11/month** | |

## 🐛 Troubleshooting

### Gmail API Issues

**Error: "Invalid credentials"**

- Re-run `python src/gmail_auth.py` to refresh OAuth token
- Ensure `credentials.json` is in `config/` folder

**Error: "Push notification not working"**

- Verify Pub/Sub topic exists: `gcloud pubsub topics list`
- Check IAM permissions for Gmail service account
- Gmail push notifications expire after 7 days - the app auto-renews them

### WhatsApp Issues

**Error: "QR code not scanning"**

- Ensure WhatsApp is updated to latest version
- Try clearing WhatsApp cache
- Use WhatsApp on the same phone number you configured

**Error: "Session expired"**

- Delete `.wwebjs_auth` folder
- Re-run `node src/whatsapp_init.js`
- Scan QR code again

### Gemini API Issues

**Error: "API key invalid"**

- Verify your API key at [Google AI Studio](https://makersuite.google.com/app/apikey)
- Ensure no extra spaces in `.env` file
- Check API key hasn't been revoked

**Error: "Rate limit exceeded"**

- Free tier has limits (60 requests/minute)
- Consider upgrading or adding rate limiting in code

## 🔄 Updates & Maintenance

### Update Dependencies

```bash
pip install -r requirements.txt --upgrade
npm update
```

### Renew Gmail Push Notifications

Push notifications expire after 7 days. The app automatically renews them, but you can manually renew:

```bash
python src/gmail_auth.py --renew-watch
```

## 📝 License

MIT License - feel free to modify and use for your needs.

## 🤝 Contributing

This is a personal automation project, but suggestions are welcome!

## ⚠️ Disclaimer

- **WhatsApp Web.js** is an unofficial library and may break with WhatsApp updates
- Using unofficial WhatsApp libraries may violate WhatsApp's Terms of Service
- For production use, consider official WhatsApp Business API
- This tool is for personal use only

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review logs in `logs/app.log`
3. Ensure all prerequisites are met
4. Verify environment variables are set correctly
