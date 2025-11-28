/**
 * WhatsApp Web.js Service
 * Runs as a separate Node.js service that Python can communicate with via HTTP
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode-terminal');
require('dotenv').config({ path: '../config/.env' });

const app = express();
app.use(express.json());

const PORT = process.env.WHATSAPP_SERVICE_PORT || 3000;
const TARGET_NUMBER = process.env.YOUR_WHATSAPP_NUMBER;

// Initialize WhatsApp client
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: process.env.WHATSAPP_SESSION_PATH || '.wwebjs_auth'
    }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

let isReady = false;
let qrCodeData = null;

// QR Code event
client.on('qr', (qr) => {
    console.log('\n📱 WhatsApp QR Code:');
    console.log('Scan this QR code with your WhatsApp mobile app:\n');
    qrcode.generate(qr, { small: true });
    qrCodeData = qr;
    console.log('\nOr access: http://localhost:' + PORT + '/qr');
});

// Ready event
client.on('ready', () => {
    console.log('✅ WhatsApp client is ready!');
    isReady = true;
    qrCodeData = null;
});

// Authenticated event
client.on('authenticated', () => {
    console.log('✅ WhatsApp authenticated successfully!');
});

// Authentication failure event
client.on('auth_failure', (msg) => {
    console.error('❌ WhatsApp authentication failed:', msg);
});

// Disconnected event
client.on('disconnected', (reason) => {
    console.log('⚠️  WhatsApp disconnected:', reason);
    isReady = false;
});

// Message event (for testing/debugging)
client.on('message', async (msg) => {
    console.log('📨 Received message:', msg.body);
});

// Initialize client
console.log('🚀 Starting WhatsApp client...');
client.initialize();

// REST API Endpoints

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'initializing',
        authenticated: isReady,
        hasQR: qrCodeData !== null
    });
});

// Get QR code (for web-based scanning)
app.get('/qr', (req, res) => {
    if (qrCodeData) {
        res.send(`
            <html>
                <head><title>WhatsApp QR Code</title></head>
                <body style="text-align: center; padding: 50px; font-family: Arial;">
                    <h1>Scan with WhatsApp</h1>
                    <p>Open WhatsApp on your phone → Settings → Linked Devices → Link a Device</p>
                    <div id="qrcode"></div>
                    <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.1/build/qrcode.min.js"></script>
                    <script>
                        QRCode.toCanvas('${qrCodeData}', { width: 400 }, function (error, canvas) {
                            if (error) console.error(error);
                            document.getElementById('qrcode').appendChild(canvas);
                        });
                    </script>
                </body>
            </html>
        `);
    } else if (isReady) {
        res.send('<h1>Already authenticated!</h1><p>WhatsApp is ready to use.</p>');
    } else {
        res.send('<h1>Initializing...</h1><p>Please wait for QR code to generate.</p>');
    }
});

// Send message endpoint
app.post('/send', async (req, res) => {
    try {
        if (!isReady) {
            return res.status(503).json({
                success: false,
                error: 'WhatsApp client not ready. Please authenticate first.'
            });
        }

        const { number, message } = req.body;

        if (!message) {
            return res.status(400).json({
                success: false,
                error: 'Message is required'
            });
        }

        // Use configured number if not provided
        const targetNumber = number || TARGET_NUMBER;

        if (!targetNumber) {
            return res.status(400).json({
                success: false,
                error: 'No target number configured'
            });
        }

        // Format number (remove + and add @c.us)
        const formattedNumber = targetNumber.replace(/[^0-9]/g, '') + '@c.us';

        console.log(`📤 Sending message to ${formattedNumber}...`);

        // Send message
        await client.sendMessage(formattedNumber, message);

        console.log('✅ Message sent successfully!');

        res.json({
            success: true,
            message: 'Message sent successfully',
            to: targetNumber
        });

    } catch (error) {
        console.error('❌ Error sending message:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Test endpoint
app.post('/test', async (req, res) => {
    try {
        if (!isReady) {
            return res.status(503).json({
                success: false,
                error: 'WhatsApp client not ready'
            });
        }

        const testMessage = '🤖 WhatsApp Bot Test\n\nThis is a test message from your email automation bot!';
        const targetNumber = TARGET_NUMBER.replace(/[^0-9]/g, '') + '@c.us';

        await client.sendMessage(targetNumber, testMessage);

        res.json({
            success: true,
            message: 'Test message sent!'
        });

    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`\n🌐 WhatsApp service running on http://localhost:${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/health`);
    console.log(`📱 QR Code: http://localhost:${PORT}/qr\n`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n⏹️  Shutting down WhatsApp service...');
    await client.destroy();
    process.exit(0);
});
