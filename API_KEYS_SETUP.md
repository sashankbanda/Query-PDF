# API Keys Setup Guide

## Required API Keys

### ✅ **GROQ_API_KEY** (REQUIRED)

**Purpose**: Used for the Large Language Model (LLM) that generates answers to your questions.

**Why it's needed**: 
- The application uses Groq's API to power the chatbot
- It processes your questions and generates responses based on the PDF content

**How to get it**:
1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up for a free account (if you don't have one)
3. Navigate to **API Keys** section
4. Click **Create API Key**
5. Copy your API key

**Free Tier Limits**:
- Groq offers generous free tier limits
- Fast response times
- No credit card required for basic usage

---

## Optional API Keys

### ❌ **GOOGLE_API_KEY** (NOT REQUIRED)

**Status**: **No longer needed!**

**Why**: 
- We migrated from Google Generative AI Embeddings to HuggingFace embeddings
- HuggingFace runs locally and doesn't require an API key
- This saves you from API quota issues

---

## Setup Instructions

### Step 1: Create `.env` File

Create a file named `.env` in the root directory of your project (same folder as `app.py`).

### Step 2: Add Your API Key

Add the following line to your `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
```

**Example**:
```env
GROQ_API_KEY=gsk_abc123xyz789...
```

### Step 3: Verify Setup

1. Make sure your `.env` file is in the root directory:
   ```
   Query-PDF/
   ├── .env          ← Your API key file
   ├── app.py
   ├── requirements.txt
   └── ...
   ```

2. Restart your Flask server after creating/updating the `.env` file

3. The application will automatically load the API key when it starts

---

## Security Best Practices

### ⚠️ Important Security Notes:

1. **Never commit `.env` to Git**
   - The `.env` file should be in your `.gitignore`
   - It contains sensitive information

2. **Don't share your API key**
   - Keep it private
   - Don't post it in code repositories
   - Don't share it in screenshots

3. **Rotate keys if compromised**
   - If you suspect your key is exposed, generate a new one
   - Revoke the old key in your Groq dashboard

---

## Troubleshooting

### Issue: "API key not found" or "Authentication failed"

**Solutions**:
1. Check that your `.env` file exists in the root directory
2. Verify the file is named exactly `.env` (not `.env.txt` or `env`)
3. Ensure there are no extra spaces around the `=` sign
4. Make sure the API key is correct (copy-paste from Groq console)
5. Restart your Flask server after creating/updating `.env`

### Issue: "Rate limit exceeded"

**Solutions**:
1. You've hit Groq's rate limit
2. Wait a few minutes and try again
3. Check your usage in the Groq console
4. Consider upgrading if you need higher limits

### Issue: "Invalid API key"

**Solutions**:
1. Double-check you copied the entire key
2. Make sure there are no extra spaces or line breaks
3. Generate a new key if the old one might be invalid
4. Verify the key is active in your Groq dashboard

---

## Testing Your Setup

After setting up your API key, test it by:

1. Starting the Flask server:
   ```bash
   python app.py
   ```

2. If the server starts without errors, your API key is working!

3. Upload a PDF and ask a question to verify everything works

---

## Summary

| API Key | Required? | Purpose | How to Get |
|---------|-----------|---------|------------|
| **GROQ_API_KEY** | ✅ **YES** | LLM for chatbot responses | [console.groq.com](https://console.groq.com/) |
| GOOGLE_API_KEY | ❌ No | ~~Embeddings~~ (removed) | Not needed |

---

## Quick Start Checklist

- [ ] Sign up for Groq account at [console.groq.com](https://console.groq.com/)
- [ ] Generate an API key
- [ ] Create `.env` file in project root
- [ ] Add `GROQ_API_KEY=your_key_here` to `.env`
- [ ] Restart Flask server
- [ ] Test by uploading a PDF and asking a question

---

**That's it!** You only need **one API key** (GROQ_API_KEY) to run the application.

