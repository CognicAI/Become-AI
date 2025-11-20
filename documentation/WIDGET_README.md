# Fin Chat Widget Plugin

This is a standalone embeddable chat widget designed to integrate with the Become AI system.

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Start Dev Server**
   ```bash
   npm start
   ```

3. **View Demo**
   Open [http://localhost:3000/demo.html](http://localhost:3000/demo.html) in your browser.

## 📦 Installation for Clients

Add the following script tag to your website's `<body>` or `<head>`:

```html
<script src="https://cdn.your-domain.com/fin-widget.js" async></script>
```

### Configuration Options
You can configure the widget using data attributes on the script tag:

```html
<script 
  src="https://cdn.your-domain.com/fin-widget.js" 
  data-widget-url="https://cdn.your-domain.com/widget.html"
  async
></script>
```

## 🛠 API Reference

The widget exposes a global API `window.finChat`:

| Method | Description |
|--------|-------------|
| `finChat.open()` | Opens the chat widget. |
| `finChat.close()` | Closes the chat widget. |
| `finChat.send(text)` | Sends a message as the user. |
| `finChat.setTheme(theme)` | Updates theme variables (e.g., `{ accent: '#ff0000' }`). |

### Events
The widget dispatches custom DOM events on the `window` object:

- `finChat.ready`: Fired when the widget iframe has loaded.
- `finChat.message`: Fired when the user sends a message.

```javascript
window.addEventListener('finChat.message', (e) => {
    console.log('User sent:', e.detail.text);
});
```

## 🔒 Security & Production Checklist

Before deploying to production, ensure you address the following:

### 1. HTTPS Everywhere
Ensure both the embedding page and the widget iframe are served over HTTPS. Mixed content (HTTP iframe on HTTPS page) will be blocked by browsers.

### 2. Validate PostMessage Origins
In `widget/widget.html` and `embed/fin-widget.js`, replace the wildcard `*` or permissive checks with strict origin validation.

**In `widget.html`:**
```javascript
const ALLOWED_ORIGINS = ['https://client-site.com'];
if (!ALLOWED_ORIGINS.includes(event.origin)) return;
```

**In `fin-widget.js`:**
```javascript
const WIDGET_ORIGIN = new URL(WIDGET_URL).origin;
if (event.origin !== WIDGET_ORIGIN) return;
```

### 3. Content Security Policy (CSP)
Set the `Content-Security-Policy` header on your server response for `widget.html`.

- **frame-ancestors**: Controls where the widget can be embedded.
  ```
  Content-Security-Policy: frame-ancestors 'self' https://client-site.com;
  ```
  Use `*` only if you want to allow embedding on ANY site.

### 4. Sandbox Attribute
For extra security, you can add the `sandbox` attribute to the iframe in `fin-widget.js`, but ensure you allow necessary permissions:
```javascript
iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-popups');
```

### 5. Input Sanitization
Ensure that any text sent from the widget to your backend is properly sanitized to prevent XSS attacks.

## 🎨 Customization

The widget uses CSS variables for styling. You can override these in `widget/widget.html` or pass them via `finChat.setTheme()`.

- `--accent-color`: Color of user bubbles and active elements.
- `--bg-color`: Background color of the widget.
- `--font-family`: Font stack used in the widget.

## 📂 Project Structure

- `embed/fin-widget.js`: The lightweight script injected into the client site. Handles the launcher and iframe creation.
- `widget/widget.html`: The actual chat interface loaded inside the iframe.
- `server/index.js`: A simple Express server to host the files and demonstrate security headers.
