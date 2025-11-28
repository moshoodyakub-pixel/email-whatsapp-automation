/**
 * WhatsApp initialization script
 * Run this once to authenticate with WhatsApp
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
require('dotenv').config({ path: '../config/.env' });

console.log('🚀 WhatsApp Authentication Setup\n');

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: process.env.WHATSAPP_SESSION_PATH || '.wwebjs_auth'
    }),
    puppeteer: {
        headless: false,  // Show browser for initial setup
        args: ['--no-sandbox']
    }
});

client.on('qr', (qr) => {
    console.log('\n📱 SCAN THIS QR CODE WITH YOUR WHATSAPP APP:\n');
    qrcode.generate(qr, { small: true });
    console.log('\nSteps:');
    console.log('1. Open WhatsApp on your phone');
    console.log('2. Go to Settings → Linked Devices');
    console.log('3. Tap "Link a Device"');
    console.log('4. Scan the QR code above\n');
});

client.on('authenticated', () => {
    console.log('✅ Authentication successful!');
    console.log('Session data saved. You won\'t need to scan QR code again.\n');
});

client.on('ready', () => {
    console.log('✅ WhatsApp is ready!');
    console.log('\nYou can now close this window and run the main application.\n');

    // Send a test message
    const targetNumber = process.env.YOUR_WHATSAPP_NUMBER;
    if (targetNumber) {
        const formattedNumber = targetNumber.replace(/[^0-9]/g, '') + '@c.us';
        client.sendMessage(formattedNumber, '🎉 WhatsApp bot successfully connected!')
            .then(() => {
                console.log('✅ Test message sent to your WhatsApp!');
                console.log('\nAuthentication complete. Exiting...\n');
                setTimeout(() => process.exit(0), 2000);
            })
            .catch(err => {
                console.error('❌ Failed to send test message:', err.message);
                setTimeout(() => process.exit(0), 2000);
            });
    } else {
        console.log('⚠️  YOUR_WHATSAPP_NUMBER not configured in .env');
        setTimeout(() => process.exit(0), 2000);
    }
});

client.on('auth_failure', (msg) => {
    console.error('❌ Authentication failed:', msg);
    console.log('\nPlease try again.\n');
    process.exit(1);
});

console.log('Initializing WhatsApp client...\n');
client.initialize();
