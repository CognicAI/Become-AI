const express = require('express');
const path = require('path');
const app = express();
const PORT = 3000;

// Middleware to parse JSON bodies
app.use(express.json());

// Security Headers Middleware
app.use((req, res, next) => {
    // 1. Frame Ancestors: Allow this widget to be embedded on any domain (for a public widget)
    // In production, you might restrict this to specific client domains: "frame-ancestors 'self' https://client.com"
    res.setHeader('Content-Security-Policy', "frame-ancestors *;");

    // 2. Disable X-Frame-Options to allow embedding (CSP frame-ancestors takes precedence in modern browsers)
    // If you set X-Frame-Options: DENY, it would block the iframe.
    res.removeHeader('X-Frame-Options');

    // 3. Standard security headers
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');

    next();
});

// Serve Widget HTML
// This is the isolated iframe content
app.get('/widget.html', (req, res) => {
    res.sendFile(path.join(__dirname, '../widget/widget.html'));
});

// Serve Embed Script
// This is the script clients include
app.get('/fin-widget.js', (req, res) => {
    res.sendFile(path.join(__dirname, '../embed/fin-widget.js'));
});

// Serve Demo Page (Bonus)
app.get('/demo.html', (req, res) => {
    res.sendFile(path.join(__dirname, '../demo.html'));
});

// API Endpoint Stub
// The widget could call this to send messages to the backend
app.post('/api/send', (req, res) => {
    const { text, userId } = req.body;
    console.log(`[Server] Received message: "${text}" from user: ${userId || 'anon'}`);
    
    // Simulate processing delay
    setTimeout(() => {
        res.json({ status: 'ok', reply: 'Message received by server' });
    }, 500);
});

app.listen(PORT, () => {
    console.log(`\n🚀 Widget Server running at http://localhost:${PORT}`);
    console.log(`   - Widget: http://localhost:${PORT}/widget.html`);
    console.log(`   - Embed Script: http://localhost:${PORT}/fin-widget.js`);
    console.log(`   - Demo: http://localhost:${PORT}/demo.html\n`);
});